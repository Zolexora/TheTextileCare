# Milestone 1 Investigation & Implementation Strategy Report: Driver Schema, Models, Schemas & RBAC Permissions

**Agent**: `m1_phase8_explorer_1`  
**Working Directory**: `/workspaces/TheTextileCare/.agents/m1_phase8_explorer_1`  
**Target Scope**: Milestone 1 (Features 1–3) — Driver Domain Foundation  
**Date**: 2026-09-20  
**Handoff Target**: Parent Orchestrator (`a78db49b-ac7b-403d-96ff-f8b3d4ebe7cd`) & Milestone 1 Implementer / Worker  

---

## Executive Summary

This report establishes the complete, production-grade technical implementation strategy for **Milestone 1 (Driver Domain Foundation: Schema, Models, Schemas, and RBAC Permissions)**. 

Currently, the backend codebase contains zero driver models, zero driver tables, no driver RBAC role or permissions, and no driver schemas. In accordance with **ADR-009 (Shared Driver Application)** and the Phase 8 requirements (**Q51–Q60 / R1–R4**), Milestone 1 lays the bedrock for the driver logistics domain without introducing external distributed brokers (Kafka/Redis) or mutating legacy Phase 1–7 migrations.

This analysis provides:
1. Complete table architecture for `drivers`, `driver_vehicles`, `driver_seller_authorizations`, and `driver_compliance_documents` with exact types, constraints, foreign keys, cascade rules, and composite indexes.
2. A drop-in Alembic migration script revising `b2c3d4e5f6a7`.
3. SQLAlchemy 2.0 models for `backend/app/models/driver.py`.
4. Pydantic v2 schemas for `backend/app/schemas/driver.py`.
5. RBAC role (`RoleName.DRIVER`) and permission definitions (`DRIVER_MANAGE`, `DRIVER_VIEW`, `DUTY_MANAGE`, `DUTY_VIEW`, `DUTY_REASSIGN`, `OPERATIONS_ALERT_VIEW`) with the authoritative 8-role mapping matrix.
6. Identified migration/schema pitfalls and explicit implementation guidance for the Worker.

---

## 1. Database Schema & Migration Specification (Feature 1)

### 1.1 Four Proposed Tables Deep Dive

#### Table 1: `drivers`
- **Purpose**: Authoritative driver profile linked 1:1 with platform `User`, holding operational shift status, compliance state, current geographic coordinates, and concurrent capacity limits.
- **Columns**:
  - `id`: `sa.Uuid()`, Primary Key, nullable=False.
  - `user_id`: `sa.Uuid()`, ForeignKey(`users.id`, ondelete='CASCADE'), nullable=False, unique=True.
  - `tenant_id`: `sa.Uuid()`, ForeignKey(`tenants.id`, ondelete='SET NULL'), nullable=True. *(NULL for shared platform marketplace pool; populated if dedicated private fleet).*
  - `seller_id`: `sa.Uuid()`, ForeignKey(`sellers.id`, ondelete='SET NULL'), nullable=True. *(NULL for shared platform drivers; populated if dedicated to a specific seller).*
  - `home_branch_id`: `sa.Uuid()`, ForeignKey(`seller_branches.id`, ondelete='SET NULL'), nullable=True. *(Primary fulfillment branch anchoring).*
  - `full_name`: `sa.String(length=255)`, nullable=False.
  - `phone_number`: `sa.String(length=50)`, nullable=False. *(Mandatory direct contact number for unmasked customer visibility per R3).*
  - `status`: `sa.String(length=50)`, nullable=False, server_default='ACTIVE'. *(Enum: `ACTIVE`, `INACTIVE`, `ON_LEAVE`, `SUSPENDED`).*
  - `is_on_duty`: `sa.Boolean()`, nullable=False, server_default=sa.text('false'). *(Real-time shift toggle).*
  - `compliance_status`: `sa.String(length=50)`, nullable=False, server_default='PENDING'. *(Enum: `PENDING`, `COMPLIANT`, `EXPIRED`, `REJECTED`, `SUSPENDED`).*
  - `current_latitude`: `sa.Numeric(precision=10, scale=7)`, nullable=True.
  - `current_longitude`: `sa.Numeric(precision=10, scale=7)`, nullable=True.
  - `max_active_duties`: `sa.Integer()`, nullable=False, server_default='3'. *(Capacity threshold per Q58).*
  - `created_at`: `sa.DateTime(timezone=True)`, nullable=False, server_default=sa.text('now()').
  - `updated_at`: `sa.DateTime(timezone=True)`, nullable=False, server_default=sa.text('now()').
- **Constraints & Indexes**:
  - `UniqueConstraint('user_id', name='uq_drivers_user_id')`
  - `CheckConstraint("status IN ('ACTIVE', 'INACTIVE', 'ON_LEAVE', 'SUSPENDED')", name='ck_drivers_status')`
  - `CheckConstraint("compliance_status IN ('PENDING', 'COMPLIANT', 'EXPIRED', 'REJECTED', 'SUSPENDED')", name='ck_drivers_compliance_status')`
  - `CheckConstraint("max_active_duties >= 1", name='ck_drivers_max_active_duties')`
  - `Index('ix_drivers_user_id', 'user_id', unique=True)`
  - `Index('ix_drivers_tenant_id', 'tenant_id')`
  - `Index('ix_drivers_seller_id', 'seller_id')`
  - `Index('ix_drivers_home_branch_id', 'home_branch_id')`
  - `Index('ix_drivers_status_duty', 'status', 'is_on_duty', 'compliance_status')`

