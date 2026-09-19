"""Phase 7 — Commercial Repository.

Data access layer for seller commercial configurations and restriction statuses.
Ensures strict tenant and seller isolation.
"""
from __future__ import annotations

import uuid
from typing import Any, Sequence
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.commercial import SellerCommercialConfiguration, SellerRestrictionLevel
from app.repositories.base import BaseRepository


class CommercialRepository(BaseRepository):
    """Database access for SellerCommercialConfiguration entities."""

    def create(self, config: SellerCommercialConfiguration) -> SellerCommercialConfiguration:
        self.db.add(config)
        self.db.flush()
        return config

    def get_by_seller_id(
        self, tenant_id: uuid.UUID, seller_id: uuid.UUID
    ) -> SellerCommercialConfiguration | None:
        """Fetch commercial config scoped to both tenant_id and seller_id."""
        stmt = select(SellerCommercialConfiguration).where(
            SellerCommercialConfiguration.tenant_id == tenant_id,
            SellerCommercialConfiguration.seller_id == seller_id,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_seller_id_unscoped(
        self, seller_id: uuid.UUID
    ) -> SellerCommercialConfiguration | None:
        """Unscoped lookup for internal background services (e.g. restriction worker)."""
        stmt = select(SellerCommercialConfiguration).where(
            SellerCommercialConfiguration.seller_id == seller_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def update(
        self,
        tenant_id: uuid.UUID,
        seller_id: uuid.UUID,
        **kwargs: Any,
    ) -> SellerCommercialConfiguration | None:
        """Update commercial configuration fields scoped to tenant."""
        config = self.get_by_seller_id(tenant_id=tenant_id, seller_id=seller_id)
        if not config:
            return None

        for key, value in kwargs.items():
            if hasattr(config, key) and value is not None:
                setattr(config, key, value)

        self.db.flush()
        return config

    def update_restriction_level(
        self,
        seller_id: uuid.UUID,
        restriction_level: str,
    ) -> SellerCommercialConfiguration | None:
        """Update restriction level for a seller."""
        config = self.get_by_seller_id_unscoped(seller_id)
        if not config:
            return None

        config.restriction_level = restriction_level
        self.db.flush()
        return config

    def list_restricted_sellers(
        self, restriction_level: str | None = None
    ) -> Sequence[SellerCommercialConfiguration]:
        """List all sellers with operational restrictions."""
        stmt = select(SellerCommercialConfiguration).where(
            SellerCommercialConfiguration.restriction_level != SellerRestrictionLevel.NONE.value
        )
        if restriction_level:
            stmt = stmt.where(SellerCommercialConfiguration.restriction_level == restriction_level)
        return self.db.execute(stmt).scalars().all()

    def list_all(
        self, limit: int = 50, offset: int = 0
    ) -> tuple[Sequence[SellerCommercialConfiguration], int]:
        """Platform admin paginated listing of all commercial configurations."""
        count_q = select(func.count()).select_from(SellerCommercialConfiguration)
        total = self.db.execute(count_q).scalar() or 0

        stmt = (
            select(SellerCommercialConfiguration)
            .order_by(SellerCommercialConfiguration.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        items = self.db.execute(stmt).scalars().all()
        return items, total
