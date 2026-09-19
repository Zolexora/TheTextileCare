"""Phase 7 — Settlement Service.

Weekly Monday settlement disbursement: scheduling, querying, and batch processing.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.exceptions.base import ApiError
from app.models.billing import SellerSettlement, SettlementStatus
from app.models.commercial import PaymentGatewayType
from app.repositories.settlement import SettlementRepository


def _next_monday_at_least_n_days_out(today: date, min_days: int = 15) -> date:
    """Return the next Monday that is at least min_days from today.

    Iterates forward from today + min_days until a Monday is found.
    """
    candidate = today + timedelta(days=min_days)
    # weekday() == 0 is Monday
    while candidate.weekday() != 0:
        candidate += timedelta(days=1)
    return candidate


class SettlementService:
    """Business logic for TTC_GATEWAY settlement scheduling and processing."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = SettlementRepository(db)

    def schedule_settlement(
        self,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        payment_id: uuid.UUID,
        amount: Decimal,
        currency: str,
    ) -> SellerSettlement:
        """Create a SCHEDULED settlement for a TTC_GATEWAY payment.

        The settlement date is the next Monday that is >= 15 days from today.
        """
        today = date.today()
        scheduled_for = _next_monday_at_least_n_days_out(today, min_days=15)

        settlement = SellerSettlement(
            seller_id=seller_id,
            tenant_id=tenant_id,
            gateway_type=PaymentGatewayType.TTC_GATEWAY.value,
            status=SettlementStatus.SCHEDULED.value,
            currency=currency,
            amount=amount,
            scheduled_for=scheduled_for,
        )
        settlement = self.repo.create(settlement)
        # Caller (PaymentService) owns the commit
        return settlement

    def get_settlements_for_seller(
        self,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list, int]:
        """Paginated list of settlements for a seller."""
        items, total = self.repo.list_by_seller(
            seller_id=seller_id,
            tenant_id=tenant_id,
            limit=limit,
            offset=offset,
        )
        return list(items), total

    def process_monday_settlements(
        self,
        as_of_date: date | None = None,
    ) -> int:
        """Mark all SCHEDULED settlements whose scheduled_for <= as_of_date as SETTLED."""
        if as_of_date is None:
            as_of_date = date.today()

        from sqlalchemy import select
        from app.models.billing import SellerSettlement, SettlementStatus

        stmt = (
            select(SellerSettlement)
            .where(
                SellerSettlement.status == SettlementStatus.SCHEDULED.value,
                SellerSettlement.scheduled_for <= as_of_date,
            )
        )
        settlements = self.db.execute(stmt).scalars().all()

        processed = 0
        for settlement in settlements:
            self.repo.update_status(
                settlement_id=settlement.id,
                status=SettlementStatus.SETTLED.value,
                processed_at=datetime.now(timezone.utc),
            )
            # Mark linked payments as settled
            from app.models.payment import Payment
            payments = (
                self.db.query(Payment)
                .filter(Payment.settlement_id == settlement.id)
                .all()
            )
            for p in payments:
                p.settled = True
            self.db.flush()
            processed += 1

        self.db.commit()
        return processed
