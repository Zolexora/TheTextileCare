"""Phase 7 — Order Foundation Pydantic schemas.

All monetary values use Decimal. Client-submitted totals are never trusted;
the backend always recalculates via PricingService.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.order import OrderStatus


# ---------------------------------------------------------------------------
# Snapshot schemas — stored as JSON for historical immutability
# ---------------------------------------------------------------------------

class CatalogSnapshot(BaseModel):
    """Immutable snapshot of catalog entities at order creation time."""
    service_id: str
    service_name: str
    service_item_id: str | None = None
    service_item_name: str | None = None
    unit_type: str = "ITEM"
    addon_id: str | None = None
    addon_name: str | None = None


class PricingSnapshot(BaseModel):
    """Full authoritative pricing result snapshot."""
    currency: str
    subtotal: str
    total_surcharges: str
    total_discounts: str
    total_tax: str
    grand_total: str
    items: list[dict[str, Any]] = Field(default_factory=list)


class CustomerSnapshot(BaseModel):
    """Customer display info snapshot at order creation."""
    customer_id: str
    display_name: str | None = None
    phone: str | None = None
    email: str | None = None


class AddressSnapshot(BaseModel):
    """Customer address snapshot — immutable at order creation."""
    recipient_name: str | None = None
    phone: str | None = None
    address_line_1: str
    address_line_2: str | None = None
    locality: str | None = None
    city: str
    state: str
    postal_code: str
    country: str = "IN"


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class OrderAddonRequest(BaseModel):
    """Add-on item in an order creation request."""
    service_addon_id: uuid.UUID
    quantity: Decimal = Field(default=Decimal("1"), gt=Decimal("0"))


class OrderItemRequest(BaseModel):
    """Line item in an order creation request."""
    service_id: uuid.UUID
    service_item_id: uuid.UUID | None = None
    quantity: Decimal = Field(default=Decimal("1"), gt=Decimal("0"))
    weight: Decimal | None = Field(default=None, ge=Decimal("0"))
    unit_type: str = Field(default="ITEM", max_length=50)
    addons: list[OrderAddonRequest] = Field(default_factory=list)


class OrderCreateRequest(BaseModel):
    """Customer order creation request.

    The backend ignores any submitted totals and always recalculates via
    the PricingService. `previewed_grand_total` is used only to detect
    price changes since the customer last saw pricing.
    """
    seller_id: uuid.UUID
    branch_id: uuid.UUID
    currency: str = Field(default="INR", min_length=3, max_length=3)
    items: list[OrderItemRequest] = Field(..., min_length=1)
    customer_address_id: uuid.UUID | None = None
    previewed_grand_total: Decimal | None = Field(
        default=None,
        description="Total the customer saw on the marketplace page. "
                    "If supplied and different from calculated, returns 409 PRICE_CHANGED.",
    )
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def check_currency(self) -> "OrderCreateRequest":
        self.currency = self.currency.strip().upper()
        if len(self.currency) != 3 or not self.currency.isalpha():
            raise ValueError("currency must be a 3-letter ISO 4217 code")
        return self


class OrderCancelRequest(BaseModel):
    """Request to cancel an order."""
    cancellation_reason: str = Field(..., min_length=1, max_length=1000)


class OrderStatusTransitionRequest(BaseModel):
    """Generic seller-side status transition request."""
    reason: str | None = Field(default=None, max_length=1000)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class OrderAddonResponse(BaseModel):
    """Add-on line in an order response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    service_addon_id: uuid.UUID | None
    addon_name_snapshot: str
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal
    discount_amount: Decimal
    surcharge_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal


class OrderItemResponse(BaseModel):
    """Order line item in a response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    service_id: uuid.UUID | None
    service_item_id: uuid.UUID | None
    service_name_snapshot: str
    service_item_name_snapshot: str | None
    unit_type: str
    quantity: Decimal
    unit_price: Decimal
    subtotal: Decimal
    discount_amount: Decimal
    surcharge_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    addons: list[OrderAddonResponse] = Field(default_factory=list)


class OrderStatusHistoryResponse(BaseModel):
    """Single status transition record."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    from_status: str | None
    to_status: str
    reason: str | None
    created_at: datetime


class OrderResponse(BaseModel):
    """Full order detail response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_number: str
    status: str
    currency: str

    subtotal: Decimal
    discount_total: Decimal
    surcharge_total: Decimal
    tax_total: Decimal
    grand_total: Decimal

    seller_id: uuid.UUID
    branch_id: uuid.UUID
    customer_id: uuid.UUID

    # Snapshots
    pricing_snapshot: dict[str, Any]
    catalog_snapshot: dict[str, Any]
    customer_snapshot: dict[str, Any]
    customer_address_snapshot: dict[str, Any] | None

    placed_at: datetime
    confirmed_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    cancellation_reason: str | None

    created_at: datetime
    updated_at: datetime

    items: list[OrderItemResponse] = Field(default_factory=list)
    status_history: list[OrderStatusHistoryResponse] = Field(default_factory=list)


class OrderListItem(BaseModel):
    """Compact order summary for list views."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_number: str
    status: str
    currency: str
    grand_total: Decimal
    seller_id: uuid.UUID
    branch_id: uuid.UUID
    customer_id: uuid.UUID
    placed_at: datetime
    created_at: datetime
    items_count: int = 0


class OrderListResponse(BaseModel):
    """Paginated list of orders."""
    items: list[OrderListItem]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Price-changed error payload
# ---------------------------------------------------------------------------

class PriceChangedDetail(BaseModel):
    """Returned in 409 PRICE_CHANGED responses."""
    previewed_grand_total: Decimal
    current_grand_total: Decimal
    currency: str
    message: str = "The price has changed since you last viewed this item. Please confirm the new price."


# ---------------------------------------------------------------------------
# Order Reselect Request (Phase 7 R4)
# ---------------------------------------------------------------------------

class OrderReselectRequest(BaseModel):
    """Customer request to re-select an alternative seller after restriction cancellation (R4)."""
    new_seller_id: uuid.UUID
    new_branch_id: uuid.UUID