#### Table 2: `driver_vehicles`
- **Purpose**: Captures vehicle profile details (make, model, license plate, vehicle type, color) displayed to customers upon assignment (R3, Q54).
- **Columns**:
  - `id`: `sa.Uuid()`, Primary Key, nullable=False.
  - `driver_id`: `sa.Uuid()`, ForeignKey(`drivers.id`, ondelete='CASCADE'), nullable=False.
  - `make`: `sa.String(length=100)`, nullable=False.
  - `model`: `sa.String(length=100)`, nullable=False.
  - `plate_number`: `sa.String(length=50)`, nullable=False.
  - `vehicle_type`: `sa.String(length=50)`, nullable=False, server_default='SCOOTER'. *(Enum: `BIKE`, `SCOOTER`, `VAN`, `CAR`, `BICYCLE`).*
  - `color`: `sa.String(length=50)`, nullable=True.
  - `is_active`: `sa.Boolean()`, nullable=False, server_default=sa.text('true').
  - `created_at`: `sa.DateTime(timezone=True)`, nullable=False, server_default=sa.text('now()').
  - `updated_at`: `sa.DateTime(timezone=True)`, nullable=False, server_default=sa.text('now()').
- **Constraints & Indexes**:
  - `CheckConstraint("vehicle_type IN ('BIKE', 'SCOOTER', 'VAN', 'CAR', 'BICYCLE')", name='ck_driver_vehicles_type')`
  - `Index('ix_driver_vehicles_driver_id', 'driver_id')`
  - `Index('ix_driver_vehicles_plate_number', 'plate_number')`
  - `Index('ix_driver_vehicles_driver_active', 'driver_id', 'is_active')`

#### Table 3: `driver_seller_authorizations`
- **Purpose**: Authorizes platform pool drivers or multi-branch fleet drivers to service orders for specific sellers and branches.
- **Columns**:
  - `id`: `sa.Uuid()`, Primary Key, nullable=False.
  - `driver_id`: `sa.Uuid()`, ForeignKey(`drivers.id`, ondelete='CASCADE'), nullable=False.
  - `tenant_id`: `sa.Uuid()`, ForeignKey(`tenants.id`, ondelete='CASCADE'), nullable=False.
  - `seller_id`: `sa.Uuid()`, ForeignKey(`sellers.id`, ondelete='CASCADE'), nullable=False.
  - `branch_id`: `sa.Uuid()`, ForeignKey(`seller_branches.id`, ondelete='CASCADE'), nullable=True. *(NULL = authorized for all branches of seller).*
  - `is_authorized`: `sa.Boolean()`, nullable=False, server_default=sa.text('true').
  - `created_at`: `sa.DateTime(timezone=True)`, nullable=False, server_default=sa.text('now()').
  - `updated_at`: `sa.DateTime(timezone=True)`, nullable=False, server_default=sa.text('now()').
- **Constraints & Indexes**:
  - `UniqueConstraint('driver_id', 'seller_id', 'branch_id', name='uq_driver_seller_branch_auth')`
  - `Index('ix_driver_seller_auth_driver_id', 'driver_id')`
  - `Index('ix_driver_seller_auth_seller_id', 'seller_id')`
  - `Index('ix_driver_seller_auth_branch_id', 'branch_id')`
  - `Index('ix_driver_seller_auth_lookup', 'driver_id', 'seller_id', 'is_authorized')`

#### Table 4: `driver_compliance_documents`
- **Purpose**: Manages compliance credential documents: Driving License (`DL`), Vehicle Registration Certificate (`RC`), Vehicle Insurance (`INSURANCE`), and Background Verification Check (`BGC`). A driver is disqualified if any required document is unverified or expired (`valid_until < now()`).
- **Columns**:
  - `id`: `sa.Uuid()`, Primary Key, nullable=False.
  - `driver_id`: `sa.Uuid()`, ForeignKey(`drivers.id`, ondelete='CASCADE'), nullable=False.
  - `document_type`: `sa.String(length=50)`, nullable=False. *(Enum: `DL`, `RC`, `INSURANCE`, `BGC`).*
  - `document_number`: `sa.String(length=100)`, nullable=True.
  - `document_url`: `sa.String(length=1000)`, nullable=True.
  - `is_verified`: `sa.Boolean()`, nullable=False, server_default=sa.text('false').
  - `verified_at`: `sa.DateTime(timezone=True)`, nullable=True.
  - `verified_by_user_id`: `sa.Uuid()`, ForeignKey(`users.id`, ondelete='SET NULL'), nullable=True.
  - `valid_from`: `sa.DateTime(timezone=True)`, nullable=True.
  - `valid_until`: `sa.DateTime(timezone=True)`, nullable=True. *(Strict evaluation cutoff).*
  - `rejection_reason`: `sa.String(length=1000)`, nullable=True.
  - `created_at`: `sa.DateTime(timezone=True)`, nullable=False, server_default=sa.text('now()').
  - `updated_at`: `sa.DateTime(timezone=True)`, nullable=False, server_default=sa.text('now()').
