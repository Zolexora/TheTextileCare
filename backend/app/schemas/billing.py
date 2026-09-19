"""Phase 7 — Billing Invoices Pydantic v2 Schemas."""
from __future__ import annotations

import re
import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.billing import InvoiceStatus

__all__ = [
    "InvoiceStatus",
    "BillingInvoiceGenerateRequest",
    "BillingInvoicePayRequest",
    "BillingInvoiceResponse",
    "BillingInvoiceListResponse",
    "LatePenaltyCalculationResponse",
]

INVOICE_MONTH_REGEX = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class BillingInvoiceGenerateRequest(BaseModel):
    year: int = Field(..., ge=2020, le=2050)
    month: int = Field(..., ge=1, le=12)


class BillingInvoicePayRequest(BaseModel):
    payment_reference: str | None = Field(default=None, max_length=255)


class BillingInvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    seller_id: uuid.UUID
    invoice_month: str
    due_date: date
    status: InvoiceStatus
    currency: str

    subtotal: Decimal
    tax_total: Decimal
    penalty_total: Decimal
    total_amount: Decimal

    paid_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    @field_validator("invoice_month")
    @classmethod
    def validate_month_format(cls, v: str) -> str:
        if not INVOICE_MONTH_REGEX.match(v):
            raise ValueError(f"Invalid invoice_month: '{v}'. Must be 'YYYY-MM' format.")
        return v


class BillingInvoiceListResponse(BaseModel):
    items: list[BillingInvoiceResponse]
    total: int
    limit: int
    offset: int


class LatePenaltyCalculationResponse(BaseModel):
    invoice_id: uuid.UUID
    seller_id: uuid.UUID
    invoice_month: str
    due_date: date
    as_of_date: date
    days_overdue: int
    daily_penalty_rate: Decimal
    base_overdue_amount: Decimal
    calculated_penalty: Decimal
    total_amount: Decimal
    status: InvoiceStatus
