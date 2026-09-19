"""Phase 6 — Customer & Marketplace models."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Numeric,
    String, UniqueConstraint, Uuid, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.seller import Seller
    from app.models.user import User


class Customer(Base):
    """Platform-level customer profile. One per platform User."""
    __tablename__ = 'customers'
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_customer_user_id'),
        Index('ix_customers_user_id', 'user_id'),
        Index('ix_customers_status', 'status'),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True
    )
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default='ACTIVE', nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[User] = relationship('User')
    addresses: Mapped[list[CustomerAddress]] = relationship(
        'CustomerAddress', back_populates='customer', cascade='all, delete-orphan'
    )
    seller_relationships: Mapped[list[CustomerSeller]] = relationship(
        'CustomerSeller', back_populates='customer', cascade='all, delete-orphan'
    )


class CustomerAddress(Base):
    """Private customer delivery / pickup address."""
    __tablename__ = 'customer_addresses'
    __table_args__ = (
        Index('ix_customer_addresses_customer_id', 'customer_id'),
        Index('ix_customer_addresses_is_default', 'customer_id', 'is_default'),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('customers.id', ondelete='CASCADE'), nullable=False
    )
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    recipient_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address_line_1: Mapped[str] = mapped_column(String(255), nullable=False)
    address_line_2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    locality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(50), nullable=False)
    country: Mapped[str] = mapped_column(String(100), default='IN', nullable=False)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10, 7), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    customer: Mapped[Customer] = relationship('Customer', back_populates='addresses')


class CustomerSeller(Base):
    """Customer ↔ Seller relationship. Created on first interaction."""
    __tablename__ = 'customer_sellers'
    __table_args__ = (
        UniqueConstraint('customer_id', 'seller_id', name='uq_customer_seller'),
        Index('ix_customer_sellers_customer_id', 'customer_id'),
        Index('ix_customer_sellers_seller_id', 'seller_id'),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('customers.id', ondelete='CASCADE'), nullable=False
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey('sellers.id', ondelete='CASCADE'), nullable=False
    )
    status: Mapped[str] = mapped_column(String(50), default='ACTIVE', nullable=False)
    first_interaction_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_interaction_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    customer: Mapped[Customer] = relationship('Customer', back_populates='seller_relationships')
    seller: Mapped[Seller] = relationship('Seller')
