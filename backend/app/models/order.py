"""Phase 7 — Order Foundation models.

The Order is the authoritative historical record of what a customer requested
and what price was agreed at order creation. All commercial fields are
immutable after creation; evolution happens via explicit status transitions.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    JSON,
    Numeric,
    Sequence as SASequence,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.seller import Branch, Seller
    from app.models.tenant import Tenant
    from app.models.user import User

# ---------------------------------------------------------------------------
# Database-level sequence for concurrency-safe order number generation.
# Defined here so Base.metadata.create_all() creates it automatically in tests.
# ---------------------------------------------------------------------------
order_number_seq = SASequence("order_number_seq", start=1, increment=1)


class OrderStatus(str, enum.Enum):
    """Explicit order lifecycle states."""

    DRAFT = "DRAFT"
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# Allowed status transitions — enforced at the domain layer.
ALLOWED_TRANSITIONS: dict[OrderStatus, list[OrderStatus]] = {
    OrderStatus.DRAFT: [OrderStatus.PENDING, OrderStatus.CANCELLED],
    OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
    OrderStatus.CONFIRMED: [OrderStatus.IN_PROGRESS, OrderStatus.CANCELLED],
    OrderStatus.IN_PROGRESS: [OrderStatus.COMPLETED],
    OrderStatus.COMPLETED: [],
    OrderStatus.CANCELLED: [],
}

# Statuses that a customer is allowed to cancel from.
CUSTOMER_CANCELLABLE_STATUSES: set[OrderStatus] = {
    OrderStatus.DRAFT,
    OrderStatus.PENDING,
    OrderStatus.CONFIRMED,
}

# Statuses that a seller is allowed to cancel from.
SELLER_CANCELLABLE_STATUSES: set[OrderStatus] = {
    OrderStatus.PENDING,
    OrderStatus.CONFIRMED,
}


class Order(Base):
    """
    Authoritative historical record of a customer transaction.

    Commercial fields (items, prices, snapshots, currency, totals) are
    immutable after creation. Status evolves via controlled transitions only.
    """

    __tablename__ = "orders"
    __table_args__ = (
        UniqueConstraint("order_number", name="uq_order_order_number"),
        # Idempotency: same customer cannot create two orders with the same key.
        # The constraint is partial (customer_id, idempotency_key) but SQLAlchemy
        # UniqueConstraint handles NULLs correctly in PostgreSQL (NULLs are distinct).
        UniqueConstraint("customer_id", "idempotency_key", name="uq_order_customer_idempotency"),
        Index("ix_orders_customer_id_created_at", "customer_id", "created_at"),
        Index("ix_orders_seller_id_created_at", "seller_id", "created_at"),
        Index("ix_orders_branch_id_created_at", "branch_id", "created_at"),
        Index("ix_orders_tenant_id_status", "tenant_id", "status"),
        Index("ix_orders_status_created_at", "status", "created_at"),
        Index("ix_orders_order_number", "order_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sellers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("seller_branches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Human-readable business reference — generated from the DB sequence.
    order_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)

    # Lifecycle
    status: Mapped[str] = mapped_column(
        String(50), default=OrderStatus.PENDING.value, nullable=False, index=True
    )

    # Currency (ISO 4217 — 3 letters)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)

    # Monetary totals — persisted from the authoritative PricingService result.
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    surcharge_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    tax_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    grand_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Immutable snapshots — JSON columns for historical integrity.
    pricing_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    catalog_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    customer_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    customer_address_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Idempotency key (customer-scoped)
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Timestamps
    placed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    tenant: Mapped[Tenant] = relationship("Tenant")
    seller: Mapped[Seller] = relationship("Seller")
    branch: Mapped[Branch] = relationship("Branch")
    customer: Mapped[Customer] = relationship("Customer")
    items: Mapped[list[OrderItem]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    status_history: Mapped[list[OrderStatusHistory]] = relationship(
        "OrderStatusHistory",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="OrderStatusHistory.created_at",
    )


class OrderItem(Base):
    """Line item within an order — preserves catalog and pricing snapshot at creation time."""

    __tablename__ = "order_items"
    __table_args__ = (
        Index("ix_order_items_order_id", "order_id"),
        Index("ix_order_items_service_id", "service_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )

    # Foreign key references (for analytics/joins — NOT the historical source of truth).
    service_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("services.id", ondelete="SET NULL"), nullable=True
    )
    service_item_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("service_items.id", ondelete="SET NULL"), nullable=True
    )

    # Catalog snapshots — immutable historical record.
    service_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    service_item_name_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)
    unit_type: Mapped[str] = mapped_column(String(50), nullable=False, default="ITEM")

    # Quantity and pricing — from authoritative PricingService result.
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    surcharge_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Per-item pricing snapshot for full audit / historical reproduction.
    pricing_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    order: Mapped[Order] = relationship("Order", back_populates="items")
    addons: Mapped[list[OrderItemAddon]] = relationship(
        "OrderItemAddon", back_populates="order_item", cascade="all, delete-orphan"
    )


class OrderItemAddon(Base):
    """Add-on selected for an OrderItem — fully snapshotted at creation time."""

    __tablename__ = "order_item_addons"
    __table_args__ = (
        Index("ix_order_item_addons_order_item_id", "order_item_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("order_items.id", ondelete="CASCADE"), nullable=False
    )
    service_addon_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("service_addons.id", ondelete="SET NULL"), nullable=True
    )

    # Snapshot
    addon_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)

    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False, default=Decimal("1"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    surcharge_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    pricing_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    order_item: Mapped[OrderItem] = relationship("OrderItem", back_populates="addons")


class OrderStatusHistory(Base):
    """Immutable record of every status transition for an order."""

    __tablename__ = "order_status_history"
    __table_args__ = (
        Index("ix_order_status_history_order_id_created_at", "order_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    from_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    to_status: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    order: Mapped[Order] = relationship("Order", back_populates="status_history")
