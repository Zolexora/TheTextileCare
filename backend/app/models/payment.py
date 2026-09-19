"""Phase 7 — Payment and Refund Domain Models.

Enforces financial ledger fee/tax separation, cooling hold tracking, and refunds.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.billing import SellerSettlement
    from app.models.customer import Customer
    from app.models.order import Order
    from app.models.seller import Seller
    from app.models.tenant import Tenant


class PaymentStatus(str, enum.Enum):
    """Authoritative lifecycle states of a customer order payment."""

    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    OUTSTANDING = "OUTSTANDING"
    REFUNDED = "REFUNDED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"


class Payment(Base):
    """Authoritative financial record of a customer payment for an order."""

    __tablename__ = "payments"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_payments_order_id"),
        Index("ix_payments_order_id", "order_id"),
        Index("ix_payments_tenant_id", "tenant_id"),
        Index("ix_payments_seller_id", "seller_id"),
        Index("ix_payments_customer_id", "customer_id"),
        Index("ix_payments_status", "status"),
        Index("ix_payments_settlement_id", "settlement_id"),
        Index("ix_payments_settled_paid_at", "settled", "paid_at"),
        Index("ix_payments_seller_settled", "seller_id", "settled"),
        Index("ix_payments_due_date", "due_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )

    gateway_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default=PaymentStatus.PENDING.value, nullable=False
    )

    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Gateway financial components (isolated from platform revenue)
    gateway_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    gateway_tax: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )

    # TTC Commercial components (platform commission)
    ttc_commission: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    ttc_commission_tax: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )

    # Refunds & Retained balance
    refunded_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    retained_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )

    # Settlement tracking (R3)
    settled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    settlement_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("seller_settlements.id", ondelete="SET NULL"), nullable=True
    )

    gateway_transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    order: Mapped[Order] = relationship("Order", back_populates="payment")
    refunds: Mapped[list[Refund]] = relationship(
        "Refund", back_populates="payment", cascade="all, delete-orphan"
    )
    settlement: Mapped[SellerSettlement | None] = relationship(
        "SellerSettlement", back_populates="payments"
    )
    seller: Mapped[Seller] = relationship("Seller")
    customer: Mapped[Customer] = relationship("Customer")
    tenant: Mapped[Tenant] = relationship("Tenant")


class Refund(Base):
    """Record of a refund against a Payment."""

    __tablename__ = "refunds"
    __table_args__ = (
        Index("ix_refunds_payment_id", "payment_id"),
        Index("ix_refunds_tenant_id", "tenant_id"),
        Index("ix_refunds_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payments.id", ondelete="CASCADE"), nullable=False
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    commission_deduction: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    gateway_fee_reversed: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    gateway_tax_reversed: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )

    gateway_refund_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    payment: Mapped[Payment] = relationship("Payment", back_populates="refunds")
    tenant: Mapped[Tenant] = relationship("Tenant")
