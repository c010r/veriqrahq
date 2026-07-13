from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class CatalogResource(Base):
    __tablename__ = "catalog_resources"
    __table_args__ = (UniqueConstraint("slug", name="uq_catalog_resources_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    slug: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text, default="")
    source_url: Mapped[str] = mapped_column(Text)
    item_count: Mapped[int] = mapped_column(default=0)
    synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    items: Mapped[list["CatalogItem"]] = relationship(back_populates="resource", cascade="all, delete-orphan")


class CatalogItem(Base):
    __tablename__ = "catalog_items"
    __table_args__ = (UniqueConstraint("resource_slug", "code", name="uq_catalog_items_resource_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    resource_id: Mapped[str] = mapped_column(ForeignKey("catalog_resources.id", ondelete="CASCADE"))
    resource_slug: Mapped[str] = mapped_column(String(120), index=True)
    code: Mapped[str] = mapped_column(String(120), index=True)
    label: Mapped[str] = mapped_column(Text)
    attrs: Mapped[dict] = mapped_column(JSON, default=dict)

    resource: Mapped[CatalogResource] = relationship(back_populates="items")
