from __future__ import annotations

from app.main import app
from app.repositories.audit import sanitize_payload
from fastapi.testclient import TestClient
from tests.conftest import (
    create_test_membership,
    create_test_tenant,
    create_test_user,
    make_auth_headers,
)

client = TestClient(app)


def test_audit_logs_created_and_accessible_by_tenant_owner():
    owner = create_test_user('owner@example.com')
    tenant = create_test_tenant('Audit Tenant')
    create_test_membership(tenant.id, owner.id, 'TENANT_OWNER')

    # Perform action: add a member
    add_res = client.post(
        '/api/v1/tenants/current/members',
        json={'email': 'auditee@example.com', 'role': 'TENANT_MEMBER'},
        headers=make_auth_headers(owner, tenant),
    )
    assert add_res.status_code == 201

    # Query audit logs
    audit_res = client.get(
        '/api/v1/tenants/current/audit-logs',
        headers=make_auth_headers(owner, tenant),
    )
    assert audit_res.status_code == 200
    events = audit_res.json()['items']
    event_types = [e['event_type'] for e in events]
    assert 'MEMBERSHIP_CREATED' in event_types


def test_sensitive_data_sanitization_in_audit():
    raw_payload = {
        'username': 'alice',
        'password': 'super-secret-password',
        'api_key': 'key_12345',
        'nested': {
            'token': 'jwt.token.here',
            'email': 'alice@example.com',
        },
    }
    sanitized = sanitize_payload(raw_payload)
    assert sanitized['password'] == '[REDACTED]'
    assert sanitized['api_key'] == '[REDACTED]'
    assert sanitized['nested']['token'] == '[REDACTED]'
    assert sanitized['nested']['email'] == 'alice@example.com'
    assert sanitized['username'] == 'alice'


def test_platform_audit_logs_restricted_to_platform_admin():
    normal_owner = create_test_user('owner@example.com')
    tenant = create_test_tenant('Normal Tenant')
    create_test_membership(tenant.id, normal_owner.id, 'TENANT_OWNER')

    # Normal tenant owner attempts to view platform audit logs
    response = client.get(
        '/api/v1/platform/audit-logs',
        headers=make_auth_headers(normal_owner, tenant),
    )
    assert response.status_code == 403

    # Platform admin can access
    plat_admin = create_test_user('platadmin@platform.com')
    create_test_membership(tenant.id, plat_admin.id, 'PLATFORM_ADMIN')

    response_admin = client.get(
        '/api/v1/platform/audit-logs',
        headers=make_auth_headers(plat_admin, tenant),
    )
    assert response_admin.status_code == 200
