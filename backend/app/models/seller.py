from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant


class Seller(Base):
    __tablename__ = 'sellers'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('tenants.id', ondelete='CASCADE'), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default='ACTIVE', nullable=False)  # ACTIVE, SUSPENDED
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    tenant: Mapped[Tenant] = relationship('Tenant')
    branches: Mapped[list[Branch]] = relationship(
        'Branch', back_populates='seller', cascade='all, delete-orphan'
    )
    staff_profiles: Mapped[list[StaffProfile]] = relationship(
        'StaffProfile', back_populates='seller', cascade='all, delete-orphan'
    )
    settings: Mapped[SellerSettings] = relationship(
        'SellerSettings', back_populates='seller', uselist=False, cascade='all, delete-orphan'
    )


class Branch(Base):
    __tablename__ = 'seller_branches'
    __table_args__ = (UniqueConstraint('seller_id', 'code', name='uix_seller_branch_code'),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('sellers.id', ondelete='CASCADE'), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default='ACTIVE', nullable=False)
    timezone: Mapped[str] = mapped_column(String(100), default='UTC', nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    seller: Mapped[Seller] = relationship('Seller', back_populates='branches')


class StaffProfile(Base):
    __tablename__ = 'seller_staff_profiles'
    __table_args__ = (UniqueConstraint('seller_id', 'user_id', name='uix_seller_staff_user'),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('sellers.id', ondelete='CASCADE'), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True
    )
    job_title: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default='ACTIVE', nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    seller: Mapped[Seller] = relationship('Seller', back_populates='staff_profiles')


class SellerSettings(Base):
    __tablename__ = 'seller_settings'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('sellers.id', ondelete='CASCADE'), unique=True, nullable=False, index=True
    )
    currency: Mapped[str] = mapped_column(String(3), default='USD', nullable=False)
    tax_rate: Mapped[float | None] = mapped_column(nullable=True)
    business_hours: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    seller: Mapped[Seller] = relationship('Seller', back_populates='settings')
