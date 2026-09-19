"""Phase 7 — Settlement Payout Pydantic v2 Schemas."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.billing import SettlementStatus
from app.models.commercial import PaymentGatewayType

__all__ = [
    "SettlementStatus",
    "SettlementGenerateRequest",
    "SettlementProcessRequest",
    "SettlementResponse",
    "SettlementListResponse",
    "SettlementEligibleBatchPreviewResponse",
]


class SettlementGenerateRequest(BaseModel):
    target_date: date | None = Field(
        default=None,
        description="Target Monday date for batch settlement generation. Defaults to current date/next Monday."
    )


class SettlementProcessRequest(BaseModel):
    settlement_ids: list[uuid.UUID] = Field(..., min_length=1)


class SettlementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    seller_id: uuid.UUID
    gateway_type: PaymentGatewayType
    status: SettlementStatus
    currency: str
    amount: Decimal

    scheduled_for: date
    processed_at: datetime | None = None
    reference_id: str | None = None

    created_at: datetime
    updated_at: datetime


class SettlementListResponse(BaseModel):
    items: list[SettlementResponse]
    total: int
    limit: int
    offset: int


class SettlementEligibleBatchPreviewResponse(BaseModel):
    target_date: date
    cooling_cutoff_timestamp: datetime
    seller_id: uuid.UUID
    eligible_transactions_count: int
    total_net_settlement_amount: Decimal