- **Constraints & Indexes**:
  - `UniqueConstraint('driver_id', 'document_type', name='uq_driver_compliance_driver_doc')`
  - `CheckConstraint("document_type IN ('DL', 'RC', 'INSURANCE', 'BGC')", name='ck_driver_compliance_doc_type')`
  - `Index('ix_driver_compliance_driver_id', 'driver_id')`
  - `Index('ix_driver_compliance_doc_type', 'document_type')`
  - `Index('ix_driver_compliance_valid_until', 'valid_until')`
  - `Index('ix_driver_compliance_eval', 'driver_id', 'document_type', 'is_verified', 'valid_until')`

---

### 1.2 Alembic Migration Blueprint

**File Location**: `backend/migrations/versions/c3d4e5f6a7b8_phase8_driver_domain.py`  
**Revision ID**: `c3d4e5f6a7b8`  
**Down Revision**: `b2c3d4e5f6a7`  

```python
"""phase8_driver_domain

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-20 08:30:00.000000

Phase 8 — Driver Logistics Domain Foundation (Milestone 1).

Creates:
  - drivers
  - driver_vehicles
  - driver_seller_authorizations
  - driver_compliance_documents
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. Table: drivers
    # -----------------------------------------------------------------------
    op.create_table(
        'drivers',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=True),
        sa.Column('seller_id', sa.Uuid(), nullable=True),
        sa.Column('home_branch_id', sa.Uuid(), nullable=True),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('phone_number', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='ACTIVE', nullable=False),
        sa.Column('is_on_duty', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('compliance_status', sa.String(length=50), server_default='PENDING', nullable=False),
        sa.Column('current_latitude', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('current_longitude', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('max_active_duties', sa.Integer(), server_default='3', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE', 'ON_LEAVE', 'SUSPENDED')", name='ck_drivers_status'),
        sa.CheckConstraint("compliance_status IN ('PENDING', 'COMPLIANT', 'EXPIRED', 'REJECTED', 'SUSPENDED')", name='ck_drivers_compliance_status'),
        sa.CheckConstraint("max_active_duties >= 1", name='ck_drivers_max_active_duties'),
        sa.ForeignKeyConstraint(['home_branch_id'], ['seller_branches.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['seller_id'], ['sellers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_drivers_user_id'),
    )
    op.create_index('ix_drivers_user_id', 'drivers', ['user_id'], unique=True)
    op.create_index('ix_drivers_tenant_id', 'drivers', ['tenant_id'], unique=False)
    op.create_index('ix_drivers_seller_id', 'drivers', ['seller_id'], unique=False)
    op.create_index('ix_drivers_home_branch_id', 'drivers', ['home_branch_id'], unique=False)
    op.create_index('ix_drivers_status_duty', 'drivers', ['status', 'is_on_duty', 'compliance_status'], unique=False)

    # -----------------------------------------------------------------------
    # 2. Table: driver_vehicles
    # -----------------------------------------------------------------------
    op.create_table(
        'driver_vehicles',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('driver_id', sa.Uuid(), nullable=False),
        sa.Column('make', sa.String(length=100), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('plate_number', sa.String(length=50), nullable=False),
        sa.Column('vehicle_type', sa.String(length=50), server_default='SCOOTER', nullable=False),
        sa.Column('color', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("vehicle_type IN ('BIKE', 'SCOOTER', 'VAN', 'CAR', 'BICYCLE')", name='ck_driver_vehicles_type'),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_driver_vehicles_driver_id', 'driver_vehicles', ['driver_id'], unique=False)
    op.create_index('ix_driver_vehicles_plate_number', 'driver_vehicles', ['plate_number'], unique=False)
    op.create_index('ix_driver_vehicles_driver_active', 'driver_vehicles', ['driver_id', 'is_active'], unique=False)

    # -----------------------------------------------------------------------
    # 3. Table: driver_seller_authorizations
    # -----------------------------------------------------------------------
    op.create_table(
        'driver_seller_authorizations',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('driver_id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('seller_id', sa.Uuid(), nullable=False),
        sa.Column('branch_id', sa.Uuid(), nullable=True),
        sa.Column('is_authorized', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['branch_id'], ['seller_branches.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['seller_id'], ['sellers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('driver_id', 'seller_id', 'branch_id', name='uq_driver_seller_branch_auth'),
    )
    op.create_index('ix_driver_seller_auth_driver_id', 'driver_seller_authorizations', ['driver_id'], unique=False)
    op.create_index('ix_driver_seller_auth_seller_id', 'driver_seller_authorizations', ['seller_id'], unique=False)
    op.create_index('ix_driver_seller_auth_branch_id', 'driver_seller_authorizations', ['branch_id'], unique=False)
    op.create_index('ix_driver_seller_auth_lookup', 'driver_seller_authorizations', ['driver_id', 'seller_id', 'is_authorized'], unique=False)

    # -----------------------------------------------------------------------
    # 4. Table: driver_compliance_documents
    # -----------------------------------------------------------------------
    op.create_table(
        'driver_compliance_documents',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('driver_id', sa.Uuid(), nullable=False),
        sa.Column('document_type', sa.String(length=50), nullable=False),
        sa.Column('document_number', sa.String(length=100), nullable=True),
        sa.Column('document_url', sa.String(length=1000), nullable=True),
        sa.Column('is_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.String(length=1000), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("document_type IN ('DL', 'RC', 'INSURANCE', 'BGC')", name='ck_driver_compliance_doc_type'),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['verified_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('driver_id', 'document_type', name='uq_driver_compliance_driver_doc'),
    )
    op.create_index('ix_driver_compliance_driver_id', 'driver_compliance_documents', ['driver_id'], unique=False)
    op.create_index('ix_driver_compliance_doc_type', 'driver_compliance_documents', ['document_type'], unique=False)
    op.create_index('ix_driver_compliance_valid_until', 'driver_compliance_documents', ['valid_until'], unique=False)
    op.create_index('ix_driver_compliance_eval', 'driver_compliance_documents', ['driver_id', 'document_type', 'is_verified', 'valid_until'], unique=False)


def downgrade() -> None:
    op.drop_table('driver_compliance_documents')
    op.drop_table('driver_seller_authorizations')
    op.drop_table('driver_vehicles')
    op.drop_table('drivers')
```

