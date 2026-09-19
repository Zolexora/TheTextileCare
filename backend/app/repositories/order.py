"""Phase 7 — Order Repository.

Handles all database operations for orders, order items, add-ons,
and status history. Never performs business-rule validation — that
belongs in OrderService.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Sequence

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, selectinload

from app.models.order import Order, OrderItem, OrderItemAddon, OrderStatus, OrderStatusHistory
from app.repositories.base import BaseRepository


class OrderRepository(BaseRepository):
    """Database access for order entities."""

    # -------------------------------------------------------------------
    # Order number generation — concurrency-safe via DB sequence
    # -------------------------------------------------------------------

    def next_order_number(self) -> str:
        """Generate the next human-readable order number using a DB sequence.

        Creates the sequence idempotently so tests using create_all also work.
        """
        # Ensure sequence exists (idempotent — safe to call on every test run)
        self.db.execute(text("CREATE SEQUENCE IF NOT EXISTS order_number_seq START 1 INCREMENT 1"))
        self.db.flush()
        result = self.db.execute(text("SELECT nextval('order_number_seq')"))
        seq_val: int = result.scalar()
        year = datetime.now(timezone.utc).year
        return f"TTC-{year}-{seq_val:06d}"

    # -------------------------------------------------------------------
    # Order CRUD
    # -------------------------------------------------------------------

    def create(self, order: Order) -> Order:
        self.db.add(order)
        self.db.flush()
        return order

    def get_by_id(self, order_id: uuid.UUID) -> Order | None:
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.items).selectinload(OrderItem.addons),
                selectinload(Order.status_history),
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_order_number(self, order_number: str) -> Order | None:
        stmt = select(Order).where(Order.order_number == order_number)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_idempotency_key(
        self, customer_id: uuid.UUID, idempotency_key: str
    ) -> Order | None:
        stmt = (
            select(Order)
            .where(
                Order.customer_id == customer_id,
                Order.idempotency_key == idempotency_key,
            )
            .options(
                selectinload(Order.items).selectinload(OrderItem.addons),
                selectinload(Order.status_history),
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_customer(
        self,
        customer_id: uuid.UUID,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[Order], int]:
        base = select(Order).where(Order.customer_id == customer_id)
        count_base = select(func.count()).select_from(Order).where(Order.customer_id == customer_id)

        if status:
            base = base.where(Order.status == status)
            count_base = count_base.where(Order.status == status)

        total = self.db.execute(count_base).scalar() or 0
        orders = (
            self.db.execute(
                base.order_by(Order.created_at.desc(), Order.id.desc())
                .limit(limit)
                .offset(offset)
                .options(selectinload(Order.items).selectinload(OrderItem.addons))
            )
            .scalars()
            .all()
        )
        return orders, total

    def list_by_seller(
        self,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        status: str | None = None,
        branch_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        order_number: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[Order], int]:
        base = select(Order).where(
            Order.seller_id == seller_id,
            Order.tenant_id == tenant_id,
        )
        count_q = select(func.count()).select_from(Order).where(
            Order.seller_id == seller_id,
            Order.tenant_id == tenant_id,
        )

        filters: list[Any] = []
        if status:
            filters.append(Order.status == status)
        if branch_id:
            filters.append(Order.branch_id == branch_id)
        if customer_id:
            filters.append(Order.customer_id == customer_id)
        if order_number:
            filters.append(Order.order_number == order_number)
        if from_date:
            filters.append(Order.created_at >= from_date)
        if to_date:
            filters.append(Order.created_at <= to_date)

        for f in filters:
            base = base.where(f)
            count_q = count_q.where(f)

        total = self.db.execute(count_q).scalar() or 0
        orders = (
            self.db.execute(
                base.order_by(Order.created_at.desc(), Order.id.desc())
                .limit(limit)
                .offset(offset)
                .options(selectinload(Order.items).selectinload(OrderItem.addons))
            )
            .scalars()
            .all()
        )
        return orders, total

    def get_seller_order(
        self, order_id: uuid.UUID, seller_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> Order | None:
        stmt = (
            select(Order)
            .where(
                Order.id == order_id,
                Order.seller_id == seller_id,
                Order.tenant_id == tenant_id,
            )
            .options(
                selectinload(Order.items).selectinload(OrderItem.addons),
                selectinload(Order.status_history),
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_customer_order(
        self, order_id: uuid.UUID, customer_id: uuid.UUID
    ) -> Order | None:
        stmt = (
            select(Order)
            .where(
                Order.id == order_id,
                Order.customer_id == customer_id,
            )
            .options(
                selectinload(Order.items).selectinload(OrderItem.addons),
                selectinload(Order.status_history),
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    # -------------------------------------------------------------------
    # Order Items
    # -------------------------------------------------------------------

    def create_item(self, item: OrderItem) -> OrderItem:
        self.db.add(item)
        self.db.flush()
        return item

    # -------------------------------------------------------------------
    # Order Item Add-ons
    # -------------------------------------------------------------------

    def create_addon(self, addon: OrderItemAddon) -> OrderItemAddon:
        self.db.add(addon)
        self.db.flush()
        return addon

    # -------------------------------------------------------------------
    # Status History
    # -------------------------------------------------------------------

    def append_status_history(
        self,
        order_id: uuid.UUID,
        from_status: str | None,
        to_status: str,
        reason: str | None = None,
        actor_user_id: uuid.UUID | None = None,
    ) -> OrderStatusHistory:
        entry = OrderStatusHistory(
            order_id=order_id,
            from_status=from_status,
            to_status=to_status,
            reason=reason,
            actor_user_id=actor_user_id,
        )
        self.db.add(entry)
        self.db.flush()
        return entry
