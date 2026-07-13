from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PurchaseBase(BaseModel):
    external_id: str
    status: str
    procedure_type: str
    agency: str
    object: str
    supplier: str = "Sin proveedor informado"
    award_date: date | None = None
    closing_date: date | None = None
    currency: str = "UYU"
    awarded_amount: Decimal = Decimal("0")
    quantity: Decimal = Decimal("1")
    unit_price: Decimal = Decimal("0")
    source: str = "ARCE"
    source_url: str = ""
    notes: str = ""


class PurchaseCreate(PurchaseBase):
    pass


class PurchaseRead(PurchaseBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PurchaseList(BaseModel):
    items: list[PurchaseRead]
    total: int
    active: int
    previous: int
    awarded_total_uyu: Decimal
    awarded_average_uyu: Decimal


class ImportResult(BaseModel):
    imported: int
    updated: int
    skipped: int = 0
    message: str = Field(default="Importacion finalizada")
