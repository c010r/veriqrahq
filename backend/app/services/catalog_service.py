from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime

import httpx
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.catalog import CatalogItem, CatalogResource


ARCE_CATALOG_RESOURCES = [
    {
        "slug": "estados_compra",
        "name": "Codiguera de Estados de Compra",
        "description": "Descripcion de los estados de las compras",
        "url": "http://www.comprasestatales.gub.uy/comprasenlinea/jboss/reporteEstadosCompra.do",
    },
    {
        "slug": "incisos",
        "name": "Codiguera de Incisos",
        "description": "Descripcion de los Incisos",
        "url": "http://www.comprasestatales.gub.uy/comprasenlinea/jboss/reporteIncisos.do",
    },
    {
        "slug": "monedas",
        "name": "Codiguera de Monedas",
        "description": "Descripcion y sigla de las monedas",
        "url": "http://www.comprasestatales.gub.uy/comprasenlinea/jboss/reporteMonedas.do",
    },
    {
        "slug": "objetos_gasto",
        "name": "Codiguera de Objetos del Gasto",
        "description": "Descripcion de los objetos del gasto",
        "url": "http://www.comprasestatales.gub.uy/comprasenlinea/jboss/reporteObjetosGasto.do",
    },
    {
        "slug": "subtipos_compra",
        "name": "Codiguera de Subtipos de Compra",
        "description": "Descripcion y atributos de los subtipos de compra",
        "url": "http://www.comprasestatales.gub.uy/comprasenlinea/jboss/reporteSubTiposCompra.do",
    },
    {
        "slug": "tipos_compra",
        "name": "Codiguera de Tipos de Compra",
        "description": "Descripcion y atributos de los tipos de compra",
        "url": "http://www.comprasestatales.gub.uy/comprasenlinea/jboss/reporteTiposCompra.do",
    },
    {
        "slug": "tipos_documento_proveedor",
        "name": "Codiguera de Tipos de Documento de Proveedores",
        "description": "Descripcion de los tipos de documento de proveedores",
        "url": "http://www.comprasestatales.gub.uy/comprasenlinea/jboss/reporteTiposDocumento.do",
    },
    {
        "slug": "tipos_resolucion",
        "name": "Codiguera de Tipos de Resolucion",
        "description": "Descripcion de los tipos de resolucion",
        "url": "http://www.comprasestatales.gub.uy/comprasenlinea/jboss/reporteTiposResolucion.do",
    },
    {
        "slug": "tipos_resolucion_compra",
        "name": "Relacion entre tipos de compra y tipos de resolucion",
        "description": "Tipos de resolucion posibles para cada tipo de compra",
        "url": "http://www.comprasestatales.gub.uy/comprasenlinea/jboss/reporteTiposResolucionCompra.do",
    },
    {
        "slug": "ucc",
        "name": "Codiguera de Unidades de Compra Centralizadas",
        "description": "Descripcion de las unidades de compra centralizadas",
        "url": "http://www.comprasestatales.gub.uy/comprasenlinea/jboss/reporteUCCs.do",
    },
    {
        "slug": "unidades_ejecutoras",
        "name": "Codiguera de Unidades Ejecutoras",
        "description": "Descripcion de las unidades ejecutoras y su inciso de pertenencia",
        "url": "http://www.comprasestatales.gub.uy/comprasenlinea/jboss/reporteUnidadesEjecutoras.do",
    },
]


def _local_name(tag: str) -> str:
    return tag.split("}")[-1]


def _label_from_attrs(attrs: dict[str, str]) -> str:
    for key in ("descripcion", "nom-inciso", "nom-ue", "nombre", "sigla", "desc"):
        if attrs.get(key):
            return attrs[key]
    for key, value in attrs.items():
        if key not in {"id", "codigo", "id-inciso", "id-ue"} and value:
            return value
    return ""


def _code_from_attrs(attrs: dict[str, str], index: int) -> str:
    for key in ("id", "codigo", "id-inciso", "id-ue", "cod", "sigla"):
        if attrs.get(key):
            return attrs[key]
    return str(index)


def parse_catalog_xml(content: bytes) -> list[dict]:
    root = ET.fromstring(content)
    items = []
    seen_codes: dict[str, int] = {}
    for index, node in enumerate(list(root), start=1):
        attrs = {key: value for key, value in node.attrib.items()}
        if node.text and node.text.strip():
            attrs[_local_name(node.tag)] = node.text.strip()
        base_code = _code_from_attrs(attrs, index)
        seen_codes[base_code] = seen_codes.get(base_code, 0) + 1
        code = base_code if seen_codes[base_code] == 1 else f"{base_code}__{seen_codes[base_code]}"
        label = _label_from_attrs(attrs) or base_code
        items.append({"code": code, "label": label, "attrs": attrs})
    return items


async def sync_official_catalogs(db: Session) -> dict[str, int]:
    total = 0
    async with httpx.AsyncClient(
        timeout=45,
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; VeriqraHQ/1.0; +https://test.veriqrahq.pro)",
            "Accept": "application/xml,text/xml,*/*",
        },
    ) as client:
        for resource_data in ARCE_CATALOG_RESOURCES:
            response = await client.get(resource_data["url"])
            response.raise_for_status()
            items = parse_catalog_xml(response.content)

            resource = db.scalar(select(CatalogResource).where(CatalogResource.slug == resource_data["slug"]))
            if not resource:
                resource = CatalogResource(
                    slug=resource_data["slug"],
                    name=resource_data["name"],
                    description=resource_data["description"],
                    source_url=resource_data["url"],
                )
                db.add(resource)
                db.flush()

            resource.name = resource_data["name"]
            resource.description = resource_data["description"]
            resource.source_url = resource_data["url"]
            resource.item_count = len(items)
            resource.synced_at = datetime.utcnow()

            db.execute(delete(CatalogItem).where(CatalogItem.resource_slug == resource.slug))
            for item in items:
                db.add(
                    CatalogItem(
                        resource_id=resource.id,
                        resource_slug=resource.slug,
                        code=item["code"],
                        label=item["label"],
                        attrs=item["attrs"],
                    )
                )
            total += len(items)
    db.commit()
    return {"resources": len(ARCE_CATALOG_RESOURCES), "items": total}


def list_resources(db: Session) -> list[CatalogResource]:
    return list(db.scalars(select(CatalogResource).order_by(CatalogResource.name)).all())


def list_items(db: Session, resource_slug: str | None = None) -> list[CatalogItem]:
    statement = select(CatalogItem).order_by(CatalogItem.resource_slug, CatalogItem.label)
    if resource_slug:
        statement = statement.where(CatalogItem.resource_slug == resource_slug)
    return list(db.scalars(statement).all())


def labels_for(db: Session, resource_slug: str) -> list[str]:
    statement = select(CatalogItem.label).where(CatalogItem.resource_slug == resource_slug).order_by(CatalogItem.label)
    return list(db.scalars(statement).all())



def items_for(db: Session, resource_slug: str) -> list[CatalogItem]:
    statement = select(CatalogItem).where(CatalogItem.resource_slug == resource_slug).order_by(CatalogItem.label)
    return list(db.scalars(statement).all())

def item_label_for_code(db: Session, resource_slug: str, code: str) -> str:
    if not code or code == "all":
        return ""
    statement = select(CatalogItem.label).where(CatalogItem.resource_slug == resource_slug, CatalogItem.code == code)
    return db.scalar(statement) or ""
