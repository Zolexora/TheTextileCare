from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from app.models.membership import Membership
from app.models.role import Role
from app.repositories.base import BaseRepository


class MembershipRepository(BaseRepository):
    def get_by_id(self, membership_id: uuid.UUID) -> Membership | None:
        stmt = (
            select(Membership)
            .options(
                joinedload(Membership.role),
                joinedload(Membership.user),
                joinedload(Membership.tenant),
            )
            .where(Membership.id == membership_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_tenant_and_user(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> Membership | None:
        stmt = (
            select(Membership)
            .options(
                joinedload(Membership.role),
                joinedload(Membership.user),
                joinedload(Membership.tenant),
            )
            .where(Membership.tenant_id == tenant_id, Membership.user_id == user_id)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_identifier_in_tenant(
        self, tenant_id: uuid.UUID, identifier: uuid.UUID
    ) -> Membership | None:
        stmt = (
            select(Membership)
            .options(
                joinedload(Membership.role),
                joinedload(Membership.user),
                joinedload(Membership.tenant),
            )
            .where(
                Membership.tenant_id == tenant_id,
                or_(Membership.id == identifier, Membership.user_id == identifier),
            )
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def create(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        role_name: str,
        status: str = 'ACTIVE',
    ) -> Membership:
        stmt = select(Role).where(Role.name == role_name)
        role = self.db.execute(stmt).scalar_one_or_none()
        if not role:
            raise ValueError(f"Role '{role_name}' does not exist")

        membership = Membership(
            tenant_id=tenant_id,
            user_id=user_id,
            role_id=role.id,
            status=status,
        )
        self.db.add(membership)
        self.db.commit()
        self.db.refresh(membership)
        # Re-fetch with loaded relationships
        return self.get_by_id(membership.id) or membership

    def list_for_tenant(self, tenant_id: uuid.UUID) -> list[Membership]:
        stmt = (
            select(Membership)
            .options(joinedload(Membership.role), joinedload(Membership.user))
            .where(Membership.tenant_id == tenant_id)
            .order_by(Membership.created_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def list_for_user(self, user_id: uuid.UUID) -> list[Membership]:
        stmt = (
            select(Membership)
            .options(joinedload(Membership.role), joinedload(Membership.tenant))
            .where(Membership.user_id == user_id, Membership.status == 'ACTIVE')
            .order_by(Membership.created_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_active_owners(self, tenant_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(Membership)
            .join(Role, Role.id == Membership.role_id)
            .where(
                Membership.tenant_id == tenant_id,
                Membership.status == 'ACTIVE',
                Role.name == 'TENANT_OWNER',
            )
        )
        return self.db.execute(stmt).scalar_one()

    def update(self, membership: Membership, **kwargs) -> Membership:
        for key, value in kwargs.items():
            if hasattr(membership, key):
                setattr(membership, key, value)
        self.db.commit()
        self.db.refresh(membership)
        return self.get_by_id(membership.id) or membership

    def delete(self, membership: Membership) -> None:
        self.db.delete(membership)
        self.db.commit()
