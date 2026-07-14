from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.purchase import Purchase
from app.schemas.purchase import PurchaseCreate


def upsert_purchases(db: Session, purchases: list[PurchaseCreate]) -> tuple[int, int]:
    imported = 0
    updated = 0
    for item in purchases:
        existing = db.scalar(select(Purchase).where(Purchase.external_id == item.external_id))
        values = item.model_dump()
        if existing:
            for key, value in values.items():
                setattr(existing, key, value)
            updated += 1
        else:
            db.add(Purchase(**values))
            imported += 1
    db.commit()
    return imported, updated


def list_purchases(
    db: Session,
    *,
    query: str = "",
    status: str = "all",
    agency: str = "all",
    procedure_type: str = "all",
    currency: str = "all",
    unit: str = "all",
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[Purchase], int]:
    statement = select(Purchase)
    count_statement = select(func.count(Purchase.id))
    filters = []

    if query:
        pattern = f"%{query}%"
        filters.append(or_(Purchase.object.ilike(pattern), Purchase.supplier.ilike(pattern), Purchase.external_id.ilike(pattern)))
    if status != "all":
        filters.append(Purchase.status == status)
    if agency != "all":
        filters.append(Purchase.agency == agency)
    if procedure_type != "all":
        filters.append(Purchase.procedure_type.ilike(f"{procedure_type}%"))
    if currency != "all":
        filters.append(Purchase.currency == currency)
    if unit != "all":
        filters.append(Purchase.notes.ilike(f"%Unidad ejecutora: {unit}%"))

    for condition in filters:
        statement = statement.where(condition)
        count_statement = count_statement.where(condition)

    items = db.scalars(statement.order_by(Purchase.award_date.desc().nullslast()).limit(limit).offset(offset)).all()
    total = db.scalar(count_statement) or 0
    return list(items), total


def metrics(db: Session) -> dict[str, Decimal | int]:
    active = db.scalar(select(func.count(Purchase.id)).where(Purchase.status == "vigente")) or 0
    previous = db.scalar(select(func.count(Purchase.id)).where(Purchase.status == "anterior")) or 0
    total = db.scalar(select(func.coalesce(func.sum(Purchase.awarded_amount), 0)).where(Purchase.currency == "UYU")) or Decimal("0")
    count = db.scalar(select(func.count(Purchase.id)).where(Purchase.currency == "UYU")) or 0
    return {
        "active": active,
        "previous": previous,
        "awarded_total_uyu": total,
        "awarded_average_uyu": total / count if count else Decimal("0"),
    }


def distinct_values(db: Session, column_name: str) -> list[str]:
    column = getattr(Purchase, column_name)
    return list(db.scalars(select(column).distinct().order_by(column)).all())
