from __future__ import annotations

import uuid

import pytest
from app.db import Base, SessionLocal, engine
from app.models.membership import Membership
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.memberships import MembershipRepository
from app.repositories.tenants import TenantRepository
from app.repositories.users import UserRepository
from app.services.roles import RoleService


@pytest.fixture(autouse=True)
def reset_database():
    """Reset database tables and seed defaults before each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        RoleService(db).seed_defaults()
    yield


def create_test_user(email: str, name: str | None = None, auth_user_id: str | None = None) -> User:
    with SessionLocal() as db:
        repo = UserRepository(db)
        return repo.create_or_get(
            email=email,
            auth_user_id=auth_user_id or f'auth-{email}',
            name=name or email.split('@')[0],
        )


def create_test_tenant(name: str, slug: str | None = None) -> Tenant:
    with SessionLocal() as db:
        repo = TenantRepository(db)
        actual_slug = slug or name.lower().replace(' ', '-')
        return repo.create(name=name, slug=actual_slug)


def create_test_membership(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    role_name: str,
    status: str = 'ACTIVE',
) -> Membership:
    with SessionLocal() as db:
        repo = MembershipRepository(db)
        return repo.create(
            tenant_id=tenant_id,
            user_id=user_id,
            role_name=role_name,
            status=status,
        )


def make_auth_headers(user: User, tenant: Tenant | None = None) -> dict[str, str]:
    headers = {'X-User-Id': str(user.id)}
    if tenant:
        headers['X-Tenant-Id'] = str(tenant.id)
    return headers
