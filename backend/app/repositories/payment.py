"""Phase 7 — Payment Repository.

Data access layer for payment transactions, refunds, fee/tax ledgers, and cooling holds.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Sequence
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.payment import Payment, PaymentStatus, Refund
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository):
    """Database access for Payment and Refund entities."""

    # -------------------------------------------------------------------
    # Payments CRUD & Scoped Lookups
    # -------------------------------------------------------------------

    def create(self, payment: Payment) -> Payment:
        self.db.add(payment)
        self.db.flush()
        return payment

    def get_by_id(
        self, payment_id: uuid.UUID, tenant_id: uuid.UUID | None = None
    ) -> Payment | None:
        stmt = select(Payment).where(Payment.id == payment_id)
        if tenant_id:
            stmt = stmt.where(Payment.tenant_id == tenant_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_order_id(
        self, order_id: uuid.UUID, tenant_id: uuid.UUID | None = None
    ) -> Payment | None:
        stmt = select(Payment).where(Payment.order_id == order_id)
        if tenant_id:
            stmt = stmt.where(Payment.tenant_id == tenant_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_order_id_for_customer(
        self, order_id: uuid.UUID, customer_id: uuid.UUID
    ) -> Payment | None:
        stmt = select(Payment).where(
            Payment.order_id == order_id,
            Payment.customer_id == customer_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def update_status(
        self,
        payment_id: uuid.UUID,
        status: str,
        gateway_transaction_id: str | None = None,
        paid_at: datetime | None = None,
    ) -> Payment | None:
        payment = self.get_by_id(payment_id)
        if not payment:
            return None

        payment.status = status
        if gateway_transaction_id:
            payment.gateway_transaction_id = gateway_transaction_id
        if paid_at:
            payment.paid_at = paid_at
        elif status == PaymentStatus.SUCCEEDED.value and not payment.paid_at:
            payment.paid_at = func.now()

        self.db.flush()
        return payment

    # -------------------------------------------------------------------
    # Refund Operations & Retained Amount Adjustments
    # -------------------------------------------------------------------

    def create_refund(self, refund: Refund) -> Refund:
        self.db.add(refund)
        self.db.flush()
        return refund

    def list_refunds_for_payment(self, payment_id: uuid.UUID) -> Sequence[Refund]:
        stmt = select(Refund).where(Refund.payment_id == payment_id).order_by(Refund.created_at.asc())
        return self.db.execute(stmt).scalars().all()

    def update_retained_commission(
        self,
        payment_id: uuid.UUID,
        refunded_amount: Decimal,
        retained_amount: Decimal,
        ttc_commission: Decimal,
        ttc_commission_tax: Decimal,
        status: str,
    ) -> Payment | None:
        """Update payment financial balances following partial/full refund."""
        payment = self.get_by_id(payment_id)
        if not payment:
            return None

        payment.refunded_amount = refunded_amount
        payment.retained_amount = retained_amount
        payment.ttc_commission = ttc_commission
        payment.ttc_commission_tax = ttc_commission_tax
        payment.status = status
        self.db.flush()
        return payment

    # -------------------------------------------------------------------
    # Settlement Queries (TTC Gateway 15-Day Cooling Period)
    # -------------------------------------------------------------------

    def get_eligible_cooling_payments(
        self,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        cooling_cutoff: datetime,
    ) -> Sequence[Payment]:
        """Fetch payments eligible for Monday weekly settlement.
        
        Criteria:
        - TTC_GATEWAY transaction
        - SUCCEEDED status
        - Not yet settled (settled == False)
        - Cleared 15-day cooling period (paid_at <= cooling_cutoff)
        - Strictly scoped to seller_id and tenant_id
        """
        stmt = (
            select(Payment)
            .where(
                Payment.seller_id == seller_id,
                Payment.tenant_id == tenant_id,
                Payment.gateway_type == "TTC_GATEWAY",
                Payment.status == PaymentStatus.SUCCEEDED.value,
                Payment.settled == False,
                Payment.paid_at <= cooling_cutoff,
            )
            .order_by(Payment.paid_at.asc())
        )
        return self.db.execute(stmt).scalars().all()

    def mark_settled(self, payment_ids: list[uuid.UUID], settlement_id: uuid.UUID) -> int:
        """Batch mark payments as settled and link to SellerSettlement record."""
        if not payment_ids:
            return 0

        stmt = (
            select(Payment)
            .where(Payment.id.in_(payment_ids))
        )
        payments = self.db.execute(stmt).scalars().all()
        for p in payments:
            p.settled = True
            p.settlement_id = settlement_id
        self.db.flush()
        return len(payments)

    # -------------------------------------------------------------------
    # Paginated Listing
    # -------------------------------------------------------------------

    def list_by_seller(
        self,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[Payment], int]:
        base = select(Payment).where(
            Payment.seller_id == seller_id,
            Payment.tenant_id == tenant_id,
        )
        count_q = select(func.count()).select_from(Payment).where(
            Payment.seller_id == seller_id,
            Payment.tenant_id == tenant_id,
        )
        if status:
            base = base.where(Payment.status == status)
            count_q = count_q.where(Payment.status == status)

        total = self.db.execute(count_q).scalar() or 0
        items = (
            self.db.execute(
                base.order_by(Payment.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return items, total

    def list_by_customer(
        self,
        customer_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[Payment], int]:
        base = select(Payment).where(Payment.customer_id == customer_id)
        count_q = select(func.count()).select_from(Payment).where(Payment.customer_id == customer_id)

        total = self.db.execute(count_q).scalar() or 0
        items = (
            self.db.execute(
                base.order_by(Payment.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return items, total
