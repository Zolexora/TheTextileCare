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


def test_create_tenant():
    user = create_test_user('founder@example.com')

    response = client.post(
        '/api/v1/tenants',
        json={'name': 'Acme Cleaners', 'slug': 'acme-cleaners'},
        headers=make_auth_headers(user),
    )
    assert response.status_code == 201
    data = response.json()
    assert data['name'] == 'Acme Cleaners'
    assert data['slug'] == 'acme-cleaners'
    assert data['status'] == 'ACTIVE'


def test_create_tenant_duplicate_slug_conflict():
    user = create_test_user('founder@example.com')
    create_test_tenant('Existing Tenant', slug='duplicate-slug')

    response = client.post(
        '/api/v1/tenants',
        json={'name': 'Another Tenant', 'slug': 'duplicate-slug'},
        headers=make_auth_headers(user),
    )
    assert response.status_code == 409


def test_get_current_tenant():
    user = create_test_user('owner@example.com')
    tenant = create_test_tenant('My Laundry Service')
    create_test_membership(tenant.id, user.id, 'TENANT_OWNER')

    response = client.get(
        '/api/v1/tenants/current',
        headers=make_auth_headers(user, tenant),
    )
    assert response.status_code == 200
    assert response.json()['name'] == 'My Laundry Service'


def test_update_current_tenant():
    user = create_test_user('owner@example.com')
    tenant = create_test_tenant('Original Name')
    create_test_membership(tenant.id, user.id, 'TENANT_OWNER')

    response = client.patch(
        '/api/v1/tenants/current',
        json={'name': 'Updated Laundry Name'},
        headers=make_auth_headers(user, tenant),
    )
    assert response.status_code == 200
    assert response.json()['name'] == 'Updated Laundry Name'


def test_list_tenants_returns_user_tenants():
    user = create_test_user('owner@example.com')
    t1 = create_test_tenant('Tenant One')
    t2 = create_test_tenant('Tenant Two')
    _ = create_test_tenant('Tenant Other')  # not joined

    create_test_membership(t1.id, user.id, 'TENANT_OWNER')
    create_test_membership(t2.id, user.id, 'TENANT_MEMBER')

    response = client.get('/api/v1/tenants', headers=make_auth_headers(user))
    assert response.status_code == 200
    data = response.json()
    assert data['total'] == 2
    assert len(data['items']) == 2
