from __future__ import annotations

import uuid
from datetime import datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Time, Uuid, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User


class Seller(Base):
    __tablename__ = 'sellers'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('tenants.id', ondelete='CASCADE'), unique=True, nullable=False, index=True
    )
    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    business_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default='PENDING', nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
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
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('sellers.id', ondelete='CASCADE'), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default='ACTIVE', nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line_1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address_line_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latitude: Mapped[float | None] = mapped_column(nullable=True)
    longitude: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    seller: Mapped[Seller] = relationship('Seller', back_populates='branches')
    tenant: Mapped[Tenant] = relationship('Tenant')
    business_hours: Mapped[list[BusinessHour]] = relationship(
        'BusinessHour', back_populates='branch', cascade='all, delete-orphan'
    )


class StaffProfile(Base):
    __tablename__ = 'seller_staff_profiles'
    __table_args__ = (UniqueConstraint('tenant_id', 'user_id', name='uix_staff_tenant_user'),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True
    )
    seller_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey('sellers.id', ondelete='CASCADE'), nullable=True, index=True
    )
    employee_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default='ACTIVE', nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    tenant: Mapped[Tenant] = relationship('Tenant')
    user: Mapped[User] = relationship('User')
    seller: Mapped[Seller] = relationship('Seller', back_populates='staff_profiles')


class SellerSettings(Base):
    __tablename__ = 'seller_settings'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('sellers.id', ondelete='CASCADE'), unique=True, nullable=False, index=True
    )
    timezone: Mapped[str] = mapped_column(String(100), default='UTC', nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default='USD', nullable=False)
    locale: Mapped[str] = mapped_column(String(20), default='en-US', nullable=False)
    date_format: Mapped[str] = mapped_column(String(50), default='YYYY-MM-DD', nullable=False)
    time_format: Mapped[str] = mapped_column(String(50), default='24h', nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    seller: Mapped[Seller] = relationship('Seller', back_populates='settings')


class BusinessHour(Base):
    __tablename__ = 'business_hours'
    __table_args__ = (UniqueConstraint('branch_id', 'day_of_week', name='uix_branch_day'),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('seller_branches.id', ondelete='CASCADE'), nullable=False, index=True
    )
    day_of_week: Mapped[int] = mapped_column(nullable=False)  # 0=Monday, 6=Sunday
    is_open: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    open_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    close_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    tenant: Mapped[Tenant] = relationship('Tenant')
    branch: Mapped[Branch] = relationship('Branch', back_populates='business_hours')
