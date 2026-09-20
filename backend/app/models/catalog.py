from __future__ import annotations
import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid, func, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base
import sqlalchemy

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.seller import Seller, Branch
    from app.models.user import User

class Catalog(Base):
    __tablename__ = 'catalogs'
    __table_args__ = (
        UniqueConstraint('tenant_id', 'seller_id', name='uq_tenant_seller_catalog'),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('sellers.id', ondelete='CASCADE'), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default='DRAFT', nullable=False) # DRAFT, ACTIVE, INACTIVE

    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    tenant: Mapped[Tenant] = relationship('Tenant')
    seller: Mapped[Seller] = relationship('Seller')
    categories: Mapped[list[Category]] = relationship('Category', back_populates='catalog', cascade='all, delete-orphan')
    services: Mapped[list[Service]] = relationship('Service', back_populates='catalog', cascade='all, delete-orphan')

class Category(Base):
    __tablename__ = 'catalog_categories'
    __table_args__ = (
        UniqueConstraint('catalog_id', 'slug', name='uq_catalog_category_slug'),
        Index('ix_catalog_categories_catalog_id_status', 'catalog_id', 'status'),
        Index('ix_catalog_categories_catalog_id_parent_id', 'catalog_id', 'parent_id')
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    catalog_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('catalogs.id', ondelete='CASCADE'), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('catalog_categories.id', ondelete='RESTRICT'), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default='ACTIVE', nullable=False)

    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    catalog: Mapped[Catalog] = relationship('Catalog', back_populates='categories')
    parent: Mapped[Category | None] = relationship('Category', remote_side=[id], backref='children')
    services: Mapped[list[Service]] = relationship('Service', back_populates='category')

class Service(Base):
    __tablename__ = 'services'
    __table_args__ = (
        UniqueConstraint('catalog_id', 'slug', name='uq_catalog_service_slug'),
        Index('ix_services_catalog_id_status', 'catalog_id', 'status'),
        Index('ix_services_category_id', 'category_id')
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    catalog_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('catalogs.id', ondelete='CASCADE'), nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('catalog_categories.id', ondelete='SET NULL'), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    short_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    service_type: Mapped[str] = mapped_column(String(50), default='SERVICE', nullable=False)
    status: Mapped[str] = mapped_column(String(50), default='ACTIVE', nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    catalog: Mapped[Catalog] = relationship('Catalog', back_populates='services')
    category: Mapped[Category | None] = relationship('Category', back_populates='services')
    items: Mapped[list[ServiceItem]] = relationship('ServiceItem', back_populates='service', cascade='all, delete-orphan')
    addons: Mapped[list[ServiceAddon]] = relationship('ServiceAddon', back_populates='service', cascade='all, delete-orphan')
    branch_availability: Mapped[list[ServiceBranchAvailability]] = relationship('ServiceBranchAvailability', back_populates='service', cascade='all, delete-orphan')

class ServiceItem(Base):
    __tablename__ = 'service_items'
    __table_args__ = (
        UniqueConstraint('service_id', 'code', name='uq_service_item_code'),
        Index('ix_service_items_service_id_status', 'service_id', 'status')
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    service_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('services.id', ondelete='CASCADE'), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    unit_type: Mapped[str] = mapped_column(String(50), default='ITEM', nullable=False) # ITEM, KG, PAIR, SET
    status: Mapped[str] = mapped_column(String(50), default='ACTIVE', nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    service: Mapped[Service] = relationship('Service', back_populates='items')

class ServiceAddon(Base):
    __tablename__ = 'service_addons'
    __table_args__ = (
        UniqueConstraint('service_id', 'code', name='uq_service_addon_code'),
        Index('ix_service_addons_service_id_status', 'service_id', 'status')
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    service_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('services.id', ondelete='CASCADE'), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default='ACTIVE', nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    service: Mapped[Service] = relationship('Service', back_populates='addons')

class ServiceBranchAvailability(Base):
    __tablename__ = 'service_branch_availability'
    __table_args__ = (
        UniqueConstraint('service_id', 'branch_id', name='uq_service_branch_availability'),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    service_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('services.id', ondelete='CASCADE'), nullable=False)
    branch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('seller_branches.id', ondelete='CASCADE'), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    service: Mapped[Service] = relationship('Service', back_populates='branch_availability')
    branch: Mapped[Branch] = relationship('Branch')


class ServiceConfigurationVersion(Base):
    __tablename__ = 'service_configuration_versions'
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    service_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('services.id', ondelete='CASCADE'), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    configuration_snapshot: Mapped[dict] = mapped_column(sqlalchemy.JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

class PricePolicyVersion(Base):
    __tablename__ = 'price_policy_versions'
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False)
    service_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('services.id', ondelete='CASCADE'), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    recalculation_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    price_change_policy: Mapped[str] = mapped_column(String(50), nullable=False, default='STRICT')
    price_rejection_policy: Mapped[str] = mapped_column(String(50), nullable=False, default='CANCEL') 
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
