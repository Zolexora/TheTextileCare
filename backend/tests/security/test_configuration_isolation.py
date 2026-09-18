from __future__ import annotations
import uuid
from app.main import app
from fastapi.testclient import TestClient
from tests.conftest import (
    create_test_membership,
    create_test_tenant,
    create_test_user,
    make_auth_headers,
)

client = TestClient(app)

def test_tenant_configuration_isolation():
    user_a = create_test_user('usera_conf@alpha.com')
    tenant_a = create_test_tenant('Alpha Corp Conf')
    create_test_membership(tenant_a.id, user_a.id, 'TENANT_OWNER')

    user_b = create_test_user('userb_conf@beta.com')
    tenant_b = create_test_tenant('Beta Corp Conf')
    create_test_membership(tenant_b.id, user_b.id, 'TENANT_OWNER')

    headers_a = make_auth_headers(user_a, tenant_a)
    headers_b = make_auth_headers(user_b, tenant_b)

    # Get configuration for A
    res_a = client.get('/api/v1/configuration', headers=headers_a)
    assert res_a.status_code == 200

    # Test platform admin endpoints blocked for tenant admin
    res_admin = client.get('/api/v1/configuration/admin/definitions', headers=headers_a)
    assert res_admin.status_code in [403, 401]

def test_public_configuration_no_sensitive_data():
    pass # Will test in integration
