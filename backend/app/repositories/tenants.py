from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.models.membership import Membership
from app.models.tenant import Tenant
from app.repositories.base import BaseRepository


class TenantRepository(BaseRepository):
    def get_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        return self.db.get(Tenant, tenant_id)

    def get_by_slug(self, slug: str) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.slug == slug)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, name: str, slug: str, status: str = 'ACTIVE') -> Tenant:
        existing = self.get_by_slug(slug)
        if existing:
            return existing
        tenant = Tenant(name=name, slug=slug, status=status)
        self.db.add(tenant)
        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def update(self, tenant: Tenant, **kwargs) -> Tenant:
        for key, value in kwargs.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        self.db.commit()
        self.db.refresh(tenant)
        return tenant

    def list_for_user(self, user_id: uuid.UUID) -> list[Tenant]:
        stmt = (
            select(Tenant)
            .join(Membership, Membership.tenant_id == Tenant.id)
            .where(Membership.user_id == user_id, Membership.status == 'ACTIVE')
            .order_by(Tenant.created_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_all(self, limit: int = 50, offset: int = 0) -> list[Tenant]:
        stmt = select(Tenant).order_by(Tenant.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def count_all(self) -> int:
        stmt = select(func.count()).select_from(Tenant)
        return self.db.execute(stmt).scalar_one()
