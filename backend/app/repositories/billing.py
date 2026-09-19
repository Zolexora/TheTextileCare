"""Phase 7 — Billing Repository.

Data access layer for monthly seller billing invoices, overdue calculations, and late penalties.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Sequence
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.billing import InvoiceStatus, SellerBillingInvoice
from app.repositories.base import BaseRepository


class BillingRepository(BaseRepository):
    """Database access for SellerBillingInvoice entities."""

    def create(self, invoice: SellerBillingInvoice) -> SellerBillingInvoice:
        self.db.add(invoice)
        self.db.flush()
        return invoice

    def get_by_id(
        self, invoice_id: uuid.UUID, tenant_id: uuid.UUID | None = None
    ) -> SellerBillingInvoice | None:
        stmt = select(SellerBillingInvoice).where(SellerBillingInvoice.id == invoice_id)
        if tenant_id:
            stmt = stmt.where(SellerBillingInvoice.tenant_id == tenant_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_seller_and_month(
        self, seller_id: uuid.UUID, tenant_id: uuid.UUID, invoice_month: str | date
    ) -> SellerBillingInvoice | None:
        """Find invoice for a seller in a given month to guarantee idempotent invoice creation."""
        month_str = invoice_month if isinstance(invoice_month, str) else invoice_month.strftime("%Y-%m")
        stmt = select(SellerBillingInvoice).where(
            SellerBillingInvoice.seller_id == seller_id,
            SellerBillingInvoice.tenant_id == tenant_id,
            SellerBillingInvoice.invoice_month == month_str,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_overdue_invoices(
        self, as_of_date: date, tenant_id: uuid.UUID | None = None
    ) -> Sequence[SellerBillingInvoice]:
        """Fetch all invoices whose due_date has passed and are still unpaid."""
        stmt = (
            select(SellerBillingInvoice)
            .where(
                SellerBillingInvoice.status.in_([InvoiceStatus.PENDING.value, InvoiceStatus.OVERDUE.value]),
                SellerBillingInvoice.due_date < as_of_date,
            )
        )
        if tenant_id:
            stmt = stmt.where(SellerBillingInvoice.tenant_id == tenant_id)
        return self.db.execute(stmt).scalars().all()

    def get_max_overdue_days_for_seller(
        self, seller_id: uuid.UUID, as_of_date: date
    ) -> int:
        """Calculate the longest number of days overdue across all unpaid invoices for a seller."""
        stmt = select(SellerBillingInvoice).where(
            SellerBillingInvoice.seller_id == seller_id,
            SellerBillingInvoice.status.in_([InvoiceStatus.PENDING.value, InvoiceStatus.OVERDUE.value]),
            SellerBillingInvoice.due_date < as_of_date,
        )
        invoices = self.db.execute(stmt).scalars().all()
        if not invoices:
            return 0
        max_days = max((as_of_date - inv.due_date).days for inv in invoices)
        return max(max_days, 0)

    def update_penalty(
        self,
        invoice_id: uuid.UUID,
        penalty_total: Decimal,
        total_amount: Decimal,
        status: str = InvoiceStatus.OVERDUE.value,
    ) -> SellerBillingInvoice | None:
        """Idempotently update accrued late-payment penalties on an overdue invoice."""
        invoice = self.get_by_id(invoice_id)
        if not invoice:
            return None

        invoice.penalty_total = penalty_total
        invoice.total_amount = total_amount
        invoice.status = status
        self.db.flush()
        return invoice

    def mark_as_paid(
        self, invoice_id: uuid.UUID, paid_at: datetime | None = None
    ) -> SellerBillingInvoice | None:
        invoice = self.get_by_id(invoice_id)
        if not invoice:
            return None

        invoice.status = InvoiceStatus.PAID.value
        invoice.paid_at = paid_at or func.now()
        self.db.flush()
        return invoice

    def list_by_seller(
        self,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[SellerBillingInvoice], int]:
        base = select(SellerBillingInvoice).where(
            SellerBillingInvoice.seller_id == seller_id,
            SellerBillingInvoice.tenant_id == tenant_id,
        )
        count_q = select(func.count()).select_from(SellerBillingInvoice).where(
            SellerBillingInvoice.seller_id == seller_id,
            SellerBillingInvoice.tenant_id == tenant_id,
        )
        if status:
            base = base.where(SellerBillingInvoice.status == status)
            count_q = count_q.where(SellerBillingInvoice.status == status)

        total = self.db.execute(count_q).scalar() or 0
        items = (
            self.db.execute(
                base.order_by(SellerBillingInvoice.invoice_month.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return items, total

    def list_all(
        self,
        status: str | None = None,
        invoice_month: str | date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[SellerBillingInvoice], int]:
        base = select(SellerBillingInvoice)
        count_q = select(func.count()).select_from(SellerBillingInvoice)

        if status:
            base = base.where(SellerBillingInvoice.status == status)
            count_q = count_q.where(SellerBillingInvoice.status == status)
        if invoice_month:
            month_str = invoice_month if isinstance(invoice_month, str) else invoice_month.strftime("%Y-%m")
            base = base.where(SellerBillingInvoice.invoice_month == month_str)
            count_q = count_q.where(SellerBillingInvoice.invoice_month == month_str)

        total = self.db.execute(count_q).scalar() or 0
        items = (
            self.db.execute(
                base.order_by(SellerBillingInvoice.invoice_month.desc(), SellerBillingInvoice.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return items, total
