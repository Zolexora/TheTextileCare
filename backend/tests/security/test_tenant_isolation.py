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


def test_cross_tenant_tenant_read_denied():
    user_a = create_test_user('usera@alpha.com')
    tenant_a = create_test_tenant('Alpha Corp')
    create_test_membership(tenant_a.id, user_a.id, 'TENANT_OWNER')

    user_b = create_test_user('userb@beta.com')
    tenant_b = create_test_tenant('Beta Corp')
    create_test_membership(tenant_b.id, user_b.id, 'TENANT_OWNER')

    # User A tries to read Tenant B directly by ID
    response = client.get(
        f'/api/v1/tenants/{tenant_b.id}',
        headers=make_auth_headers(user_a, tenant_a),
    )
    assert response.status_code in {403, 404}


def test_cross_tenant_tenant_update_denied():
    user_a = create_test_user('usera@alpha.com')
    tenant_a = create_test_tenant('Alpha Corp')
    create_test_membership(tenant_a.id, user_a.id, 'TENANT_OWNER')

    user_b = create_test_user('userb@beta.com')
    tenant_b = create_test_tenant('Beta Corp')
    create_test_membership(tenant_b.id, user_b.id, 'TENANT_OWNER')

    # User A tries to modify Tenant B
    response = client.patch(
        f'/api/v1/tenants/{tenant_b.id}',
        json={'name': 'Hacked Tenant B'},
        headers=make_auth_headers(user_a, tenant_a),
    )
    assert response.status_code in {403, 404}


def test_cross_tenant_members_read_denied():
    user_a = create_test_user('usera@alpha.com')
    tenant_a = create_test_tenant('Alpha Corp')
    create_test_membership(tenant_a.id, user_a.id, 'TENANT_OWNER')

    user_b = create_test_user('userb@beta.com')
    tenant_b = create_test_tenant('Beta Corp')
    create_test_membership(tenant_b.id, user_b.id, 'TENANT_OWNER')

    response = client.get(
        f'/api/v1/tenants/{tenant_b.id}/members',
        headers=make_auth_headers(user_a, tenant_a),
    )
    assert response.status_code in {403, 404}


def test_cross_tenant_members_manipulation_denied():
    user_a = create_test_user('usera@alpha.com')
    tenant_a = create_test_tenant('Alpha Corp')
    create_test_membership(tenant_a.id, user_a.id, 'TENANT_OWNER')

    user_b = create_test_user('userb@beta.com')
    tenant_b = create_test_tenant('Beta Corp')
    membership_b = create_test_membership(tenant_b.id, user_b.id, 'TENANT_OWNER')

    # User A tries to modify membership in Tenant B
    response = client.patch(
        f'/api/v1/tenants/{tenant_b.id}/members/{membership_b.id}',
        json={'role': 'TENANT_ADMIN'},
        headers=make_auth_headers(user_a, tenant_a),
    )
    assert response.status_code in {403, 404}

    # User A tries to delete membership in Tenant B
    response_del = client.delete(
        f'/api/v1/tenants/{tenant_b.id}/members/{membership_b.id}',
        headers=make_auth_headers(user_a, tenant_a),
    )
    assert response_del.status_code in {403, 404}


def test_cross_tenant_audit_logs_denied():
    user_a = create_test_user('usera@alpha.com')
    tenant_a = create_test_tenant('Alpha Corp')
    create_test_membership(tenant_a.id, user_a.id, 'TENANT_OWNER')

    user_b = create_test_user('userb@beta.com')
    tenant_b = create_test_tenant('Beta Corp')
    create_test_membership(tenant_b.id, user_b.id, 'TENANT_OWNER')

    response = client.get(
        f'/api/v1/tenants/{tenant_b.id}/audit-logs',
        headers=make_auth_headers(user_a, tenant_a),
    )
    assert response.status_code in {403, 404}


def test_client_tenant_id_spoofing_rejected():
    user_a = create_test_user('usera@alpha.com')
    tenant_a = create_test_tenant('Alpha Corp')
    create_test_membership(tenant_a.id, user_a.id, 'TENANT_OWNER')

    _ = create_test_user('userb@beta.com')
    tenant_b = create_test_tenant('Beta Corp')

    # User A passes Tenant B's ID in header to /current
    response = client.get(
        '/api/v1/tenants/current',
        headers={'X-User-Id': str(user_a.id), 'X-Tenant-Id': str(tenant_b.id)},
    )
    assert response.status_code == 403


def test_multi_tenant_user_switching_enforces_roles_per_tenant():
    user = create_test_user('multi@example.com')
    tenant_1 = create_test_tenant('Tenant One')
    tenant_2 = create_test_tenant('Tenant Two')

    create_test_membership(tenant_1.id, user.id, 'TENANT_OWNER')
    create_test_membership(tenant_2.id, user.id, 'TENANT_MEMBER')

    # In Tenant 1, user has TENANT_OWNER and can view members
    res1 = client.get(
        '/api/v1/tenants/current/members',
        headers={'X-User-Id': str(user.id), 'X-Tenant-Id': str(tenant_1.id)},
    )
    assert res1.status_code == 200

    # In Tenant 2, user is TENANT_MEMBER and cannot add members (requires membership.manage)
    other_user = create_test_user('other@example.com')
    res2 = client.post(
        '/api/v1/tenants/current/members',
        json={'user_id': str(other_user.id), 'role': 'TENANT_MEMBER'},
        headers={'X-User-Id': str(user.id), 'X-Tenant-Id': str(tenant_2.id)},
    )
    assert res2.status_code == 403
