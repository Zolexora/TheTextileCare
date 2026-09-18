from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository):
    def get_by_id(self, role_id: uuid.UUID) -> Role | None:
        stmt = select(Role).options(selectinload(Role.permissions)).where(Role.id == role_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_name(self, name: str) -> Role | None:
        stmt = select(Role).options(selectinload(Role.permissions)).where(Role.name == name)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_all(self) -> list[Role]:
        stmt = select(Role).options(selectinload(Role.permissions)).order_by(Role.name.asc())
        return list(self.db.execute(stmt).scalars().all())

    def create(
        self,
        name: str,
        description: str | None = None,
        is_platform_role: bool = False,
    ) -> Role:
        role = Role(name=name, description=description, is_platform_role=is_platform_role)
        self.db.add(role)
        self.db.commit()
        self.db.refresh(role)
        return role

    def get_permission_by_name(self, name: str) -> Permission | None:
        stmt = select(Permission).where(Permission.name == name)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_all_permissions(self) -> list[Permission]:
        stmt = select(Permission).order_by(Permission.name.asc())
        return list(self.db.execute(stmt).scalars().all())

    def create_permission(self, name: str, description: str | None = None) -> Permission:
        perm = Permission(name=name, description=description)
        self.db.add(perm)
        self.db.commit()
        self.db.refresh(perm)
        return perm

    def assign_permission_to_role(
        self, role_id: uuid.UUID, permission_id: uuid.UUID
    ) -> RolePermission:
        stmt = select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        )
        existing = self.db.execute(stmt).scalar_one_or_none()
        if existing:
            return existing

        mapping = RolePermission(role_id=role_id, permission_id=permission_id)
        self.db.add(mapping)
        self.db.commit()
        self.db.refresh(mapping)
        return mapping
