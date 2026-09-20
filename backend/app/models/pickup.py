"""Phase 7 — Order Pickup Domain Model.

Tracks physical garment collection, driver inspection snapshots,
and customer verification before payment is requested.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.seller import Seller
    from app.models.tenant import Tenant


class PickupStatus(str, enum.Enum):
    """Lifecycle states of the physical garment pickup process."""

    SCHEDULED = "SCHEDULED"
    DETAILS_SUBMITTED = "DETAILS_SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PRICE_DISPUTE = "PRICE_DISPUTE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class OrderPickup(Base):
    """Authoritative physical pickup and inspection record for an Order.
    
    Customer approval of submitted details triggers payment collection.
    """

    __tablename__ = "order_pickups"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_order_pickups_order_id"),
        Index("ix_order_pickups_order_id", "order_id"),
        Index("ix_order_pickups_tenant_id", "tenant_id"),
        Index("ix_order_pickups_seller_id", "seller_id"),
        Index("ix_order_pickups_status", "status"),
        Index("ix_order_pickups_seller_status", "seller_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sellers.id", ondelete="RESTRICT"), nullable=False
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), nullable=False
    )

    status: Mapped[str] = mapped_column(
        String(50), default=PickupStatus.SCHEDULED.value, nullable=False
    )

    actual_pickup_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    details_submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(
        String(1000), nullable=True
    )
    actual_details: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True
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
    order: Mapped[Order] = relationship("Order", back_populates="pickup")
    tenant: Mapped[Tenant] = relationship("Tenant")
    seller: Mapped[Seller] = relationship("Seller")
