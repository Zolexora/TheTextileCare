from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.membership import Membership
    from app.models.permission import Permission
    from app.models.role_permission import RolePermission


class Role(Base):
    __tablename__ = 'roles'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_platform_role: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    role_permissions: Mapped[list[RolePermission]] = relationship(
        'RolePermission',
        back_populates='role',
        cascade='all, delete-orphan',
        overlaps='permissions,roles',
    )
    permissions: Mapped[list[Permission]] = relationship(
        'Permission',
        secondary='role_permissions',
        back_populates='roles',
        overlaps='role_permissions,role,permission',
    )
    memberships: Mapped[list[Membership]] = relationship('Membership', back_populates='role')
