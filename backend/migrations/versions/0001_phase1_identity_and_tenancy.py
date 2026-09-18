"""Phase 1: identity, tenancy, membership, rbac, and audit schema

Revision ID: 0001_phase1
Revises:
Create Date: 2026-09-18 07:56:00.000000

"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import column, table

# revision identifiers, used by Alembic.
revision: str = '0001_phase1'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. users table
    op.create_table(
        'users',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('auth_user_id', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='ACTIVE'),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index('ix_users_auth_user_id', 'users', ['auth_user_id'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 2. tenants table
    op.create_table(
        'tenants',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='ACTIVE'),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index('ix_tenants_slug', 'tenants', ['slug'], unique=True)

    # 3. roles table
    op.create_table(
        'roles',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('is_platform_role', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index('ix_roles_name', 'roles', ['name'], unique=True)

    # 4. permissions table
    op.create_table(
        'permissions',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index('ix_permissions_name', 'permissions', ['name'], unique=True)

    # 5. role_permissions table
    op.create_table(
        'role_permissions',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            'role_id',
            sa.Uuid(as_uuid=True),
            sa.ForeignKey('roles.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'permission_id',
            sa.Uuid(as_uuid=True),
            sa.ForeignKey('permissions.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint('role_id', 'permission_id', name='uq_role_permission'),
    )
    op.create_index('ix_role_permissions_role_id', 'role_permissions', ['role_id'])
    op.create_index('ix_role_permissions_permission_id', 'role_permissions', ['permission_id'])

    # 6. memberships table
    op.create_table(
        'memberships',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            'tenant_id',
            sa.Uuid(as_uuid=True),
            sa.ForeignKey('tenants.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'user_id',
            sa.Uuid(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column(
            'role_id',
            sa.Uuid(as_uuid=True),
            sa.ForeignKey('roles.id', ondelete='RESTRICT'),
            nullable=False,
        ),
        sa.Column('status', sa.String(50), nullable=False, server_default='ACTIVE'),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            'updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint('tenant_id', 'user_id', name='uq_tenant_user_membership'),
    )
    op.create_index('ix_memberships_tenant_id', 'memberships', ['tenant_id'])
    op.create_index('ix_memberships_user_id', 'memberships', ['user_id'])
    op.create_index('ix_memberships_role_id', 'memberships', ['role_id'])

    # 7. audit_events table
    op.create_table(
        'audit_events',
        sa.Column('id', sa.Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column(
            'tenant_id',
            sa.Uuid(as_uuid=True),
            sa.ForeignKey('tenants.id', ondelete='CASCADE'),
            nullable=True,
        ),
        sa.Column(
            'actor_user_id',
            sa.Uuid(as_uuid=True),
            sa.ForeignKey('users.id', ondelete='SET NULL'),
            nullable=True,
        ),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(100), nullable=True),
        sa.Column('entity_id', sa.String(100), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index('ix_audit_events_tenant_id', 'audit_events', ['tenant_id'])
    op.create_index('ix_audit_events_actor_user_id', 'audit_events', ['actor_user_id'])
    op.create_index('ix_audit_events_event_type', 'audit_events', ['event_type'])

    # 8. Seed permissions and roles
    permissions_table = table(
        'permissions',
        column('id', sa.Uuid(as_uuid=True)),
        column('name', sa.String),
        column('description', sa.String),
    )
    roles_table = table(
        'roles',
        column('id', sa.Uuid(as_uuid=True)),
        column('name', sa.String),
        column('description', sa.String),
        column('is_platform_role', sa.Boolean),
    )
    role_permissions_table = table(
        'role_permissions',
        column('id', sa.Uuid(as_uuid=True)),
        column('role_id', sa.Uuid(as_uuid=True)),
        column('permission_id', sa.Uuid(as_uuid=True)),
    )

    perm_defs = [
        ('tenant.read', 'View tenant details and configuration'),
        ('tenant.manage', 'Modify tenant configuration and settings'),
        ('membership.read', 'View tenant membership roster and roles'),
        ('membership.manage', 'Add, modify, or remove tenant memberships'),
        ('role.read', 'View role and permission definitions'),
        ('role.manage', 'Manage roles and permission mappings'),
        ('user.read', 'View user profile information'),
        ('user.manage', 'Manage user profiles and statuses'),
        ('audit.read', 'View audit logs for authorized scope'),
    ]
    perm_id_map: dict[str, uuid.UUID] = {}
    for name, desc in perm_defs:
        pid = uuid.uuid4()
        perm_id_map[name] = pid
        op.bulk_insert(permissions_table, [{'id': pid, 'name': name, 'description': desc}])

    role_defs = [
        ('PLATFORM_ADMIN', 'Platform super administrator with unrestricted access', True),
        ('PLATFORM_SUPPORT', 'Platform support personnel with operational visibility', True),
        ('TENANT_OWNER', 'Tenant owner with complete organizational control', False),
        ('TENANT_ADMIN', 'Tenant administrator managing members and settings', False),
        ('TENANT_MEMBER', 'Standard tenant member with operational permissions', False),
        ('TENANT_VIEWER', 'Read-only tenant viewer', False),
    ]
    role_id_map: dict[str, uuid.UUID] = {}
    for name, desc, is_platform in role_defs:
        rid = uuid.uuid4()
        role_id_map[name] = rid
        op.bulk_insert(
            roles_table,
            [{'id': rid, 'name': name, 'description': desc, 'is_platform_role': is_platform}],
        )

    matrix = {
        'PLATFORM_ADMIN': [
            'tenant.read',
            'tenant.manage',
            'membership.read',
            'membership.manage',
            'role.read',
            'role.manage',
            'user.read',
            'user.manage',
            'audit.read',
        ],
        'PLATFORM_SUPPORT': [
            'tenant.read',
            'membership.read',
            'role.read',
            'user.read',
            'audit.read',
        ],
        'TENANT_OWNER': [
            'tenant.read',
            'tenant.manage',
            'membership.read',
            'membership.manage',
            'role.read',
            'user.read',
            'audit.read',
        ],
        'TENANT_ADMIN': [
            'tenant.read',
            'tenant.manage',
            'membership.read',
            'membership.manage',
            'role.read',
            'user.read',
            'audit.read',
        ],
        'TENANT_MEMBER': [
            'tenant.read',
            'membership.read',
            'user.read',
        ],
        'TENANT_VIEWER': [
            'tenant.read',
        ],
    }

    mappings = []
    for r_name, p_names in matrix.items():
        rid = role_id_map[r_name]
        for p_name in p_names:
            pid = perm_id_map[p_name]
            mappings.append({'id': uuid.uuid4(), 'role_id': rid, 'permission_id': pid})

    if mappings:
        op.bulk_insert(role_permissions_table, mappings)


def downgrade() -> None:
    op.drop_table('audit_events')
    op.drop_table('memberships')
    op.drop_table('role_permissions')
    op.drop_table('permissions')
    op.drop_table('roles')
    op.drop_table('tenants')
    op.drop_table('users')
