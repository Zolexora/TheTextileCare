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
        sa.Column('branch_id', sa.Uuid(), nullable=True),
        sa.Column('full_name', sa.String(length=255), server_default='', nullable=False),
        sa.Column('phone_number', sa.String(length=50), server_default='', nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='ACTIVE', nullable=False),
        sa.Column('is_on_duty', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('compliance_status', sa.String(length=50), server_default='PENDING', nullable=False),
        sa.Column('availability_status', sa.String(length=50), server_default='AVAILABLE', nullable=False),
        sa.Column('current_latitude', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('current_longitude', sa.Numeric(precision=10, scale=7), nullable=True),
        sa.Column('max_active_duties', sa.Integer(), server_default='3', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('ACTIVE', 'INACTIVE', 'ON_LEAVE', 'SUSPENDED')", name='ck_drivers_status'),
        sa.CheckConstraint("compliance_status IN ('PENDING', 'COMPLIANT', 'EXPIRED', 'REJECTED', 'SUSPENDED')", name='ck_drivers_compliance_status'),
        sa.CheckConstraint("availability_status IN ('AVAILABLE', 'BUSY', 'OFFLINE')", name='ck_drivers_availability_status'),
        sa.CheckConstraint("max_active_duties >= 1", name='ck_drivers_max_active_duties'),
        sa.ForeignKeyConstraint(['branch_id'], ['seller_branches.id'], ondelete='SET NULL'),
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
    op.create_index('ix_drivers_branch_id', 'drivers', ['branch_id'], unique=False)
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
        sa.Column('plate_number', sa.String(length=50), server_default='', nullable=False),
        sa.Column('license_plate', sa.String(length=50), nullable=True),
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
    op.create_index('ix_driver_vehicles_license_plate', 'driver_vehicles', ['license_plate'], unique=False)
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
