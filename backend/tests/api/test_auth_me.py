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


def test_auth_me_unauthenticated_returns_401():
    response = client.get('/api/v1/auth/me')
    assert response.status_code == 401


def test_auth_me_authenticated_returns_profile():
    user = create_test_user('testuser@example.com', name='Test User')
    tenant = create_test_tenant('Test Tenant')
    create_test_membership(tenant.id, user.id, 'TENANT_OWNER')

    response = client.get('/api/v1/auth/me', headers=make_auth_headers(user))
    assert response.status_code == 200
    data = response.json()
    assert data['user']['email'] == 'testuser@example.com'
    assert data['user']['name'] == 'Test User'
    assert len(data['tenants']) == 1
    assert data['tenants'][0]['slug'] == 'test-tenant'
    assert len(data['memberships']) == 1
    assert data['memberships'][0]['role'] == 'TENANT_OWNER'


def test_suspended_user_is_rejected():
    user = create_test_user('suspended@example.com')
    # Update status to SUSPENDED
    from app.db import SessionLocal
    from app.models import User

    with SessionLocal() as db:
        u = db.get(User, user.id)
        u.status = 'SUSPENDED'
        db.commit()

    response = client.get('/api/v1/auth/me', headers=make_auth_headers(user))
    assert response.status_code == 403
