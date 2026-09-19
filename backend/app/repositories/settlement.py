"""Phase 7 — Settlement Repository.

Data access layer for weekly Monday settlement disbursements, status transitions, and audit trails.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Sequence
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.billing import SellerSettlement, SettlementStatus
from app.repositories.base import BaseRepository


class SettlementRepository(BaseRepository):
    """Database access for SellerSettlement entities."""

    def create(self, settlement: SellerSettlement) -> SellerSettlement:
        self.db.add(settlement)
        self.db.flush()
        return settlement

    def get_by_id(
        self, settlement_id: uuid.UUID, tenant_id: uuid.UUID | None = None
    ) -> SellerSettlement | None:
        stmt = select(SellerSettlement).where(SellerSettlement.id == settlement_id)
        if tenant_id:
            stmt = stmt.where(SellerSettlement.tenant_id == tenant_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_scheduled_for_date(
        self,
        scheduled_for: date,
        status: str = SettlementStatus.SCHEDULED.value,
    ) -> Sequence[SellerSettlement]:
        """Fetch all settlements scheduled for a target Monday."""
        stmt = select(SellerSettlement).where(
            SellerSettlement.scheduled_for == scheduled_for,
            SellerSettlement.status == status,
        )
        return self.db.execute(stmt).scalars().all()

    def update_status(
        self,
        settlement_id: uuid.UUID,
        status: str,
        reference_id: str | None = None,
        processed_at: datetime | None = None,
    ) -> SellerSettlement | None:
        settlement = self.get_by_id(settlement_id)
        if not settlement:
            return None

        settlement.status = status
        if reference_id:
            settlement.reference_id = reference_id
        if processed_at:
            settlement.processed_at = processed_at
        elif status == SettlementStatus.SETTLED.value and not settlement.processed_at:
            settlement.processed_at = func.now()

        self.db.flush()
        return settlement

    def list_by_seller(
        self,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[SellerSettlement], int]:
        base = select(SellerSettlement).where(
            SellerSettlement.seller_id == seller_id,
            SellerSettlement.tenant_id == tenant_id,
        )
        count_q = select(func.count()).select_from(SellerSettlement).where(
            SellerSettlement.seller_id == seller_id,
            SellerSettlement.tenant_id == tenant_id,
        )
        if status:
            base = base.where(SellerSettlement.status == status)
            count_q = count_q.where(SellerSettlement.status == status)

        total = self.db.execute(count_q).scalar() or 0
        items = (
            self.db.execute(
                base.order_by(SellerSettlement.scheduled_for.desc(), SellerSettlement.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return items, total

    def list_all(
        self,
        status: str | None = None,
        scheduled_for: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[SellerSettlement], int]:
        base = select(SellerSettlement)
        count_q = select(func.count()).select_from(SellerSettlement)

        if status:
            base = base.where(SellerSettlement.status == status)
            count_q = count_q.where(SellerSettlement.status == status)
        if scheduled_for:
            base = base.where(SellerSettlement.scheduled_for == scheduled_for)
            count_q = count_q.where(SellerSettlement.scheduled_for == scheduled_for)

        total = self.db.execute(count_q).scalar() or 0
        items = (
            self.db.execute(
                base.order_by(SellerSettlement.scheduled_for.desc(), SellerSettlement.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            .scalars()
            .all()
        )
        return items, total
