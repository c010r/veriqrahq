from __future__ import annotations

import csv
import io
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from html import unescape

from app.schemas.purchase import PurchaseCreate


def clean_text(value: object) -> str:
    text = unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize(value: object) -> str:
    text = clean_text(value).lower()
    replacements = str.maketrans("áéíóúüñ", "aeiouun")
    return text.translate(replacements)


def parse_decimal(value: object) -> Decimal:
    text = re.sub(r"[^0-9,.-]", "", clean_text(value))
    if not text:
        return Decimal("0")
    if "," in text and text.rfind(",") > text.rfind("."):
        text = text.replace(".", "").replace(",", ".")
    else:
        text = text.replace(",", "")
    try:
        return Decimal(text)
    except InvalidOperation:
        return Decimal("0")


def parse_date(value: object) -> date | None:
    text = clean_text(value)
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%a, %d %b %Y %H:%M:%S %z"):
        try:
            return datetime.strptime(text[:31], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def infer_status(*values: object) -> str:
    text = normalize(" ".join(clean_text(value) for value in values))
    active_terms = ("vigente", "activo", "abierto", "llamado", "en curso")
    if any(term in text for term in active_terms):
        return "vigente"
    return "anterior"


def infer_currency(*values: object) -> str:
    text = normalize(" ".join(clean_text(value) for value in values))
    if "usd" in text or "u$s" in text or "us$" in text:
        return "USD"
    if "eur" in text:
        return "EUR"
    return "UYU"


def first(row: dict[str, object], *keys: str) -> str:
    normalized = {normalize(key): value for key, value in row.items()}
    for key in keys:
        value = normalized.get(normalize(key))
        if value not in (None, ""):
            return clean_text(value)
    return ""


def from_mapping(row: dict[str, object], fallback_id: str, source: str) -> PurchaseCreate:
    title = first(row, "objeto", "object", "titulo", "title", "descripcion", "description")
    description = first(row, "descripcion", "description", "detalle", "observaciones", "summary")
    amount = parse_decimal(first(row, "precio_adjudicado", "precioAdjudicado", "montoAdjudicado", "monto", "importe", "total", "precio") or description)
    unit_price = parse_decimal(first(row, "precio_unitario", "precioUnitario", "unitPrice")) or amount
    link = first(row, "link", "url", "source_url")
    external_id = first(row, "id", "guid", "expediente", "numero", "nroCompra", "codigo") or link or fallback_id

    return PurchaseCreate(
        external_id=external_id,
        status=infer_status(first(row, "estado", "status", "situacion"), title, description),
        procedure_type=first(row, "procedimiento", "procedure", "tipoCompra", "tipo_compra", "categoria") or "Publicacion ARCE",
        agency=first(row, "organismo", "agency", "inciso", "unidadEjecutora", "unidad_ejecutora", "author") or "ARCE",
        object=title or "Publicacion de Compras Estatales",
        supplier=first(row, "proveedor", "supplier", "adjudicatario", "empresa", "razonSocial") or "Sin proveedor informado",
        award_date=parse_date(first(row, "fecha_adjudicacion", "fechaAdjudicacion", "fechaPublicacion", "pubDate", "fecha")),
        closing_date=parse_date(first(row, "fecha_cierre", "fechaCierre", "vigenciaHasta", "fechaVencimiento")),
        currency=first(row, "moneda", "currency", "sigla") or infer_currency(description, amount),
        awarded_amount=amount,
        quantity=parse_decimal(first(row, "cantidad", "quantity")) or Decimal("1"),
        unit_price=unit_price,
        source=source,
        source_url=link,
        notes=description,
    )


def parse_csv(text: str, source: str = "CSV ARCE") -> list[PurchaseCreate]:
    reader = csv.DictReader(io.StringIO(text))
    return [from_mapping(dict(row), f"CSV-{index}", source) for index, row in enumerate(reader, start=1)]


def xml_to_dict(node: ET.Element) -> dict[str, object]:
    data: dict[str, object] = {}
    for child in list(node):
        name = child.tag.split("}")[-1]
        if list(child):
            data.update({f"{name}_{key}": value for key, value in xml_to_dict(child).items()})
        else:
            data[name] = child.text or ""
    if node.text and node.text.strip():
        data[node.tag.split("}")[-1]] = node.text
    return data


def parse_xml(text: str, source: str = "XML/RSS ARCE") -> list[PurchaseCreate]:
    root = ET.fromstring(text)
    candidates = [
        node
        for node in root.iter()
        if node.tag.split("}")[-1].lower() in {"item", "compra", "publicacion", "adjudicacion", "llamado"}
    ]
    if not candidates:
        candidates = list(root)
    return [from_mapping(xml_to_dict(node), f"XML-{index}", source) for index, node in enumerate(candidates, start=1)]
