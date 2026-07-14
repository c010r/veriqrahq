import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.purchase import ImportResult, PurchaseList, PurchaseRead
from app.services.catalog_service import labels_for
from app.services.arce_parser import parse_csv, parse_xml
from app.services.purchase_service import distinct_values, list_purchases, metrics, upsert_purchases

router = APIRouter(prefix="/purchases", tags=["purchases"])

ARCE_RSS_BASE = "https://www.comprasestatales.gub.uy/consultas/rss"
ARCE_HEADERS = {"User-Agent": "Mozilla/5.0"}


def official_arce_rss_url(tipo_pub: str, inciso: str) -> str:
    clean_tipo_pub = tipo_pub.strip().upper()
    clean_inciso = inciso.strip()
    if clean_tipo_pub not in {"VIG", "ADJ"}:
        raise HTTPException(status_code=400, detail="Tipo de publicacion ARCE no soportado.")
    if not clean_inciso.isdigit():
        raise HTTPException(status_code=400, detail="El inciso ARCE debe ser numerico.")
    return f"{ARCE_RSS_BASE}/tipo-pub/{clean_tipo_pub}/inciso/{clean_inciso}"



@router.get("", response_model=PurchaseList)
def get_purchases(
    db: Session = Depends(get_db),
    query: str = "",
    status: str = "all",
    agency: str = "all",
    procedure_type: str = "all",
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
) -> PurchaseList:
    items, total = list_purchases(
        db,
        query=query,
        status=status,
        agency=agency,
        procedure_type=procedure_type,
        limit=limit,
        offset=offset,
    )
    current_metrics = metrics(db)
    return PurchaseList(items=items, total=total, **current_metrics)


@router.get("/catalogs")
def get_catalogs(db: Session = Depends(get_db)) -> dict[str, list[str]]:
    official_agencies = labels_for(db, "incisos")
    official_procedure_types = labels_for(db, "tipos_compra")
    agencies = sorted(set(official_agencies) | set(distinct_values(db, "agency")))
    procedure_types = sorted(set(official_procedure_types) | set(distinct_values(db, "procedure_type")))
    return {
        "agencies": agencies,
        "procedure_types": procedure_types,
        "statuses": ["vigente", "anterior"],
    }


@router.post("/import", response_model=ImportResult)
async def import_file(
    db: Session = Depends(get_db),
    file: UploadFile = File(...),
    source: str = Form(default="ARCE"),
) -> ImportResult:
    content = (await file.read()).decode("utf-8-sig")
    if file.filename and file.filename.lower().endswith(".csv"):
        purchases = parse_csv(content, source=source)
    else:
        purchases = parse_xml(content, source=source)
    imported, updated = upsert_purchases(db, purchases)
    return ImportResult(imported=imported, updated=updated)


@router.post("/sync-url", response_model=ImportResult)
async def sync_url(
    db: Session = Depends(get_db),
    url: str = Form(...),
) -> ImportResult:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url, headers=ARCE_HEADERS)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail=f"No se pudo obtener la fuente ARCE: {exc}") from exc

    content_type = response.headers.get("content-type", "")
    if "csv" in content_type or url.lower().endswith(".csv"):
        purchases = parse_csv(response.text, source=url)
    else:
        purchases = parse_xml(response.text, source=url)
    imported, updated = upsert_purchases(db, purchases)
    return ImportResult(imported=imported, updated=updated)


@router.post("/sync-official", response_model=ImportResult)
async def sync_official(
    db: Session = Depends(get_db),
    inciso: str = Form(default="29"),
    tipo_pub: str = Form(default="VIG"),
) -> ImportResult:
    url = official_arce_rss_url(tipo_pub, inciso)
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(url, headers=ARCE_HEADERS)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=400, detail=f"No se pudo obtener el RSS oficial ARCE: {exc}") from exc

    purchases = parse_xml(response.text, source=url)
    imported, updated = upsert_purchases(db, purchases)
    return ImportResult(imported=imported, updated=updated)
