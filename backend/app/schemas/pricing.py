"""Pydantic V2 schemas for TTC Phase 5 Pricing Engine Foundation.

Defines request/response DTOs for Price Books, Price Rules, and Deterministic
Pricing Calculations with strict validation and Decimal precision.
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.pricing import (
    ComponentType,
    PriceBookScope,
    PriceBookStatus,
    PriceRuleType,
    RateType,
)

# Re-export enums for schema consumers
__all__ = [
    "PriceBookScope",
    "PriceBookStatus",
    "PriceRuleType",
    "ComponentType",
    "RateType",
    "PriceBookBase",
    "PriceBookCreate",
    "PriceBookUpdate",
    "PriceBookResponse",
    "PriceBookListParams",
    "PriceRuleBase",
    "PriceRuleCreate",
    "PriceRuleUpdate",
    "PriceRuleResponse",
    "PricingCalculationItemRequest",
    "PricingCalculationRequest",
    "PricingCalculationComponentBreakdown",
    "PricingCalculationItemResult",
    "PricingCalculationResult",
    "validate_currency_code",
]


# ============================================================================
# Currency Helper / Validator
# ============================================================================

CURRENCY_REGEX = re.compile(r"^[A-Z]{3}$")


def validate_currency_code(v: str) -> str:
    normalized = v.strip().upper()
    if not CURRENCY_REGEX.match(normalized):
        raise ValueError(f"Invalid ISO 4217 currency code: '{v}'. Must be a 3-letter uppercase string.")
    return normalized


# ============================================================================
# PriceBook Schemas
# ============================================================================

class PriceBookBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Descriptive name of the price book")
    description: str | None = Field(None, max_length=1000, description="Optional detailed description")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="ISO 4217 currency code")
    priority: int = Field(default=0, description="Priority tie-breaker for conflicting books")
    is_default: bool = Field(default=False, description="Whether this is the default book for seller/branch")
    is_active: bool = Field(default=True, description="Whether this price book is active")

    @field_validator("currency")
    @classmethod
    def check_currency(cls, v: str) -> str:
        return validate_currency_code(v)


class PriceBookCreate(PriceBookBase):
    scope: PriceBookScope | None = Field(
        default=None,
        description="Applicability scope (PLATFORM_DEFAULT, SELLER, BRANCH)."
    )
    seller_id: uuid.UUID | None = Field(None, description="Target seller if scope is SELLER or BRANCH")
    branch_id: uuid.UUID | None = Field(None, description="Target branch if scope is BRANCH")
    status: PriceBookStatus = Field(default=PriceBookStatus.DRAFT, description="Initial lifecycle status")

    @model_validator(mode="after")
    def validate_scope_and_identifiers(self) -> PriceBookCreate:
        if self.scope is None:
            if self.branch_id is not None:
                self.scope = PriceBookScope.BRANCH
            elif self.seller_id is not None:
                self.scope = PriceBookScope.SELLER
            else:
                self.scope = PriceBookScope.PLATFORM_DEFAULT

        if self.scope == PriceBookScope.PLATFORM_DEFAULT:
            if self.seller_id is not None or self.branch_id is not None:
                raise ValueError("PLATFORM_DEFAULT price books must not have seller_id or branch_id.")
        elif self.scope == PriceBookScope.SELLER:
            if self.seller_id is None:
                raise ValueError("SELLER scope price books require a valid seller_id.")
            if self.branch_id is not None:
                raise ValueError("SELLER scope price books must not have a branch_id.")
        elif self.scope == PriceBookScope.BRANCH:
            if self.seller_id is None or self.branch_id is None:
                raise ValueError("BRANCH scope price books require both seller_id and branch_id.")
        return self


class PriceBookUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=1000)
    currency: str | None = Field(None, min_length=3, max_length=3)
    priority: int | None = None
    is_default: bool | None = None
    is_active: bool | None = None
    status: PriceBookStatus | None = None

    @field_validator("currency")
    @classmethod
    def check_currency(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_currency_code(v)
        return v


class PriceBookResponse(PriceBookBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    scope: PriceBookScope
    status: PriceBookStatus
    seller_id: uuid.UUID | None
    branch_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    rules_count: int | None = None


class PriceBookListParams(BaseModel):
    scope: PriceBookScope | None = None
    seller_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    is_active: bool | None = None
    status: PriceBookStatus | None = None
    include_platform_defaults: bool = Field(default=True, description="Whether to include PLATFORM_DEFAULT books")


# ============================================================================
# PriceRule Schemas
# ============================================================================

class PriceRuleBase(BaseModel):
    name: str | None = Field(None, max_length=255, description="Optional human-readable rule name")
    description: str | None = Field(None, max_length=1000, description="Optional detailed description")
    service_id: uuid.UUID | None = Field(None, description="Catalog service target")
    service_item_id: uuid.UUID | None = Field(None, description="Specific catalog service item target")
    service_addon_id: uuid.UUID | None = Field(None, description="Specific catalog addon target")
    rule_type: PriceRuleType = Field(default=PriceRuleType.FIXED, description="Rule calculation type")
    component_type: ComponentType = Field(default=ComponentType.BASE_PRICE, description="Component tier")
    rate_type: RateType = Field(default=RateType.FLAT, description="FLAT or PERCENTAGE")
    rate: Decimal = Field(..., ge=Decimal("0.00"), description="Monetary rate or percentage")
    status: str = Field(default="ACTIVE", max_length=50, description="Rule lifecycle status")
    is_active: bool = Field(default=True, description="Whether this rule is active")
    priority: int = Field(default=0, description="Tie-breaking priority within same specificity level")
    effective_from: datetime | None = Field(None, description="Start of temporal validity window")
    effective_to: datetime | None = Field(None, description="End of temporal validity window")

    @model_validator(mode="after")
    def validate_effective_date_range(self) -> PriceRuleBase:
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be greater than or equal to effective_from.")
        return self


class PriceRuleCreate(PriceRuleBase):
    pass


class PriceRuleUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=1000)
    service_id: uuid.UUID | None = None
    service_item_id: uuid.UUID | None = None
    service_addon_id: uuid.UUID | None = None
    rule_type: PriceRuleType | None = None
    component_type: ComponentType | None = None
    rate_type: RateType | None = None
    rate: Decimal | None = Field(None, ge=Decimal("0.00"))
    status: str | None = Field(None, max_length=50)
    is_active: bool | None = None
    priority: int | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None

    @model_validator(mode="after")
    def validate_effective_date_range(self) -> PriceRuleUpdate:
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("effective_to must be greater than or equal to effective_from.")
        return self


class PriceRuleResponse(PriceRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    price_book_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Deterministic Pricing Calculation Schemas
# ============================================================================

class PricingCalculationItemRequest(BaseModel):
    service_id: uuid.UUID = Field(..., description="Target catalog service ID")
    service_item_id: uuid.UUID | None = Field(None, description="Target catalog service item ID")
    quantity: Decimal = Field(default=Decimal("1"), gt=Decimal("0"), description="Item quantity (must be > 0)")
    weight: Decimal | None = Field(None, ge=Decimal("0"), description="Item weight in kg for PER_WEIGHT rules")
    unit_type: str = Field(default="ITEM", max_length=50, description="Unit type (ITEM, KG, PAIR, SET)")
    addon_ids: list[uuid.UUID] = Field(default_factory=list, description="Selected addon IDs for this item")


class PricingCalculationRequest(BaseModel):
    seller_id: uuid.UUID = Field(..., description="Target seller")
    branch_id: uuid.UUID | None = Field(None, description="Optional branch for branch-level overrides")
    currency: str = Field(default="USD", min_length=3, max_length=3, description="Calculation currency")
    calculation_time: datetime | None = Field(
        None, description="Reference datetime for effective dates (defaults to UTC now)"
    )
    calculation_date: datetime | None = Field(
        None, description="Alias for calculation_time"
    )
    items: list[PricingCalculationItemRequest] = Field(
        ..., min_length=1, description="List of items to calculate pricing for"
    )

    @field_validator("currency")
    @classmethod
    def check_currency(cls, v: str) -> str:
        return validate_currency_code(v)

    @model_validator(mode="after")
    def sync_calculation_time(self) -> PricingCalculationRequest:
        if self.calculation_time is None and self.calculation_date is not None:
            self.calculation_time = self.calculation_date
        return self


class PricingCalculationComponentBreakdown(BaseModel):
    name: str = Field(..., description="Name of rule or component")
    component_type: ComponentType
    rate_type: RateType
    rate: Decimal = Field(..., description="Configured rate or percentage")
    amount: Decimal = Field(..., description="Evaluated monetary impact (positive Decimal)")


class PricingCalculationItemResult(BaseModel):
    service_id: uuid.UUID
    service_item_id: uuid.UUID | None = None
    unit_price: Decimal = Field(..., description="Base rate per unit/item before multipliers")
    quantity: Decimal
    weight: Decimal | None = None
    base_price: Decimal = Field(..., description="Total base price for line item (rate * qty/weight)")
    surcharges: Decimal = Field(default=Decimal("0.00"), description="Total surcharges applied")
    discounts: Decimal = Field(default=Decimal("0.00"), description="Total discounts applied")
    tax: Decimal = Field(default=Decimal("0.00"), description="Total tax applied")
    subtotal: Decimal = Field(..., description="Line subtotal (base_price)")
    total: Decimal = Field(..., description="Line total (base_price + surcharges - discounts + tax)")
    applied_rule_ids: list[uuid.UUID] = Field(default_factory=list, description="IDs of rules matched")
    breakdown: list[PricingCalculationComponentBreakdown] = Field(default_factory=list)


class PricingCalculationResult(BaseModel):
    currency: str
    subtotal: Decimal = Field(..., description="Sum of all item base prices")
    total_surcharges: Decimal = Field(..., description="Sum of all surcharges across items")
    total_discounts: Decimal = Field(..., description="Sum of all discounts across items")
    total_tax: Decimal = Field(..., description="Sum of all taxes across items")
    grand_total: Decimal = Field(..., description="Subtotal + surcharges - discounts + tax")
    items: list[PricingCalculationItemResult] = Field(..., description="Detailed per-item calculation results")

    @model_validator(mode="after")
    def validate_grand_total_invariant(self) -> PricingCalculationResult:
        expected = self.subtotal + self.total_surcharges - self.total_discounts + self.total_tax
        if self.grand_total != expected:
            raise ValueError(
                f"Grand total invariant violated: grand_total ({self.grand_total}) "
                f"!= subtotal ({self.subtotal}) + surcharges ({self.total_surcharges}) "
                f"- discounts ({self.total_discounts}) + tax ({self.total_tax}) [Expected: {expected}]"
            )
        return self
