from __future__ import annotations

import pytest
from app.core.permissions.constants import (
    DEFAULT_ROLE_PERMISSIONS,
    PermissionName,
    RoleName,
)
from app.db import SessionLocal
from app.models.membership import Membership
from app.models.permission import Permission
from app.models.role import Role
from app.models.tenant import Tenant
from app.models.user import User
from app.services.roles import RoleService
from sqlalchemy.exc import IntegrityError


def test_seed_creates_all_expected_roles_and_permissions():
    with SessionLocal() as db:
        role_service = RoleService(db)
        role_service.seed_defaults()

        roles = {r.name: r for r in db.query(Role).all()}
        assert set(roles.keys()) == {r.value for r in RoleName}

        perms = {p.name: p for p in db.query(Permission).all()}
        assert set(perms.keys()) == {p.value for p in PermissionName}

        # Verify matrix mapping
        for role_name, expected_perms in DEFAULT_ROLE_PERMISSIONS.items():
            assigned_perms = role_service.get_permissions_for_role(role_name)
            assert assigned_perms == set(expected_perms)


def test_db_constraint_unique_role_name():
    with SessionLocal() as db:
        duplicate_role = Role(name='TENANT_OWNER', description='Duplicate')
        db.add(duplicate_role)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_db_constraint_unique_permission_name():
    with SessionLocal() as db:
        duplicate_perm = Permission(name='tenant.read', description='Duplicate')
        db.add(duplicate_perm)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_db_constraint_unique_tenant_slug():
    with SessionLocal() as db:
        t1 = Tenant(name='Tenant 1', slug='unique-slug-test')
        t2 = Tenant(name='Tenant 2', slug='unique-slug-test')
        db.add(t1)
        db.commit()

        db.add(t2)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_db_constraint_unique_tenant_user_membership():
    with SessionLocal() as db:
        tenant = Tenant(name='Test Tenant', slug='membership-test-slug')
        user = User(email='membertest@example.com', auth_user_id='auth-membertest')
        role = db.query(Role).filter_by(name='TENANT_MEMBER').first()
        db.add(tenant)
        db.add(user)
        db.commit()

        m1 = Membership(tenant_id=tenant.id, user_id=user.id, role_id=role.id)
        m2 = Membership(tenant_id=tenant.id, user_id=user.id, role_id=role.id)
        db.add(m1)
        db.commit()

        db.add(m2)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
