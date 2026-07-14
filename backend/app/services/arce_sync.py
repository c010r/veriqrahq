from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from urllib.parse import quote_plus

import httpx
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.services import sync_state
from app.services.arce_parser import enrich_from_detail_html, has_next_page, parse_arce_results_html
from app.services.catalog_service import items_for
from app.services.purchase_service import upsert_purchases

ARCE_BASE = "https://www.comprasestatales.gub.uy"
ARCE_HEADERS = {"User-Agent": "Mozilla/5.0"}
HISTORY_START = date(2024, 1, 1)
_sync_lock = asyncio.Lock()


def history_start(end: date | None = None) -> date:
    return HISTORY_START


def month_ranges(start: date, end: date):
    current = date(start.year, start.month, 1)
    while current <= end:
        if current.month == 12:
            next_month = date(current.year + 1, 1, 1)
        else:
            next_month = date(current.year, current.month + 1, 1)
        yield max(start, current), min(end, next_month - timedelta(days=1))
        current = next_month


def format_range(start: date, end: date) -> str:
    raw = f"{start.isoformat()} 00:00:00_{end.isoformat()} 23:59:59"
    return quote_plus(raw)


def search_url(publication_type: str, inciso: str, start: date, end: date, *, page: int = 1, date_type: str = "PUB") -> str:
    return (
        f"{ARCE_BASE}/consultas/buscar/tipo-pub/{publication_type}/inciso/{inciso}"
        f"/tipo-fecha/{date_type}/rango-fecha/{format_range(start, end)}/page/{page}"
    )


async def sync_window(
    db: Session,
    client: httpx.AsyncClient,
    *,
    publication_type: str,
    inciso: str,
    agency: str,
    start: date,
    end: date,
    date_type: str,
    max_pages: int = 80,
) -> tuple[int, int, int]:
    imported = 0
    updated = 0
    processed = 0
    for page in range(1, max_pages + 1):
        url = search_url(publication_type, inciso, start, end, page=page, date_type=date_type)
        response = await client.get(url, headers=ARCE_HEADERS)
        response.raise_for_status()
        purchases = parse_arce_results_html(response.text, source=url, publication_type=publication_type)
        if publication_type.upper() == "ADJ" and purchases:
            semaphore = asyncio.Semaphore(10)

            async def enrich_item(item):
                if not item.source_url:
                    return
                async with semaphore:
                    try:
                        detail_response = await client.get(item.source_url, headers=ARCE_HEADERS)
                        detail_response.raise_for_status()
                    except httpx.HTTPError:
                        return
                    enrich_from_detail_html(item, detail_response.text)

            await asyncio.gather(*(enrich_item(item) for item in purchases))
        if agency:
            for item in purchases:
                item.agency = agency
        if purchases:
            next_imported, next_updated = upsert_purchases(db, purchases)
            imported += next_imported
            updated += next_updated
            processed += len(purchases)
        if not has_next_page(response.text) or not purchases:
            break
    return imported, updated, processed


async def _sync_history(agencies: list[tuple[str, str]], *, start: date, end: date, task_name: str) -> None:
    async with _sync_lock:
        label = "todos los organismos" if len(agencies) > 1 else agencies[0][1]
        sync_state.start(task_name, f"Sincronizando datos desde {HISTORY_START:%d/%m/%Y} de {label}...")
        total_imported = 0
        total_updated = 0
        total_processed = 0
        db = SessionLocal()
        try:
            async with httpx.AsyncClient(timeout=45, follow_redirects=True) as client:
                for inciso, agency in agencies:
                    for publication_type, publication_label in (("ALL", "pedidos"), ("ADJ", "adjudicaciones")):
                        for start_window, end_window in month_ranges(start, end):
                            message = f"{agency}: {publication_label} {start_window:%m/%Y}"
                            sync_state.progress(message, processed=total_processed, imported=total_imported, updated=total_updated)
                            next_imported, next_updated, next_processed = await sync_window(
                                db,
                                client,
                                publication_type=publication_type,
                                inciso=inciso,
                                agency=agency,
                                start=start_window,
                                end=end_window,
                                date_type="PUB",
                            )
                            total_imported += next_imported
                            total_updated += next_updated
                            total_processed += next_processed
            sync_state.finish(
                f"Historico desde {HISTORY_START:%d/%m/%Y} sincronizado para {label}.",
                imported=total_imported,
                updated=total_updated,
                processed=total_processed,
            )
        except Exception as exc:  # noqa: BLE001
            sync_state.fail(f"Fallo la sincronizacion historica: {exc}")
        finally:
            db.close()


async def sync_history_for_agency(inciso: str, agency: str, *, start: date | None = None, end: date | None = None) -> None:
    end = end or date.today()
    await _sync_history([(inciso, agency)], start=start or history_start(end), end=end, task_name="history")


async def sync_history_for_all_agencies(*, start: date | None = None, end: date | None = None) -> None:
    end = end or date.today()
    db = SessionLocal()
    try:
        agencies = active_agencies(db)
    finally:
        db.close()
    await _sync_history(agencies, start=start or history_start(end), end=end, task_name="history_all")


def active_agencies(db: Session) -> list[tuple[str, str]]:
    items = items_for(db, "incisos")
    return [(item.code, item.label) for item in items if item.code and item.label]


async def sync_recent(publication_type: str, *, hours: int, label: str) -> None:
    if sync_state.get_state().get("running"):
        return
    async with _sync_lock:
        if sync_state.get_state().get("running"):
            return
        end = datetime.utcnow().date()
        start = (datetime.utcnow() - timedelta(hours=hours)).date()
        sync_state.start(label, f"Sincronizando {label} de las ultimas {hours} horas...")
        total_imported = 0
        total_updated = 0
        total_processed = 0
        db = SessionLocal()
        try:
            agencies = active_agencies(db)
            async with httpx.AsyncClient(timeout=45, follow_redirects=True) as client:
                for inciso, agency in agencies:
                    sync_state.progress(f"{label}: {agency}", processed=total_processed, imported=total_imported, updated=total_updated)
                    next_imported, next_updated, next_processed = await sync_window(
                        db,
                        client,
                        publication_type=publication_type,
                        inciso=inciso,
                        agency=agency,
                        start=start,
                        end=end,
                        date_type="MOD",
                        max_pages=10,
                    )
                    total_imported += next_imported
                    total_updated += next_updated
                    total_processed += next_processed
            sync_state.finish(
                f"Sincronizacion automatica de {label} finalizada.",
                imported=total_imported,
                updated=total_updated,
                processed=total_processed,
            )
        except Exception as exc:  # noqa: BLE001
            sync_state.fail(f"Fallo la sincronizacion automatica de {label}: {exc}")
        finally:
            db.close()


async def scheduler_loop() -> None:
    last_awards = datetime.utcnow()
    last_new = datetime.utcnow()
    while True:
        now = datetime.utcnow()
        try:
            if now - last_awards >= timedelta(hours=1):
                await sync_recent("ADJ", hours=1, label="adjudicaciones")
                last_awards = datetime.utcnow()
            if now - last_new >= timedelta(hours=6):
                await sync_recent("ALL", hours=6, label="nuevos llamados")
                last_new = datetime.utcnow()
        finally:
            await asyncio.sleep(300)
