from xml.etree.ElementTree import ParseError

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.catalog import OfficialCatalogRead
from app.services.catalog_service import list_items, list_resources, sync_official_catalogs

router = APIRouter(prefix="/catalogs", tags=["catalogs"])


@router.get("/official", response_model=OfficialCatalogRead)
def get_official_catalog(
    db: Session = Depends(get_db),
    resource_slug: str | None = Query(default=None),
    include_items: bool = Query(default=False),
) -> OfficialCatalogRead:
    return OfficialCatalogRead(
        resources=list_resources(db),
        items=list_items(db, resource_slug=resource_slug) if include_items else [],
    )


@router.post("/official/sync")
async def sync_official_catalog(db: Session = Depends(get_db)) -> dict[str, int]:
    try:
        return await sync_official_catalogs(db)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"No se pudieron sincronizar las codigueras ARCE: {exc}") from exc
    except ParseError as exc:
        raise HTTPException(status_code=502, detail="ARCE devolvio una codiguera con XML invalido.") from exc