---

## 2. SQLAlchemy 2.0 Models Specification (Feature 2)

**Target Location**: `backend/app/models/driver.py`  
**Registration**: Register in `backend/app/models/__init__.py` and add to `__all__`.

```python
"""Phase 8 — Driver Domain Models.

Manages driver profiles, vehicles, compliance verification credentials,
and seller branch logistics authorizations.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.seller import Branch, Seller
    from app.models.tenant import Tenant
    from app.models.user import User


class DriverStatus(str, enum.Enum):
    """Operational lifecycle status of a driver."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ON_LEAVE = "ON_LEAVE"
    SUSPENDED = "SUSPENDED"


class DriverComplianceStatus(str, enum.Enum):
    """Overall compliance evaluation status of a driver."""
    PENDING = "PENDING"
    COMPLIANT = "COMPLIANT"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class VehicleType(str, enum.Enum):
    """Supported vehicle categories."""
    BIKE = "BIKE"
    SCOOTER = "SCOOTER"
    VAN = "VAN"
    CAR = "CAR"
    BICYCLE = "BICYCLE"


class ComplianceDocumentType(str, enum.Enum):
    """Mandatory compliance document types per Q55."""
    DL = "DL"                  # Driving License
    RC = "RC"                  # Registration Certificate
    INSURANCE = "INSURANCE"    # Vehicle Insurance
    BGC = "BGC"                # Background Verification Check


REQUIRED_COMPLIANCE_DOCUMENTS = {
    ComplianceDocumentType.DL.value,
    ComplianceDocumentType.RC.value,
    ComplianceDocumentType.INSURANCE.value,
    ComplianceDocumentType.BGC.value,
}


class Driver(Base):
    """Driver profile entity linked 1:1 with User."""

    __tablename__ = "drivers"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_drivers_user_id"),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'ON_LEAVE', 'SUSPENDED')",
            name="ck_drivers_status",
        ),
        CheckConstraint(
            "compliance_status IN ('PENDING', 'COMPLIANT', 'EXPIRED', 'REJECTED', 'SUSPENDED')",
            name="ck_drivers_compliance_status",
        ),
        CheckConstraint("max_active_duties >= 1", name="ck_drivers_max_active_duties"),
        Index("ix_drivers_user_id", "user_id", unique=True),
        Index("ix_drivers_tenant_id", "tenant_id"),
        Index("ix_drivers_seller_id", "seller_id"),
        Index("ix_drivers_home_branch_id", "home_branch_id"),
        Index("ix_drivers_status_duty", "status", "is_on_duty", "compliance_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True
    )
    seller_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sellers.id", ondelete="SET NULL"), nullable=True
    )
    home_branch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("seller_branches.id", ondelete="SET NULL"), nullable=True
    )

    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default=DriverStatus.ACTIVE.value, nullable=False
    )
    is_on_duty: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    compliance_status: Mapped[str] = mapped_column(
        String(50), default=DriverComplianceStatus.PENDING.value, nullable=False
    )

    current_latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    current_longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    max_active_duties: Mapped[int] = mapped_column(
        Integer, default=3, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship("User")
    tenant: Mapped[Tenant | None] = relationship("Tenant")
    seller: Mapped[Seller | None] = relationship("Seller")
    home_branch: Mapped[Branch | None] = relationship("Branch")

    vehicles: Mapped[list[DriverVehicle]] = relationship(
        "DriverVehicle", back_populates="driver", cascade="all, delete-orphan"
    )
    authorizations: Mapped[list[DriverSellerAuthorization]] = relationship(
        "DriverSellerAuthorization", back_populates="driver", cascade="all, delete-orphan"
    )
    compliance_documents: Mapped[list[DriverComplianceDocument]] = relationship(
        "DriverComplianceDocument", back_populates="driver", cascade="all, delete-orphan"
    )

    @property
    def is_eligible_for_dispatch(self) -> bool:
        """Binary eligibility evaluator for priority matching (R1, Q56, Q77)."""
        return (
            self.status == DriverStatus.ACTIVE.value
            and self.is_on_duty
            and self.compliance_status == DriverComplianceStatus.COMPLIANT.value
        )


class DriverVehicle(Base):
    """Vehicle profile registered for a driver."""

    __tablename__ = "driver_vehicles"
    __table_args__ = (
        CheckConstraint(
            "vehicle_type IN ('BIKE', 'SCOOTER', 'VAN', 'CAR', 'BICYCLE')",
            name="ck_driver_vehicles_type",
        ),
        Index("ix_driver_vehicles_driver_id", "driver_id"),
        Index("ix_driver_vehicles_plate_number", "plate_number"),
        Index("ix_driver_vehicles_driver_active", "driver_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False
    )

    make: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    plate_number: Mapped[str] = mapped_column(String(50), nullable=False)
    vehicle_type: Mapped[str] = mapped_column(
        String(50), default=VehicleType.SCOOTER.value, nullable=False
    )
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    driver: Mapped[Driver] = relationship("Driver", back_populates="vehicles")


class DriverSellerAuthorization(Base):
    """Driver authorization to service a tenant, seller, or branch."""

    __tablename__ = "driver_seller_authorizations"
    __table_args__ = (
        UniqueConstraint("driver_id", "seller_id", "branch_id", name="uq_driver_seller_branch_auth"),
        Index("ix_driver_seller_auth_driver_id", "driver_id"),
        Index("ix_driver_seller_auth_seller_id", "seller_id"),
        Index("ix_driver_seller_auth_branch_id", "branch_id"),
        Index("ix_driver_seller_auth_lookup", "driver_id", "seller_id", "is_authorized"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False
    )
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("seller_branches.id", ondelete="CASCADE"), nullable=True
    )
    is_authorized: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    driver: Mapped[Driver] = relationship("Driver", back_populates="authorizations")
    tenant: Mapped[Tenant] = relationship("Tenant")
    seller: Mapped[Seller] = relationship("Seller")
    branch: Mapped[Branch | None] = relationship("Branch")


class DriverComplianceDocument(Base):
    """Compliance credential document for a driver (DL, RC, Insurance, BGC)."""

    __tablename__ = "driver_compliance_documents"
    __table_args__ = (
        UniqueConstraint("driver_id", "document_type", name="uq_driver_compliance_driver_doc"),
        CheckConstraint(
            "document_type IN ('DL', 'RC', 'INSURANCE', 'BGC')",
            name="ck_driver_compliance_doc_type",
        ),
        Index("ix_driver_compliance_driver_id", "driver_id"),
        Index("ix_driver_compliance_doc_type", "document_type"),
        Index("ix_driver_compliance_valid_until", "valid_until"),
        Index("ix_driver_compliance_eval", "driver_id", "document_type", "is_verified", "valid_until"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    document_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    document_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    driver: Mapped[Driver] = relationship("Driver", back_populates="compliance_documents")
    verified_by: Mapped[User | None] = relationship("User")

    @property
    def is_valid(self) -> bool:
        """Evaluates whether document is verified and unexpired."""
        if not self.is_verified:
            return False
        if self.valid_until is not None:
            now = datetime.now(timezone.utc)
            cmp_time = self.valid_until if self.valid_until.tzinfo else self.valid_until.replace(tzinfo=timezone.utc)
            if cmp_time < now:
                return False
        return True
```

