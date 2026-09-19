"""Phase 7 — Commercial Configuration and Seller Restriction Models."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.seller import Seller
    from app.models.tenant import Tenant


class PaymentGatewayType(str, enum.Enum):
    TTC_GATEWAY = "TTC_GATEWAY"
    SELLER_GATEWAY = "SELLER_GATEWAY"


class SellerCommercialModel(str, enum.Enum):
    COMMISSION = "COMMISSION"
    SUBSCRIPTION = "SUBSCRIPTION"


class SellerRestrictionLevel(str, enum.Enum):
    NONE = "NONE"
    WARNING = "WARNING"
    MARKETPLACE_RESTRICTED = "MARKETPLACE_RESTRICTED"
    WHITE_LABEL_RESTRICTED = "WHITE_LABEL_RESTRICTED"
    FULL_SUSPENSION = "FULL_SUSPENSION"


class SellerCommercialConfiguration(Base):
    """Authoritative commercial terms and operational restriction parameters for a seller."""

    __tablename__ = "seller_commercial_configs"
    __table_args__ = (
        UniqueConstraint("seller_id", name="uq_seller_commercial_configs_seller_id"),
        Index("ix_seller_commercial_configs_seller_id", "seller_id"),
        Index("ix_seller_commercial_configs_tenant_id", "tenant_id"),
        Index("ix_seller_commercial_configs_restriction_level", "restriction_level"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False
    )

    # Gateway routing
    marketplace_gateway: Mapped[str] = mapped_column(
        String(50), default=PaymentGatewayType.TTC_GATEWAY.value, nullable=False
    )
    white_label_gateway: Mapped[str] = mapped_column(
        String(50), default=PaymentGatewayType.SELLER_GATEWAY.value, nullable=False
    )

    # Mutually exclusive commercial models (R2)
    commercial_model: Mapped[str] = mapped_column(
        String(50), default=SellerCommercialModel.COMMISSION.value, nullable=False
    )
    commission_rate_percent: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal("10.00"), nullable=False
    )
    subscription_fee: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), nullable=False
    )

    # Payment timing & failure modes (R1)
    payment_required_before_pickup: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    outstanding_receivable_allowed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    payment_deadline_days: Mapped[int] = mapped_column(default=1, nullable=False)

    # Active restriction level (R4)
    restriction_level: Mapped[str] = mapped_column(
        String(50), default=SellerRestrictionLevel.NONE.value, nullable=False
    )

    # Grace days and penalty rates (R2)
    overdue_grace_days: Mapped[int] = mapped_column(default=7, nullable=False)
    daily_penalty_rate: Mapped[Decimal] = mapped_column(
        Numeric(6, 4), default=Decimal("0.0010"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    @property
    def payment_gateway_type(self) -> str:
        return self.marketplace_gateway

    @payment_gateway_type.setter
    def payment_gateway_type(self, value: str | PaymentGatewayType) -> None:
        self.marketplace_gateway = value.value if isinstance(value, PaymentGatewayType) else value

    # Relationships
    seller: Mapped[Seller] = relationship("Seller")
    tenant: Mapped[Tenant] = relationship("Tenant")
