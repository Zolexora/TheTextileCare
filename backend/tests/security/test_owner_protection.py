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


def test_cannot_remove_sole_tenant_owner():
    owner = create_test_user('owner@example.com')
    tenant = create_test_tenant('Test Corp')
    membership = create_test_membership(tenant.id, owner.id, 'TENANT_OWNER')

    # Add a platform admin to perform the remove attempt to avoid self-modification check
    plat_admin = create_test_user('admin@platform.com')
    create_test_membership(tenant.id, plat_admin.id, 'PLATFORM_ADMIN')

    response = client.delete(
        f'/api/v1/tenants/current/members/{membership.id}',
        headers=make_auth_headers(plat_admin, tenant),
    )
    assert response.status_code == 400
    assert response.json()['error']['code'] == 'LAST_OWNER_PROTECTION'


def test_cannot_suspend_sole_tenant_owner():
    owner = create_test_user('owner@example.com')
    tenant = create_test_tenant('Test Corp')
    membership = create_test_membership(tenant.id, owner.id, 'TENANT_OWNER')

    plat_admin = create_test_user('admin@platform.com')
    create_test_membership(tenant.id, plat_admin.id, 'PLATFORM_ADMIN')

    response = client.patch(
        f'/api/v1/tenants/current/members/{membership.id}',
        json={'status': 'SUSPENDED'},
        headers=make_auth_headers(plat_admin, tenant),
    )
    assert response.status_code == 400
    assert response.json()['error']['code'] == 'LAST_OWNER_PROTECTION'


def test_can_remove_owner_if_another_owner_exists():
    owner1 = create_test_user('owner1@example.com')
    owner2 = create_test_user('owner2@example.com')
    tenant = create_test_tenant('Test Corp')
    m1 = create_test_membership(tenant.id, owner1.id, 'TENANT_OWNER')
    _ = create_test_membership(tenant.id, owner2.id, 'TENANT_OWNER')

    plat_admin = create_test_user('admin@platform.com')
    create_test_membership(tenant.id, plat_admin.id, 'PLATFORM_ADMIN')

    response = client.delete(
        f'/api/v1/tenants/current/members/{m1.id}',
        headers=make_auth_headers(plat_admin, tenant),
    )
    assert response.status_code == 204