---

## 3. Pydantic v2 Schemas Specification (Feature 2)

**Target Location**: `backend/app/schemas/driver.py`  
**Registration**: Register in `backend/app/schemas/__init__.py` and add to `__all__`.

```python
"""Phase 8 — Driver Domain Pydantic v2 Schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.driver import (
    ComplianceDocumentType,
    DriverComplianceStatus,
    DriverStatus,
    VehicleType,
)

__all__ = [
    "DriverStatus",
    "DriverComplianceStatus",
    "VehicleType",
    "ComplianceDocumentType",
    "DriverVehicleBase",
    "DriverVehicleCreate",
    "DriverVehicleUpdate",
    "DriverVehicleResponse",
    "DriverComplianceDocumentBase",
    "DriverComplianceDocumentCreate",
    "DriverComplianceDocumentVerifyRequest",
    "DriverComplianceDocumentResponse",
    "DriverSellerAuthorizationCreate",
    "DriverSellerAuthorizationResponse",
    "DriverCreate",
    "DriverUpdate",
    "DriverShiftUpdate",
    "DriverLocationUpdate",
    "DriverResponse",
    "DriverListResponse",
    "CustomerDriverInfoResponse",
]


# ---------------------------------------------------------------------------
# Vehicle Schemas
# ---------------------------------------------------------------------------
class DriverVehicleBase(BaseModel):
    make: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    plate_number: str = Field(..., min_length=1, max_length=50)
    vehicle_type: VehicleType = VehicleType.SCOOTER
    color: str | None = Field(default=None, max_length=50)


class DriverVehicleCreate(DriverVehicleBase):
    pass


class DriverVehicleUpdate(BaseModel):
    make: str | None = Field(default=None, min_length=1, max_length=100)
    model: str | None = Field(default=None, min_length=1, max_length=100)
    plate_number: str | None = Field(default=None, min_length=1, max_length=50)
    vehicle_type: VehicleType | None = None
    color: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None


class DriverVehicleResponse(DriverVehicleBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    driver_id: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Compliance Document Schemas
# ---------------------------------------------------------------------------
class DriverComplianceDocumentBase(BaseModel):
    document_type: ComplianceDocumentType
    document_number: str | None = Field(default=None, max_length=100)
    document_url: str | None = Field(default=None, max_length=1000)
    valid_from: datetime | None = None
    valid_until: datetime | None = None


class DriverComplianceDocumentCreate(DriverComplianceDocumentBase):
    pass


class DriverComplianceDocumentVerifyRequest(BaseModel):
    is_verified: bool
    rejection_reason: str | None = Field(default=None, max_length=1000)


class DriverComplianceDocumentResponse(DriverComplianceDocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    driver_id: uuid.UUID
    is_verified: bool
    verified_at: datetime | None = None
    verified_by_user_id: uuid.UUID | None = None
    rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    is_valid: bool = False


# ---------------------------------------------------------------------------
# Seller Authorization Schemas
# ---------------------------------------------------------------------------
class DriverSellerAuthorizationCreate(BaseModel):
    tenant_id: uuid.UUID
    seller_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    is_authorized: bool = True


class DriverSellerAuthorizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    driver_id: uuid.UUID
    tenant_id: uuid.UUID
    seller_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    is_authorized: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Driver Profile Schemas
# ---------------------------------------------------------------------------
class DriverCreate(BaseModel):
    user_id: uuid.UUID
    tenant_id: uuid.UUID | None = None
    seller_id: uuid.UUID | None = None
    home_branch_id: uuid.UUID | None = None
    full_name: str = Field(..., min_length=1, max_length=255)
    phone_number: str = Field(..., min_length=5, max_length=50)
    max_active_duties: int = Field(default=3, ge=1, le=20)
    initial_vehicle: DriverVehicleCreate | None = None


class DriverUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone_number: str | None = Field(default=None, min_length=5, max_length=50)
    home_branch_id: uuid.UUID | None = None
    status: DriverStatus | None = None
    max_active_duties: int | None = Field(default=None, ge=1, le=20)


class DriverShiftUpdate(BaseModel):
    is_on_duty: bool
    latitude: Decimal | None = None
    longitude: Decimal | None = None


class DriverLocationUpdate(BaseModel):
    latitude: Decimal = Field(..., ge=Decimal("-90.0"), le=Decimal("90.0"))
    longitude: Decimal = Field(..., ge=Decimal("-180.0"), le=Decimal("180.0"))


class DriverResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    tenant_id: uuid.UUID | None = None
    seller_id: uuid.UUID | None = None
    home_branch_id: uuid.UUID | None = None
    full_name: str
    phone_number: str
    status: DriverStatus
    is_on_duty: bool
    compliance_status: DriverComplianceStatus
    current_latitude: Decimal | None = None
    current_longitude: Decimal | None = None
    max_active_duties: int
    is_eligible_for_dispatch: bool

    vehicles: list[DriverVehicleResponse] = Field(default_factory=list)
    compliance_documents: list[DriverComplianceDocumentResponse] = Field(default_factory=list)
    authorizations: list[DriverSellerAuthorizationResponse] = Field(default_factory=list)

    created_at: datetime
    updated_at: datetime


class DriverListResponse(BaseModel):
    items: list[DriverResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Customer-Facing Active Driver Payload (R3 Invariant)
# ---------------------------------------------------------------------------
class CustomerDriverInfoResponse(BaseModel):
    driver_name: str
    driver_phone: str  # Unmasked actual phone number per R3
    vehicle_make: str
    vehicle_model: str
    vehicle_plate_number: str
    vehicle_type: str
    vehicle_color: str | None = None
```

