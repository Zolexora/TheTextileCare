"""Phase 7 — Billing Invoices and Settlement Models."""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.payment import Payment
    from app.models.seller import Seller
    from app.models.tenant import Tenant


class InvoiceStatus(str, enum.Enum):
    """Lifecycle states of a monthly seller billing invoice."""

    PENDING = "PENDING"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class SettlementStatus(str, enum.Enum):
    """Lifecycle states of a Monday seller settlement payout."""

    SCHEDULED = "SCHEDULED"
    PROCESSING = "PROCESSING"
    SETTLED = "SETTLED"
    FAILED = "FAILED"
    PENDING = "PENDING"


class SellerBillingInvoice(Base):
    """Monthly TTC billing invoice for a seller (commission + subscription + late penalties)."""

    __tablename__ = "seller_billing_invoices"
    __table_args__ = (
        UniqueConstraint("seller_id", "invoice_month", name="uq_seller_billing_invoices_seller_month"),
        Index("ix_seller_billing_invoices_seller_id", "seller_id"),
        Index("ix_seller_billing_invoices_tenant_id", "tenant_id"),
        Index("ix_seller_billing_invoices_status", "status"),
        Index("ix_seller_billing_invoices_due_date", "due_date"),
        Index("ix_seller_billing_invoices_seller_status", "seller_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False
    )

    invoice_month: Mapped[str] = mapped_column(String(7), nullable=False)  # format: "YYYY-MM"
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default=InvoiceStatus.PENDING.value, nullable=False
    )

    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    tax_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    penalty_total: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )

    paid_at: Mapped[datetime | None] = mapped_column(
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
    seller: Mapped[Seller] = relationship("Seller")
    tenant: Mapped[Tenant] = relationship("Tenant")


class SellerSettlement(Base):
    """Weekly Monday payout disbursement to seller for TTC_GATEWAY funds after 15-day cooling hold."""

    __tablename__ = "seller_settlements"
    __table_args__ = (
        UniqueConstraint("reference_id", name="uq_seller_settlements_reference_id"),
        Index("ix_seller_settlements_seller_id", "seller_id"),
        Index("ix_seller_settlements_tenant_id", "tenant_id"),
        Index("ix_seller_settlements_status", "status"),
        Index("ix_seller_settlements_scheduled_for", "scheduled_for"),
        Index("ix_seller_settlements_seller_scheduled", "seller_id", "scheduled_for"),
        Index("ix_seller_settlements_status_scheduled", "status", "scheduled_for"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False
    )

    gateway_type: Mapped[str] = mapped_column(
        String(50), default="TTC_GATEWAY", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), default=SettlementStatus.SCHEDULED.value, nullable=False
    )

    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    scheduled_for: Mapped[date] = mapped_column(Date, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reference_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
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
    payments: Mapped[list[Payment]] = relationship(
        "Payment", back_populates="settlement"
    )
    seller: Mapped[Seller] = relationship("Seller")
    tenant: Mapped[Tenant] = relationship("Tenant")
