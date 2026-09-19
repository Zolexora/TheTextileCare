"""Phase 7 — Order Pickup Pydantic v2 Schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.pickup import PickupStatus

__all__ = [
    "PickupStatus",
    "PickupActualItemDetail",
    "PickupDetailsSubmitRequest",
    "PickupDetailsApproveRequest",
    "PickupDetailsRejectRequest",
    "PickupResponse",
    "PickupListResponse",
]


class PickupActualItemDetail(BaseModel):
    service_id: uuid.UUID
    service_item_id: uuid.UUID | None = None
    item_name: str
    verified_quantity: Decimal = Field(..., gt=Decimal("0"))
    measured_weight_kg: Decimal | None = Field(default=None, ge=Decimal("0"))
    fabric_notes: str | None = None
    detected_stains_or_damages: list[str] = Field(default_factory=list)


class PickupDetailsSubmitRequest(BaseModel):
    actual_details: dict[str, Any] = Field(
        ...,
        description="Authoritative inspection details including verified items, counts, and weights."
    )
    driver_notes: str | None = Field(default=None, max_length=1000)


class PickupDetailsApproveRequest(BaseModel):
    customer_notes: str | None = Field(default=None, max_length=1000)


class PickupDetailsRejectRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)


class PickupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    order_id: uuid.UUID
    seller_id: uuid.UUID
    status: PickupStatus

    actual_details: dict[str, Any] | None = None
    driver_notes: str | None = None
    customer_notes: str | None = None
    rejection_reason: str | None = None

    actual_pickup_at: datetime | None = None
    details_submitted_at: datetime | None = None
    approved_at: datetime | None = None
    completed_at: datetime | None = None

    created_at: datetime
    updated_at: datetime


class PickupListResponse(BaseModel):
    items: list[PickupResponse]
    total: int
    limit: int
    offset: int
