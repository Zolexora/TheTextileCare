"""Phase 7 — Payment & Refund Pydantic v2 Schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.commercial import PaymentGatewayType
from app.models.payment import PaymentStatus

__all__ = [
    "PaymentStatus",
    "PaymentGatewayType",
    "PaymentInitiateRequest",
    "PaymentProcessRequest",
    "PaymentResponse",
    "PaymentLedgerBreakdownResponse",
    "RefundCreateRequest",
    "RefundResponse",
    "PaymentListResponse",
]


class PaymentInitiateRequest(BaseModel):
    idempotency_key: str | None = Field(default=None, max_length=255)


class PaymentProcessRequest(BaseModel):
    payment_method: str = Field(default="CARD", max_length=50)
    payment_token: str | None = None
    idempotency_key: str | None = Field(default=None, max_length=255)
    simulate_failure: bool = False  # Supports testing dual failure modes


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    order_id: uuid.UUID
    seller_id: uuid.UUID
    customer_id: uuid.UUID

    gateway_type: PaymentGatewayType
    status: PaymentStatus
    currency: str
    amount: Decimal

    # Financial ledger fee/tax separation (R1, R5)
    gateway_fee: Decimal = Decimal("0.00")
    gateway_tax: Decimal = Decimal("0.00")
    ttc_commission: Decimal = Decimal("0.00")
    ttc_commission_tax: Decimal = Decimal("0.00")

    refunded_amount: Decimal = Decimal("0.00")
    retained_amount: Decimal = Decimal("0.00")

    settled: bool = False
    settlement_id: uuid.UUID | None = None
    gateway_transaction_id: str | None = None

    paid_at: datetime | None = None
    due_date: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PaymentLedgerBreakdownResponse(BaseModel):
    payment_id: uuid.UUID
    order_id: uuid.UUID
    currency: str
    gross_customer_payment: Decimal
    gateway_fee: Decimal
    gateway_tax: Decimal
    ttc_commission: Decimal
    ttc_commission_tax: Decimal
    net_seller_share: Decimal
    refunded_amount: Decimal
    retained_amount: Decimal


class RefundCreateRequest(BaseModel):
    amount: Decimal = Field(..., gt=Decimal("0.00"))
    reason: str = Field(..., min_length=1, max_length=1000)
    idempotency_key: str | None = Field(default=None, max_length=255)


class RefundResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    payment_id: uuid.UUID
    amount: Decimal
    reason: str | None = None
    commission_deduction: Decimal = Decimal("0.00")
    gateway_fee_reversed: Decimal = Decimal("0.00")
    gateway_tax_reversed: Decimal = Decimal("0.00")
    gateway_refund_id: str | None = None
    created_at: datetime


class PaymentListResponse(BaseModel):
    items: list[PaymentResponse]
    total: int
    limit: int
    offset: int
