from __future__ import annotations

from app.main import app
from fastapi.testclient import TestClient
from tests.conftest import (
    create_test_membership,
    create_test_tenant,
    create_test_user,
    make_auth_headers,
)

client = TestClient(app)


def test_member_cannot_modify_own_role():
    user = create_test_user('member@example.com')
    tenant = create_test_tenant('Test Corp')
    membership = create_test_membership(tenant.id, user.id, 'TENANT_MEMBER')

    response = client.patch(
        f'/api/v1/tenants/current/members/{membership.id}',
        json={'role': 'TENANT_ADMIN'},
        headers=make_auth_headers(user, tenant),
    )
    # Denied because member lacks membership.manage AND self-modification is forbidden
    assert response.status_code == 403


def test_member_cannot_promote_other_user():
    member = create_test_user('member@example.com')
    other = create_test_user('other@example.com')
    tenant = create_test_tenant('Test Corp')
    create_test_membership(tenant.id, member.id, 'TENANT_MEMBER')
    other_membership = create_test_membership(tenant.id, other.id, 'TENANT_MEMBER')

    response = client.patch(
        f'/api/v1/tenants/current/members/{other_membership.id}',
        json={'role': 'TENANT_ADMIN'},
        headers=make_auth_headers(member, tenant),
    )
    assert response.status_code == 403


def test_tenant_admin_cannot_promote_to_tenant_owner():
    admin = create_test_user('admin@example.com')
    other = create_test_user('other@example.com')
    tenant = create_test_tenant('Test Corp')
    create_test_membership(tenant.id, admin.id, 'TENANT_ADMIN')
    other_membership = create_test_membership(tenant.id, other.id, 'TENANT_MEMBER')

    response = client.patch(
        f'/api/v1/tenants/current/members/{other_membership.id}',
        json={'role': 'TENANT_OWNER'},
        headers=make_auth_headers(admin, tenant),
    )
    assert response.status_code == 403


def test_tenant_admin_cannot_modify_tenant_owner():
    owner = create_test_user('owner@example.com')
    admin = create_test_user('admin@example.com')
    tenant = create_test_tenant('Test Corp')
    owner_membership = create_test_membership(tenant.id, owner.id, 'TENANT_OWNER')
    create_test_membership(tenant.id, admin.id, 'TENANT_ADMIN')

    # Admin tries to demote owner
    response = client.patch(
        f'/api/v1/tenants/current/members/{owner_membership.id}',
        json={'role': 'TENANT_MEMBER'},
        headers=make_auth_headers(admin, tenant),
    )
    assert response.status_code == 403


def test_tenant_users_cannot_assign_platform_roles():
    owner = create_test_user('owner@example.com')
    other = create_test_user('other@example.com')
    tenant = create_test_tenant('Test Corp')
    create_test_membership(tenant.id, owner.id, 'TENANT_OWNER')
    other_membership = create_test_membership(tenant.id, other.id, 'TENANT_MEMBER')

    # Owner tries to grant PLATFORM_ADMIN
    res_admin = client.patch(
        f'/api/v1/tenants/current/members/{other_membership.id}',
        json={'role': 'PLATFORM_ADMIN'},
        headers=make_auth_headers(owner, tenant),
    )
    assert res_admin.status_code == 403

    # Owner tries to grant PLATFORM_SUPPORT
    res_support = client.patch(
        f'/api/v1/tenants/current/members/{other_membership.id}',
        json={'role': 'PLATFORM_SUPPORT'},
        headers=make_auth_headers(owner, tenant),
    )
    assert res_support.status_code == 403


def test_tenant_owner_cannot_modify_themselves_to_other_role():
    owner = create_test_user('owner@example.com')
    tenant = create_test_tenant('Test Corp')
    membership = create_test_membership(tenant.id, owner.id, 'TENANT_OWNER')

    response = client.patch(
        f'/api/v1/tenants/current/members/{membership.id}',
        json={'role': 'TENANT_ADMIN'},
        headers=make_auth_headers(owner, tenant),
    )
    assert response.status_code in {400, 403}
