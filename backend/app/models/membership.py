from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.role import Role
    from app.models.tenant import Tenant
    from app.models.user import User


class Membership(Base):
    __tablename__ = 'memberships'
    __table_args__ = (UniqueConstraint('tenant_id', 'user_id', name='uq_tenant_user_membership'),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('roles.id', ondelete='RESTRICT'), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(50), default='ACTIVE', nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    tenant: Mapped[Tenant] = relationship('Tenant', back_populates='memberships')
    user: Mapped[User] = relationship('User', back_populates='memberships')
    role: Mapped[Role] = relationship('Role', back_populates='memberships')
