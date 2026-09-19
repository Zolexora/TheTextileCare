"""Phase 7 — Commercial Configuration Pydantic v2 Schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.commercial import (
    PaymentGatewayType,
    SellerCommercialModel,
    SellerRestrictionLevel,
)

__all__ = [
    "PaymentGatewayType",
    "SellerCommercialModel",
    "SellerRestrictionLevel",
    "CommercialConfigBase",
    "CommercialConfigCreate",
    "CommercialConfigUpdate",
    "CommercialConfigResponse",
    "SellerRestrictionEvaluationResponse",
]


class CommercialConfigBase(BaseModel):
    commercial_model: SellerCommercialModel = SellerCommercialModel.COMMISSION
    commission_rate_percent: Decimal = Field(
        default=Decimal("10.00"), ge=Decimal("0.00"), le=Decimal("100.00")
    )
    subscription_fee: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))

    payment_gateway_type: PaymentGatewayType = PaymentGatewayType.TTC_GATEWAY
    marketplace_gateway: PaymentGatewayType = PaymentGatewayType.TTC_GATEWAY
    white_label_gateway: PaymentGatewayType = PaymentGatewayType.SELLER_GATEWAY

    payment_required_before_pickup: bool = True
    outstanding_receivable_allowed: bool = False
    payment_deadline_days: int = Field(default=1, ge=0)

    overdue_grace_days: int = Field(default=7, ge=0)
    daily_penalty_rate: Decimal = Field(
        default=Decimal("0.0010"), ge=Decimal("0.0000"), le=Decimal("1.0000")
    )

    overdue_warning_days: int = Field(default=1, ge=0)
    overdue_restriction_days: int = Field(default=7, ge=0)
    overdue_suspension_days: int = Field(default=30, ge=0)

    @model_validator(mode="after")
    def validate_mutual_exclusivity(self) -> CommercialConfigBase:
        """Enforces mutual exclusivity between Commission and Subscription models (R2)."""
        if self.commercial_model == SellerCommercialModel.COMMISSION:
            if self.commission_rate_percent <= Decimal("0.00"):
                raise ValueError("Commission model requires commission_rate_percent > 0.00.")
            if self.subscription_fee != Decimal("0.00"):
                raise ValueError("Commission model requires subscription_fee to be exactly 0.00.")
        elif self.commercial_model == SellerCommercialModel.SUBSCRIPTION:
            if self.subscription_fee <= Decimal("0.00"):
                raise ValueError("Subscription model requires subscription_fee > 0.00.")
            if self.commission_rate_percent != Decimal("0.00"):
                raise ValueError("Subscription model requires commission_rate_percent to be exactly 0.00.")
        return self


class CommercialConfigCreate(CommercialConfigBase):
    seller_id: uuid.UUID


class CommercialConfigUpdate(BaseModel):
    commercial_model: SellerCommercialModel | None = None
    commission_rate_percent: Decimal | None = Field(default=None, ge=Decimal("0.00"), le=Decimal("100.00"))
    subscription_fee: Decimal | None = Field(default=None, ge=Decimal("0.00"))

    payment_gateway_type: PaymentGatewayType | None = None
    marketplace_gateway: PaymentGatewayType | None = None
    white_label_gateway: PaymentGatewayType | None = None

    payment_required_before_pickup: bool | None = None
    outstanding_receivable_allowed: bool | None = None
    payment_deadline_days: int | None = Field(default=None, ge=0)

    overdue_grace_days: int | None = Field(default=None, ge=0)
    daily_penalty_rate: Decimal | None = Field(default=None, ge=Decimal("0.0000"), le=Decimal("1.0000"))

    overdue_warning_days: int | None = Field(default=None, ge=0)
    overdue_restriction_days: int | None = Field(default=None, ge=0)
    overdue_suspension_days: int | None = Field(default=None, ge=0)
    restriction_level: SellerRestrictionLevel | None = None

    @model_validator(mode="after")
    def validate_partial_mutual_exclusivity(self) -> CommercialConfigUpdate:
        if self.commercial_model is not None:
            if self.commercial_model == SellerCommercialModel.COMMISSION:
                if self.subscription_fee is not None and self.subscription_fee > Decimal("0.00"):
                    raise ValueError("Cannot set non-zero subscription_fee with COMMISSION model.")
            elif self.commercial_model == SellerCommercialModel.SUBSCRIPTION:
                if self.commission_rate_percent is not None and self.commission_rate_percent > Decimal("0.00"):
                    raise ValueError("Cannot set non-zero commission_rate_percent with SUBSCRIPTION model.")
        return self


class CommercialConfigResponse(CommercialConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    seller_id: uuid.UUID
    restriction_level: SellerRestrictionLevel
    created_at: datetime
    updated_at: datetime


class SellerRestrictionEvaluationResponse(BaseModel):
    seller_id: uuid.UUID
    previous_restriction_level: SellerRestrictionLevel
    new_restriction_level: SellerRestrictionLevel
    max_days_overdue: int
    overdue_invoices_count: int
    pending_orders_cancelled_count: int
    evaluated_at: datetime
