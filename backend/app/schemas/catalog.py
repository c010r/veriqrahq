from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CatalogResourceRead(BaseModel):
    slug: str
    name: str
    description: str
    source_url: str
    item_count: int
    synced_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class CatalogItemRead(BaseModel):
    resource_slug: str
    code: str
    label: str
    attrs: dict

    model_config = ConfigDict(from_attributes=True)


class OfficialCatalogRead(BaseModel):
    resources: list[CatalogResourceRead]
    items: list[CatalogItemRead] = []
