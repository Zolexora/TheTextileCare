"""Phase 7 — Billing Service.

Monthly invoice management, commission recording, late penalties, and payment marking.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.core.exceptions.base import ApiError
from app.models.billing import InvoiceStatus, SellerBillingInvoice
from app.repositories.billing import BillingRepository
from app.repositories.commercial import CommercialRepository
from app.repositories.payment import PaymentRepository

_TWO_DP = Decimal("0.01")
_GST = Decimal("0.18")


def _round(value: Decimal) -> Decimal:
    return value.quantize(_TWO_DP, rounding=ROUND_HALF_UP)


class BillingService:
    """Business logic for monthly seller billing invoices."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = BillingRepository(db)
        self.commercial_repo = CommercialRepository(db)
        self.payment_repo = PaymentRepository(db)

    # -------------------------------------------------------------------
    # Invoice lifecycle
    # -------------------------------------------------------------------

    def get_or_create_monthly_invoice(
        self,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        month: str,  # "YYYY-MM"
        currency: str = "INR",
    ) -> SellerBillingInvoice:
        """Idempotent: return existing invoice for the month or create a new one."""
        existing = self.repo.get_by_seller_and_month(
            seller_id=seller_id, tenant_id=tenant_id, invoice_month=month
        )
        if existing:
            return existing

        year_int, month_int = (int(p) for p in month.split("-"))
        # Due date: last day of the month following invoice month
        if month_int == 12:
            due_year, due_month = year_int + 1, 1
        else:
            due_year, due_month = year_int, month_int + 1
        import calendar
        last_day = calendar.monthrange(due_year, due_month)[1]
        due_date = date(due_year, due_month, last_day)

        invoice = SellerBillingInvoice(
            seller_id=seller_id,
            tenant_id=tenant_id,
            invoice_month=month,
            due_date=due_date,
            currency=currency,
            status=InvoiceStatus.PENDING.value,
        )
        invoice = self.repo.create(invoice)
        self.db.commit()
        return invoice

    def record_commission_charge(
        self,
        payment_id: uuid.UUID,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> SellerBillingInvoice:
        """Called when a payment succeeds; add TTC commission to the monthly invoice."""
        payment = self.payment_repo.get_by_id(payment_id, tenant_id=tenant_id)
        if not payment:
            raise ApiError(
                status_code=404,
                code="PAYMENT_NOT_FOUND",
                message=f"Payment {payment_id} not found.",
            )

        config = self.commercial_repo.get_by_seller_id(
            tenant_id=tenant_id, seller_id=seller_id
        )
        commission_rate = (
            Decimal(str(config.commission_rate_percent))
            if config
            else Decimal("10.00")
        )

        retained = Decimal(str(payment.retained_amount))
        commission = _round(retained * commission_rate / Decimal("100"))
        gst = _round(commission * _GST)

        # Find or create invoice for the payment's month
        paid_at = payment.paid_at or datetime.now(timezone.utc)
        if hasattr(paid_at, "year"):
            month_str = f"{paid_at.year:04d}-{paid_at.month:02d}"
        else:
            now = datetime.now(timezone.utc)
            month_str = f"{now.year:04d}-{now.month:02d}"

        invoice = self.get_or_create_monthly_invoice(
            seller_id=seller_id,
            tenant_id=tenant_id,
            month=month_str,
            currency=payment.currency,
        )

        invoice.subtotal = _round(Decimal(str(invoice.subtotal)) + commission)
        invoice.tax_total = _round(Decimal(str(invoice.tax_total)) + gst)
        invoice.total_amount = _round(
            Decimal(str(invoice.subtotal))
            + Decimal(str(invoice.tax_total))
            + Decimal(str(invoice.penalty_total))
        )
        self.db.flush()
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def apply_daily_penalties(self, as_of_date: date | None = None) -> int:
        """Idempotently apply late-payment penalties to all overdue invoices.

        penalty = max_overdue_days * daily_penalty_rate_amount
        """
        if as_of_date is None:
            as_of_date = date.today()

        overdue_invoices = self.repo.get_overdue_invoices(as_of_date=as_of_date)
        penalized = 0

        for invoice in overdue_invoices:
            days_overdue = (as_of_date - invoice.due_date).days
            if days_overdue <= 0:
                continue

            config = self.commercial_repo.get_by_seller_id(
                tenant_id=invoice.tenant_id, seller_id=invoice.seller_id
            )
            daily_rate = (
                Decimal(str(config.daily_penalty_rate))
                if config
                else Decimal("0.0010")
            )
            base_amount = Decimal(str(invoice.subtotal)) + Decimal(str(invoice.tax_total))
            penalty = _round(Decimal(str(days_overdue)) * daily_rate * base_amount)

            new_total = _round(
                Decimal(str(invoice.subtotal))
                + Decimal(str(invoice.tax_total))
                + penalty
            )
            self.repo.update_penalty(
                invoice_id=invoice.id,
                penalty_total=penalty,
                total_amount=new_total,
                status=InvoiceStatus.OVERDUE.value,
            )
            penalized += 1

        self.db.commit()
        return penalized

    def mark_invoice_paid(
        self,
        invoice_id: uuid.UUID,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> SellerBillingInvoice:
        """Mark a seller invoice as paid."""
        invoice = self.repo.get_by_id(invoice_id=invoice_id, tenant_id=tenant_id)
        if not invoice:
            raise ApiError(
                status_code=404,
                code="INVOICE_NOT_FOUND",
                message=f"Invoice {invoice_id} not found.",
            )
        if invoice.seller_id != seller_id:
            raise ApiError(
                status_code=403,
                code="INVOICE_ACCESS_DENIED",
                message="Invoice does not belong to this seller.",
            )
        if invoice.status == InvoiceStatus.PAID.value:
            return invoice

        result = self.repo.mark_as_paid(
            invoice_id=invoice_id,
            paid_at=datetime.now(timezone.utc),
        )
        self.db.commit()
        return result
