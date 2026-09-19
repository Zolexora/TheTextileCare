"""Phase 7 — Order Pickup Repository.

Data access layer for physical garment pickup lifecycles and detail approvals.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Sequence
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.pickup import OrderPickup, PickupStatus
from app.repositories.base import BaseRepository


class PickupRepository(BaseRepository):
    """Database access for OrderPickup entities."""

    def create(self, pickup: OrderPickup) -> OrderPickup:
        self.db.add(pickup)
        self.db.flush()
        return pickup

    def get_by_id(
        self, pickup_id: uuid.UUID, tenant_id: uuid.UUID | None = None
    ) -> OrderPickup | None:
        stmt = select(OrderPickup).where(OrderPickup.id == pickup_id)
        if tenant_id:
            stmt = stmt.where(OrderPickup.tenant_id == tenant_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_order_id(
        self, order_id: uuid.UUID, tenant_id: uuid.UUID | None = None
    ) -> OrderPickup | None:
        """Fetch pickup by order_id, optionally validating tenant ownership."""
        stmt = select(OrderPickup).where(OrderPickup.order_id == order_id)
        if tenant_id:
            stmt = stmt.where(OrderPickup.tenant_id == tenant_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_order_id_for_customer(
        self, order_id: uuid.UUID, customer_id: uuid.UUID
    ) -> OrderPickup | None:
        """Fetch pickup ensuring the associated order belongs to the customer."""
        stmt = (
            select(OrderPickup)
            .join(Order, Order.id == OrderPickup.order_id)
            .where(
                OrderPickup.order_id == order_id,
                Order.customer_id == customer_id,
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def submit_actual_details(
        self,
        order_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actual_details: dict[str, Any],
        actual_pickup_at: datetime | None = None,
    ) -> OrderPickup | None:
        """Seller submits verified pickup details; transitions status to DETAILS_SUBMITTED."""
        pickup = self.get_by_order_id(order_id, tenant_id)
        if not pickup:
            return None

        pickup.actual_details = actual_details
        pickup.details_submitted_at = func.now()
        if actual_pickup_at:
            pickup.actual_pickup_at = actual_pickup_at
        pickup.status = PickupStatus.DETAILS_SUBMITTED.value
        self.db.flush()
        return pickup

    def approve_details(
        self, order_id: uuid.UUID, customer_id: uuid.UUID
    ) -> OrderPickup | None:
        """Customer approves pickup details; transitions status to APPROVED."""
        pickup = self.get_by_order_id_for_customer(order_id, customer_id)
        if not pickup:
            return None

        pickup.status = PickupStatus.APPROVED.value
        pickup.approved_at = func.now()
        self.db.flush()
        return pickup

    def reject_details(
        self, order_id: uuid.UUID, customer_id: uuid.UUID, reason: str
    ) -> OrderPickup | None:
        """Customer rejects pickup details; transitions status to REJECTED."""
        pickup = self.get_by_order_id_for_customer(order_id, customer_id)
        if not pickup:
            return None

        pickup.status = PickupStatus.REJECTED.value
        pickup.rejection_reason = reason
        self.db.flush()
        return pickup

    def complete_pickup(
        self, order_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> OrderPickup | None:
        """Seller completes pickup physical workflow; transitions status to COMPLETED."""
        pickup = self.get_by_order_id(order_id, tenant_id)
        if not pickup:
            return None

        pickup.status = PickupStatus.COMPLETED.value
        self.db.flush()
        return pickup

    def list_by_seller(
        self,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[OrderPickup], int]:
        """Paginated pickup listing scoped to seller and tenant."""
        base = select(OrderPickup).where(
            OrderPickup.seller_id == seller_id,
            OrderPickup.tenant_id == tenant_id,
        )
        count_q = select(func.count()).select_from(OrderPickup).where(
            OrderPickup.seller_id == seller_id,
            OrderPickup.tenant_id == tenant_id,
        )

        if status:
            base = base.where(OrderPickup.status == status)
            count_q = count_q.where(OrderPickup.status == status)

        total = self.db.execute(count_q).scalar() or 0
        items = (
            self.db.execute(
                base.order_by(OrderPickup.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return items, total