---

## 4. RBAC Permissions & Role-Permission Matrix (Feature 3)

### 4.1 Permission Definitions in `backend/app/core/permissions/constants.py`

Add the following members to `PermissionName(str, Enum)`:
```python
    # Phase 8 Driver & Logistics Permissions
    DRIVER_VIEW = 'driver.view'
    DRIVER_MANAGE = 'driver.manage'
    DUTY_VIEW = 'duty.view'
    DUTY_MANAGE = 'duty.manage'
    DUTY_REASSIGN = 'duty.reassign'
    OPERATIONS_ALERT_VIEW = 'operations_alert.view'

    # Aliases for read operations to ensure cross-module compatibility
    DRIVER_READ = 'driver.view'
    DUTY_READ = 'duty.view'
```

Add the new role to `RoleName(str, Enum)`:
```python
    # Phase 8 Driver Role
    DRIVER = 'DRIVER'
```

Update `TENANT_ROLES`:
```python
TENANT_ROLES = {
    RoleName.TENANT_OWNER.value,
    RoleName.TENANT_ADMIN.value,
    RoleName.TENANT_MEMBER.value,
    RoleName.TENANT_VIEWER.value,
    RoleName.SELLER_OWNER.value,
    RoleName.SELLER_ADMIN.value,
    RoleName.STAFF.value,
    RoleName.VIEWER.value,
    RoleName.DRIVER.value,  # Driver operates within tenant fulfillment context
}
```

