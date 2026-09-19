"""Pricing engine data models and enums for TTC Phase 5."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.catalog import Service, ServiceAddon, ServiceItem
    from app.models.seller import Branch, Seller
    from app.models.tenant import Tenant


class PriceBookScope(str, enum.Enum):
    """Precedence scope for price books."""
    PLATFORM_DEFAULT = "PLATFORM_DEFAULT"
    SELLER = "SELLER"
    BRANCH = "BRANCH"


class PriceBookStatus(str, enum.Enum):
    """Lifecycle status for price books."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class PriceRuleType(str, enum.Enum):
    """Unit calculation type for price rules."""
    FIXED = "FIXED"
    PER_ITEM = "PER_ITEM"
    PER_UNIT = "PER_UNIT"
    PER_WEIGHT = "PER_WEIGHT"


class ComponentType(str, enum.Enum):
    """Financial breakdown component category."""
    BASE_PRICE = "BASE_PRICE"
    SURCHARGE = "SURCHARGE"
    DISCOUNT = "DISCOUNT"
    TAX = "TAX"


class RateType(str, enum.Enum):
    """Specifies whether rate is an absolute amount or percentage."""
    FLAT = "FLAT"
    PERCENTAGE = "PERCENTAGE"


class PriceBook(Base):
    """Container for scoped pricing rules in TTC Phase 5."""
    __tablename__ = "price_books"
    __table_args__ = (
        Index("idx_price_books_tenant_scope", "tenant_id", "scope"),
        Index("idx_price_books_tenant_seller", "tenant_id", "seller_id"),
        Index("idx_price_books_tenant_branch", "tenant_id", "branch_id"),
        Index("idx_price_books_tenant_status", "tenant_id", "status"),
        Index("idx_price_books_seller_id", "seller_id"),
        Index("idx_price_books_branch_id", "branch_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    scope: Mapped[PriceBookScope] = mapped_column(
        SQLEnum(PriceBookScope, name="price_book_scope", native_enum=False, length=50),
        default=PriceBookScope.SELLER,
        nullable=False,
    )
    status: Mapped[PriceBookStatus] = mapped_column(
        SQLEnum(PriceBookStatus, name="price_book_status", native_enum=False, length=50),
        default=PriceBookStatus.DRAFT,
        nullable=False,
    )
    seller_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sellers.id", ondelete="CASCADE"), nullable=True
    )
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("seller_branches.id", ondelete="CASCADE"), nullable=True
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    tenant: Mapped[Tenant | None] = relationship("Tenant")
    seller: Mapped[Seller | None] = relationship("Seller")
    branch: Mapped[Branch | None] = relationship("Branch")
    rules: Mapped[list[PriceRule]] = relationship(
        "PriceRule", back_populates="price_book", cascade="all, delete-orphan"
    )


class PriceRule(Base):
    """Specific pricing calculation rule referencing catalog entities."""
    __tablename__ = "price_rules"
    __table_args__ = (
        Index("idx_price_rules_book_service", "price_book_id", "service_id"),
        Index("idx_price_rules_book_item", "price_book_id", "service_item_id"),
        Index("idx_price_rules_book_addon", "price_book_id", "service_addon_id"),
        Index("idx_price_rules_book_active", "price_book_id", "is_active"),
        Index("idx_price_rules_tenant_id", "tenant_id"),
        Index("idx_price_rules_tenant_book", "tenant_id", "price_book_id"),
        Index("idx_price_rules_service_lookup", "service_id", "service_item_id", "service_addon_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    price_book_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("price_books.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    service_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), nullable=True, index=True
    )
    service_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("service_items.id", ondelete="CASCADE"), nullable=True, index=True
    )
    service_addon_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("service_addons.id", ondelete="CASCADE"), nullable=True, index=True
    )

    rule_type: Mapped[PriceRuleType] = mapped_column(
        SQLEnum(PriceRuleType, name="price_rule_type", native_enum=False, length=50),
        nullable=False,
    )
    component_type: Mapped[ComponentType] = mapped_column(
        SQLEnum(ComponentType, name="component_type", native_enum=False, length=50),
        default=ComponentType.BASE_PRICE,
        nullable=False,
    )
    rate_type: Mapped[RateType] = mapped_column(
        SQLEnum(RateType, name="rate_type", native_enum=False, length=50),
        default=RateType.FLAT,
        nullable=False,
    )
    rate: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    effective_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    effective_to: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    price_book: Mapped[PriceBook] = relationship("PriceBook", back_populates="rules")
    tenant: Mapped[Tenant | None] = relationship("Tenant")
    service: Mapped[Service | None] = relationship("Service")
    service_item: Mapped[ServiceItem | None] = relationship("ServiceItem")
    service_addon: Mapped[ServiceAddon | None] = relationship("ServiceAddon")
