from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Date, DateTime, Numeric, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Purchase(Base):
    __tablename__ = "purchases"
    __table_args__ = (UniqueConstraint("external_id", name="uq_purchases_external_id"),)

    id: Mapped[str] = mapped_column(Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    external_id: Mapped[str] = mapped_column(String(180), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    procedure_type: Mapped[str] = mapped_column(String(160), index=True)
    agency: Mapped[str] = mapped_column(String(240), index=True)
    object: Mapped[str] = mapped_column(Text)
    supplier: Mapped[str] = mapped_column(String(240), default="Sin proveedor informado")
    award_date: Mapped[date | None] = mapped_column(Date, index=True)
    closing_date: Mapped[date | None] = mapped_column(Date, index=True)
    currency: Mapped[str] = mapped_column(String(12), default="UYU")
    awarded_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    source: Mapped[str] = mapped_column(String(260), default="ARCE")
    source_url: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