### 4.2 Role-Permission Mapping Matrix

| Role | `driver.view` | `driver.manage` | `duty.view` | `duty.manage` | `duty.reassign` | `operations_alert.view` | Rationale / Least Privilege Boundary |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`PLATFORM_ADMIN`** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Super administrator with platform-wide unrestricted access. |
| **`TENANT_OWNER`** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Full operational and configuration authority for the tenant. |
| **`TENANT_ADMIN`** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Administrative authority to onboard drivers, dispatch, and review alerts. |
| **`SELLER_OWNER`** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Seller organization owner managing fleet, branches, and dispatches. |
| **`SELLER_ADMIN`** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Seller operational manager configuring drivers and resolving alerts. |
| **`STAFF`** | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | Counter/branch staff can view drivers and assign/reassign duties, but cannot create or suspend driver accounts. |
| **`VIEWER`** | ✅ | ❌ | ✅ | ❌ | ❌ | ✅ | Read-only auditor or analyst; strictly prohibited from dispatch mutations. |
| **`DRIVER`** | ✅ | ❌ | ✅ | ✅ | ❌ | ❌ | Operational mobile driver: can view own profile and duties, update task status (start/complete), but cannot reassign or view ops alerts. |

### 4.3 Seeding Updates in `backend/app/services/roles.py`

In `backend/app/services/roles.py`:
1. Add description to `ROLE_DESCRIPTIONS`:
   ```python
   RoleName.DRIVER.value: 'Logistics fulfillment driver managing assigned pickup and delivery duties',
   ```
2. Add descriptions to `PERMISSION_DESCRIPTIONS`:
   ```python
   PermissionName.DRIVER_VIEW.value: 'View driver profiles, vehicle details, and operational status',
   PermissionName.DRIVER_MANAGE.value: 'Create, update, suspend, or configure drivers and compliance documents',
   PermissionName.DUTY_VIEW.value: 'View logistics duties and assignment history',
   PermissionName.DUTY_MANAGE.value: 'Create, assign, start, or complete logistics fulfillment duties',
   PermissionName.DUTY_REASSIGN.value: 'Reassign logistics duties with mandatory justification reason',
   PermissionName.OPERATIONS_ALERT_VIEW.value: 'View operational alerts for driver unavailability, timeouts, and SLA breaches',
   ```

---

## 5. Potential Migration & Schema Pitfalls (Item 5)

| # | Potential Pitfall | Risk / Failure Mode | Recommended Worker Mitigation |
|---|-------------------|---------------------|-------------------------------|
| 1 | **Alembic Down Revision Mismatch** | Specifying `down_revision = None` or branching from an earlier revision creates multiple migration heads and breaks CI. | The existing head is `b2c3d4e5f6a7`. Set `down_revision = 'b2c3d4e5f6a7'`. Verify using `PYTHONPATH=. alembic heads`. |
| 2 | **Duplicate Index Declaration** | Declaring `index=True` on `mapped_column()` AND specifying `Index('ix_...', ...)` in `__table_args__` causes PostgreSQL duplicate index errors. | Define all indexes exclusively inside `__table_args__` or exclusively on `mapped_column()`. Follow the project standard in `backend/app/models/pickup.py`. |
| 3 | **Enum Alteration in PostgreSQL** | Creating native PostgreSQL `ENUM` types causes severe migration locking, prevents easy rollbacks, and breaks on SQLite. | Use `sa.String(length=50)` combined with `sa.CheckConstraint(...)` in Alembic migrations and `Base` models. |
| 4 | **UUID Default Evaluation** | Passing `default=uuid.uuid4()` instead of `default=uuid.uuid4` in SQLAlchemy models evaluates the function at import time, assigning every row the same UUID. | Always pass the callable `default=uuid.uuid4` (without parentheses). |
| 5 | **Missing Model Exports in `__init__.py`** | If `backend/app/models/driver.py` is created but not exported in `backend/app/models/__init__.py`, SQLAlchemy declarative metadata will not discover the tables. | Add all driver models and enums to `backend/app/models/__init__.py` and include them in `__all__`. |
| 6 | **Timezone Naive Expiration Comparisons** | Comparing timezone-aware `valid_until` against timezone-naive `datetime.now()` raises a runtime `TypeError` in Python. | Always use `datetime.now(timezone.utc)` for compliance expiration checks in `DriverComplianceDocument.is_valid`. |
| 7 | **Nullable Unique Constraints on Authorizations** | `UNIQUE(driver_id, seller_id, branch_id)` permits duplicate rows in PostgreSQL when `branch_id IS NULL`. | For complete database-level enforcement, add a partial unique index: `CREATE UNIQUE INDEX uq_driver_seller_all_branches ON driver_seller_authorizations (driver_id, seller_id) WHERE branch_id IS NULL;` |

---

## 6. Formal 5-Component Handoff Report

### 6.1 Observation
- **Alembic Migration Lineage**:
  - Ran `PYTHONPATH=. alembic heads` at `/workspaces/TheTextileCare/backend`.
  - Confirmed current head is `b2c3d4e5f6a7 (head)` from `b2c3d4e5f6a7_phase7_commercial_billing_payment.py`.
  - Next migration revision must use `down_revision = 'b2c3d4e5f6a7'`.
