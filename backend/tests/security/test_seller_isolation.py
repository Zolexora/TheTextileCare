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


def test_seller_isolation():
    # Tenant A and its users
    user_a = create_test_user('usera@alpha.com')
    tenant_a = create_test_tenant('Alpha Corp')
    create_test_membership(tenant_a.id, user_a.id, 'TENANT_OWNER')

    # Tenant B and its users
    user_b = create_test_user('userb@beta.com')
    tenant_b = create_test_tenant('Beta Corp')
    create_test_membership(tenant_b.id, user_b.id, 'TENANT_OWNER')

    # Create Seller A
    res_a = client.post(
        '/api/v1/sellers',
        json={'business_name': 'Alpha Seller', 'slug': 'alpha-seller'},
        headers=make_auth_headers(user_a, tenant_a)
    )
    assert res_a.status_code == 201

    # User B tries to read Seller A (by pretending they are in tenant A context)
    res_b_bad = client.get(
        '/api/v1/sellers',
        headers=make_auth_headers(user_b, tenant_a)
    )
    # User B is not in tenant A, so this should 403
    assert res_b_bad.status_code == 403

    # Create Seller B
    res_b = client.post(
        '/api/v1/sellers',
        json={'business_name': 'Beta Seller', 'slug': 'beta-seller'},
        headers=make_auth_headers(user_b, tenant_b)
    )
    assert res_b.status_code == 201

    # Create Branch for Seller A
    res_branch_a = client.post(
        '/api/v1/sellers/branches',
        json={'name': 'Alpha Branch 1', 'code': 'A1'},
        headers=make_auth_headers(user_a, tenant_a)
    )
    assert res_branch_a.status_code == 201
    branch_a_id = res_branch_a.json()['id']

    # User B tries to update Branch A
    res_branch_b_bad = client.patch(
        f'/api/v1/sellers/branches/{branch_a_id}',
        json={'name': 'Hacked Branch'},
        headers=make_auth_headers(user_b, tenant_b)
    )
    # This should fail because branch_a_id belongs to Seller A, but User B is in context of Tenant B/Seller B
    assert res_branch_b_bad.status_code == 404

def test_seller_staff_isolation():
    # Tenant A and its users
    user_a = create_test_user('usera@alpha.com')
    tenant_a = create_test_tenant('Alpha Corp')
    create_test_membership(tenant_a.id, user_a.id, 'TENANT_OWNER')
    
    user_a2 = create_test_user('user_a2@alpha.com')
    create_test_membership(tenant_a.id, user_a2.id, 'STAFF')

    client.post(
        '/api/v1/sellers',
        json={'business_name': 'Alpha Seller', 'slug': 'alpha-seller'},
        headers=make_auth_headers(user_a, tenant_a)
    )

    # Invite staff in tenant A
    res_staff = client.post(
        '/api/v1/sellers/staff',
        json={'user_id': str(user_a2.id), 'display_name': 'Manager'},
        headers=make_auth_headers(user_a, tenant_a)
    )
    assert res_staff.status_code == 201

    # User not in tenant A tries to be invited
    user_b = create_test_user('userb@beta.com')
    res_staff_bad = client.post(
        '/api/v1/sellers/staff',
        json={'user_id': str(user_b.id), 'display_name': 'Hacker'},
        headers=make_auth_headers(user_a, tenant_a)
    )
    # Should fail because user_b is not in tenant_a
    assert res_staff_bad.status_code == 400

