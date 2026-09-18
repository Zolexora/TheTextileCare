from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid, func, JSON, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User

class Application(Base):
    __tablename__ = 'applications'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    application_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default='ACTIVE', nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    modules: Mapped[list[ApplicationModule]] = relationship(
        'ApplicationModule', back_populates='application', cascade='all, delete-orphan'
    )

class ApplicationModule(Base):
    __tablename__ = 'application_modules'
    __table_args__ = (
        UniqueConstraint('application_id', 'key', name='uq_app_module_key'),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('applications.id', ondelete='CASCADE'), nullable=False)
    key: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default='ACTIVE', nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    application: Mapped[Application] = relationship('Application', back_populates='modules')

class ConfigurationDefinition(Base):
    __tablename__ = 'configuration_definitions'

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    domain: Mapped[str] = mapped_column(String(50), nullable=False)  # GENERAL, BRANDING, FEATURES, etc.
    data_type: Mapped[str] = mapped_column(String(50), nullable=False) # STRING, BOOLEAN, INTEGER, NUMBER, JSON
    schema: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    default_value: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default='ACTIVE', nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

class ConfigurationValue(Base):
    __tablename__ = 'configuration_values'
    __table_args__ = (
        Index(
            'ix_config_values_unique_published',
            'tenant_id', 'definition_id', 'application_id', 'module_id',
            unique=True,
            postgresql_where=text("status = 'PUBLISHED'")
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    application_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('applications.id', ondelete='CASCADE'), nullable=True, index=True)
    module_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('application_modules.id', ondelete='CASCADE'), nullable=True)
    definition_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('configuration_definitions.id', ondelete='CASCADE'), nullable=False, index=True)
    value: Mapped[Any] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default='PUBLISHED', nullable=False) # DRAFT, PUBLISHED, ARCHIVED
    
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    tenant: Mapped[Tenant] = relationship('Tenant', foreign_keys=[tenant_id])
    application: Mapped[Application | None] = relationship('Application', foreign_keys=[application_id])
    module: Mapped[ApplicationModule | None] = relationship('ApplicationModule', foreign_keys=[module_id])
    definition: Mapped[ConfigurationDefinition] = relationship('ConfigurationDefinition', foreign_keys=[definition_id])
    creator: Mapped[User | None] = relationship('User', foreign_keys=[created_by])
    updater: Mapped[User | None] = relationship('User', foreign_keys=[updated_by])