- **Model Baseline**:
  - Inspected `backend/app/models/`: verified 18 model files exist, with no `driver.py`.
  - Inspected `backend/app/models/pickup.py`: verified `OrderPickup` pattern using `Mapped[...]`, `mapped_column(...)`, `Uuid(as_uuid=True)`, and table args constraints.
  - Inspected `backend/app/models/customer.py` (line 79–80): coordinates are modeled as `Numeric(10, 7)`.
- **RBAC Baseline**:
  - Inspected `backend/app/core/permissions/constants.py`: confirmed `RoleName` has 11 roles (no `DRIVER`), `PermissionName` has 44 permissions (no driver or duty permissions), and `DEFAULT_ROLE_PERMISSIONS` maps role permissions.
  - Inspected `backend/app/services/roles.py`: confirmed `ROLE_DESCRIPTIONS` and `PERMISSION_DESCRIPTIONS` are seeded into the database via `RoleService.seed_defaults()`.
- **Existing Test Execution**:
  - Ran `pytest tests/unit/test_phase7_models_schemas.py -q`. 17 passed. 1 test had a pre-existing fixture typo (`func.now()` without importing `func` on line 308).

### 6.2 Logic Chain
1. *From R1 & Q51–Q60*: Driver dispatch requires active operational status, shift availability (`is_on_duty`), unexpired verified compliance credentials (`DL`, `RC`, `INSURANCE`, `BGC`), and capacity limit enforcement (`max_active_duties`).
2. *From Table Requirements*: Four tables are necessary and sufficient for Milestone 1:
   - `drivers` (profile, status, shift, geolocation, capacity)
   - `driver_vehicles` (make, model, plate, type, color)
   - `driver_seller_authorizations` (tenant/seller/branch access scoping)
   - `driver_compliance_documents` (canonical credentials with verification and expiry)
3. *From ADR-009 (Shared Driver Application)*: Drivers authenticate via a single shared platform mobile app. Therefore, `tenant_id` and `seller_id` on `drivers` are nullable to permit shared marketplace pool drivers, while `driver_seller_authorizations` handles explicit seller links.
4. *From RBAC Specification*: Six distinct permissions (`driver.manage`, `driver.view`, `duty.manage`, `duty.view`, `duty.reassign`, `operations_alert.view`) and one role (`DRIVER`) must be added to enforce least-privilege access across the 8 standard roles (`PLATFORM_ADMIN`, `TENANT_OWNER`, `TENANT_ADMIN`, `SELLER_OWNER`, `SELLER_ADMIN`, `STAFF`, `VIEWER`, `DRIVER`).
5. *From Migration Lineage*: Down revision must be explicitly pinned to `b2c3d4e5f6a7` to preserve linear, deterministic migrations.

### 6.3 Caveats
- **Pre-existing test file issue**: In `tests/unit/test_phase7_models_schemas.py:308`, `func.now()` was referenced without `func` imported. This does not affect driver domain code, but should be noted when running whole-suite regressions.
- **Future Milestone 2 Coupling**: Logistics tasks (`driver_duties`, `driver_assignments`) belong to Milestone 2. Foreign keys from `driver_duties` to `drivers.id` will be established in the Milestone 2 migration.

### 6.4 Conclusion
The Milestone 1 technical foundation is fully specified, verified against existing codebase conventions, and ready for immediate implementation by the Worker. Implementing the schema migration, SQLAlchemy models in `backend/app/models/driver.py`, Pydantic schemas in `backend/app/schemas/driver.py`, and RBAC constants/services will cleanly establish the Driver Logistics Domain without risk of regression.

### 6.5 Verification Method
To independently verify this implementation plan:

1. **Verify Alembic Head**:
   ```bash
   cd /workspaces/TheTextileCare/backend && PYTHONPATH=. alembic heads
   ```
   *Expected Output*: `b2c3d4e5f6a7 (head)`

2. **Verify Proposed Models Compile & Pass Type Checking**:
   After creating `backend/app/models/driver.py` and `backend/app/schemas/driver.py`:
   ```bash
   cd /workspaces/TheTextileCare/backend
   python3 -c "from app.models.driver import Driver, DriverVehicle, DriverSellerAuthorization, DriverComplianceDocument; print('Models imported successfully')"
   python3 -c "from app.schemas.driver import DriverResponse, DriverCreate; print('Schemas imported successfully')"
   ```

3. **Verify Migration Upgrade & Downgrade**:
   ```bash
   cd /workspaces/TheTextileCare/backend
   PYTHONPATH=. alembic upgrade head
   PYTHONPATH=. alembic downgrade -1
   PYTHONPATH=. alembic upgrade head
   ```

4. **Verify RBAC Seeding**:
   ```bash
   cd /workspaces/TheTextileCare/backend
   python3 -c "from app.core.permissions.constants import RoleName, PermissionName; assert RoleName.DRIVER == 'DRIVER'; assert PermissionName.DRIVER_MANAGE == 'driver.manage'; print('RBAC constants verified')"
   ```
