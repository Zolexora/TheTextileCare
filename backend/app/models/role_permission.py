from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.permission import Permission
    from app.models.role import Role


class RolePermission(Base):
    __tablename__ = 'role_permissions'
    __table_args__ = (UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, index=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey('permissions.id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    role: Mapped[Role] = relationship(
        'Role', back_populates='role_permissions', overlaps='permissions,roles'
    )
    permission: Mapped[Permission] = relationship(
        'Permission', overlaps='permissions,roles,role_permissions'
    )
