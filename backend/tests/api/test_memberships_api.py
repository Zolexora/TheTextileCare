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


def test_list_tenant_members():
    owner = create_test_user('owner@example.com')
    member = create_test_user('member@example.com')
    tenant = create_test_tenant('Test Corp')
    create_test_membership(tenant.id, owner.id, 'TENANT_OWNER')
    create_test_membership(tenant.id, member.id, 'TENANT_MEMBER')

    response = client.get(
        '/api/v1/tenants/current/members',
        headers=make_auth_headers(owner, tenant),
    )
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 2
    roles = {item['role'] for item in data['items']}
    assert roles == {'TENANT_OWNER', 'TENANT_MEMBER'}


def test_add_member_by_email():
    owner = create_test_user('owner@example.com')
    tenant = create_test_tenant('Test Corp')
    create_test_membership(tenant.id, owner.id, 'TENANT_OWNER')

    response = client.post(
        '/api/v1/tenants/current/members',
        json={'email': 'newinvite@example.com', 'role': 'TENANT_MEMBER'},
        headers=make_auth_headers(owner, tenant),
    )
    assert response.status_code == 201
    data = response.json()['membership']
    assert data['email'] == 'newinvite@example.com'
    assert data['role'] == 'TENANT_MEMBER'
    assert data['status'] == 'ACTIVE'


def test_cannot_add_duplicate_member_to_tenant():
    owner = create_test_user('owner@example.com')
    existing = create_test_user('existing@example.com')
    tenant = create_test_tenant('Test Corp')
    create_test_membership(tenant.id, owner.id, 'TENANT_OWNER')
    create_test_membership(tenant.id, existing.id, 'TENANT_MEMBER')

    response = client.post(
        '/api/v1/tenants/current/members',
        json={'email': 'existing@example.com', 'role': 'TENANT_MEMBER'},
        headers=make_auth_headers(owner, tenant),
    )
    assert response.status_code == 409


def test_update_member_role():
    owner = create_test_user('owner@example.com')
    member = create_test_user('member@example.com')
    tenant = create_test_tenant('Test Corp')
    create_test_membership(tenant.id, owner.id, 'TENANT_OWNER')
    m = create_test_membership(tenant.id, member.id, 'TENANT_MEMBER')

    response = client.patch(
        f'/api/v1/tenants/current/members/{m.id}',
        json={'role': 'TENANT_ADMIN'},
        headers=make_auth_headers(owner, tenant),
    )
    assert response.status_code == 200
    assert response.json()['membership']['role'] == 'TENANT_ADMIN'


def test_suspend_member():
    owner = create_test_user('owner@example.com')
    member = create_test_user('member@example.com')
    tenant = create_test_tenant('Test Corp')
    create_test_membership(tenant.id, owner.id, 'TENANT_OWNER')
    m = create_test_membership(tenant.id, member.id, 'TENANT_MEMBER')

    response = client.patch(
        f'/api/v1/tenants/current/members/{m.id}',
        json={'status': 'SUSPENDED'},
        headers=make_auth_headers(owner, tenant),
    )
    assert response.status_code == 200
    assert response.json()['membership']['status'] == 'SUSPENDED'


def test_remove_member():
    owner = create_test_user('owner@example.com')
    member = create_test_user('member@example.com')
    tenant = create_test_tenant('Test Corp')
    create_test_membership(tenant.id, owner.id, 'TENANT_OWNER')
    m = create_test_membership(tenant.id, member.id, 'TENANT_MEMBER')

    response = client.delete(
        f'/api/v1/tenants/current/members/{m.id}',
        headers=make_auth_headers(owner, tenant),
    )
    assert response.status_code == 204

    # Verify member is gone
    get_res = client.get(
        '/api/v1/tenants/current/members',
        headers=make_auth_headers(owner, tenant),
    )
    assert get_res.json()['total'] == 1
