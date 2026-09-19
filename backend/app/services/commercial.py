"""Phase 7 — Commercial Configuration Service.

Handles get-or-create commercial config, config updates, and seller restriction
evaluation with automatic PENDING marketplace order cancellation.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions.base import ApiError
from app.models.commercial import (
    PaymentGatewayType,
    SellerCommercialConfiguration,
    SellerCommercialModel,
    SellerRestrictionLevel,
)
from app.repositories.billing import BillingRepository
from app.repositories.commercial import CommercialRepository
from app.schemas.commercial import (
    CommercialConfigUpdate,
    SellerRestrictionEvaluationResponse,
)


class CommercialService:
    """Business logic for seller commercial configuration and restriction evaluation."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = CommercialRepository(db)
        self.billing_repo = BillingRepository(db)

    # -------------------------------------------------------------------
    # Config CRUD
    # -------------------------------------------------------------------

    def get_or_create_commercial_config(
        self,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> SellerCommercialConfiguration:
        """Return the seller's commercial config, creating defaults if absent."""
        config = self.repo.get_by_seller_id(tenant_id=tenant_id, seller_id=seller_id)
        if config:
            return config

        config = SellerCommercialConfiguration(
            seller_id=seller_id,
            tenant_id=tenant_id,
        )
        config = self.repo.create(config)
        self.db.commit()
        return config

    def update_commercial_config(
        self,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        update_data: CommercialConfigUpdate,
    ) -> SellerCommercialConfiguration:
        """Apply partial updates to the seller's commercial config."""
        config = self.get_or_create_commercial_config(seller_id, tenant_id)

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if value is not None and hasattr(config, key):
                setattr(config, key, value.value if hasattr(value, "value") else value)

        self.db.flush()
        self.db.commit()
        self.db.refresh(config)
        return config

    # -------------------------------------------------------------------
    # Restriction evaluation
    # -------------------------------------------------------------------

    def evaluate_seller_restriction(
        self,
        seller_id: uuid.UUID,
        as_of_date: date | None = None,
    ) -> SellerRestrictionEvaluationResponse:
        """Evaluate overdue invoices and apply the appropriate restriction level.

        If the seller escalates to MARKETPLACE_RESTRICTED, all PENDING
        marketplace orders are cancelled with a standard reason string.
        """
        if as_of_date is None:
            as_of_date = date.today()

        config = self.repo.get_by_seller_id_unscoped(seller_id)
        if not config:
            raise ApiError(
                status_code=404,
                code="COMMERCIAL_CONFIG_NOT_FOUND",
                message=f"No commercial configuration found for seller {seller_id}.",
            )

        previous_level = SellerRestrictionLevel(config.restriction_level)
        max_days_overdue = self.billing_repo.get_max_overdue_days_for_seller(
            seller_id=seller_id, as_of_date=as_of_date
        )

        # Count overdue invoices
        overdue_invoices = self.billing_repo.get_overdue_invoices(
            as_of_date=as_of_date
        )
        overdue_count = sum(1 for inv in overdue_invoices if inv.seller_id == seller_id)

        new_level = self._compute_restriction_level(config, max_days_overdue)

        cancelled_count = 0
        if (
            new_level == SellerRestrictionLevel.MARKETPLACE_RESTRICTED
            and previous_level != SellerRestrictionLevel.MARKETPLACE_RESTRICTED
        ):
            cancelled_count = self._cancel_pending_marketplace_orders(seller_id)

        self.repo.update_restriction_level(
            seller_id=seller_id,
            restriction_level=new_level.value,
        )
        self.db.commit()

        return SellerRestrictionEvaluationResponse(
            seller_id=seller_id,
            previous_restriction_level=previous_level,
            new_restriction_level=new_level,
            max_days_overdue=max_days_overdue,
            overdue_invoices_count=overdue_count,
            pending_orders_cancelled_count=cancelled_count,
            evaluated_at=datetime.now(timezone.utc),
        )

    # -------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------

    def _compute_restriction_level(
        self,
        config: SellerCommercialConfiguration,
        max_days_overdue: int,
    ) -> SellerRestrictionLevel:
        """Map days-overdue to restriction level using configurable thresholds."""
        suspension_days = getattr(config, "overdue_suspension_days", 30)
        restriction_days = getattr(config, "overdue_restriction_days", 7)
        warning_days = getattr(config, "overdue_warning_days", 1)

        if max_days_overdue <= 0:
            return SellerRestrictionLevel.NONE
        if max_days_overdue >= suspension_days:
            return SellerRestrictionLevel.FULL_SUSPENSION
        if max_days_overdue >= restriction_days:
            return SellerRestrictionLevel.MARKETPLACE_RESTRICTED
        if max_days_overdue >= warning_days:
            return SellerRestrictionLevel.WARNING
        return SellerRestrictionLevel.NONE

    def _cancel_pending_marketplace_orders(self, seller_id: uuid.UUID) -> int:
        """Cancel all PENDING orders for a marketplace-restricted seller."""
        from app.models.order import Order, OrderStatus

        orders = (
            self.db.execute(
                select(Order).where(
                    Order.seller_id == seller_id,
                    Order.status == OrderStatus.PENDING.value,
                )
            )
            .scalars()
            .all()
        )

        for order in orders:
            order.status = OrderStatus.CANCELLED.value
            order.cancellation_reason = (
                "SELLER_RESTRICTED: Seller overdue restriction applied"
            )

        self.db.flush()
        return len(orders)
