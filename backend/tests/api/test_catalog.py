from __future__ import annotations
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.conftest import create_test_membership, create_test_tenant, create_test_user, make_auth_headers
from app.db import SessionLocal
from app.models.seller import Seller

client = TestClient(app)

def create_test_seller(tenant_id: uuid.UUID) -> Seller:
    with SessionLocal() as db:
        seller = Seller(tenant_id=tenant_id, business_name='Test Seller', slug=f'test-seller-{uuid.uuid4()}')
        db.add(seller)
        db.commit()
        db.refresh(seller)
        return seller

def test_catalog_lifecycle():
    user = create_test_user('catalog_admin@alpha.com')
    tenant = create_test_tenant('Alpha Corp')
    create_test_membership(tenant.id, user.id, 'SELLER_ADMIN')
    seller = create_test_seller(tenant.id)
    headers = make_auth_headers(user, tenant)

    # 1. Create Catalog
    res = client.post('/api/v1/catalog', headers=headers, json={
        "seller_id": str(seller.id),
        "name": "Main Catalog",
        "description": "Standard offerings"
    })
    assert res.status_code == 201
    catalog = res.json()
    catalog_id = catalog['id']
    assert catalog['name'] == "Main Catalog"
    assert catalog['status'] == "DRAFT"

    # 2. Get Seller Catalogs
    res = client.get(f'/api/v1/catalog/seller/{seller.id}', headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 1

    # 3. Create Category
    res = client.post(f'/api/v1/catalog/{catalog_id}/categories', headers=headers, json={
        "name": "Dry Cleaning",
        "slug": "dry-cleaning"
    })
    assert res.status_code == 201
    category_id = res.json()['id']

    # 4. Create Service
    res = client.post(f'/api/v1/catalog/{catalog_id}/services', headers=headers, json={
        "category_id": category_id,
        "name": "Shirt Dry Cleaning",
        "slug": "shirt-dry-cleaning",
        "service_type": "SERVICE"
    })
    assert res.status_code == 201
    service_id = res.json()['id']

    # 5. Create Service Item
    res = client.post(f'/api/v1/catalog/{catalog_id}/services/{service_id}/items', headers=headers, json={
        "name": "Silk Shirt",
        "unit_type": "ITEM"
    })
    assert res.status_code == 201

    # 6. Create Service Addon
    res = client.post(f'/api/v1/catalog/{catalog_id}/services/{service_id}/addons', headers=headers, json={
        "name": "Stain Removal",
        "code": "STAIN_REM"
    })
    assert res.status_code == 201

    # 7. Activate Catalog
    res = client.post(f'/api/v1/catalog/{catalog_id}/activate', headers=headers)
    assert res.status_code == 200
    assert res.json()['status'] == "ACTIVE"

def test_tenant_isolation_and_id_injection():
    user_a = create_test_user('tenant_a@alpha.com')
    tenant_a = create_test_tenant('Tenant A')
    create_test_membership(tenant_a.id, user_a.id, 'SELLER_ADMIN')
    seller_a = create_test_seller(tenant_a.id)
    headers_a = make_auth_headers(user_a, tenant_a)

    user_b = create_test_user('tenant_b@beta.com')
    tenant_b = create_test_tenant('Tenant B')
    create_test_membership(tenant_b.id, user_b.id, 'SELLER_ADMIN')
    seller_b = create_test_seller(tenant_b.id)
    headers_b = make_auth_headers(user_b, tenant_b)

    # 1. Tenant A creates Catalog
    res = client.post('/api/v1/catalog', headers=headers_a, json={
        "seller_id": str(seller_a.id),
        "name": "A Catalog"
    })
    catalog_a_id = res.json()['id']

    # 2. Tenant B tries to read Tenant A catalog
    res = client.get(f'/api/v1/catalog/{catalog_a_id}', headers=headers_b)
    assert res.status_code == 404

    # 3. Tenant B tries to create Catalog for Tenant A seller
    res = client.post('/api/v1/catalog', headers=headers_b, json={
        "seller_id": str(seller_a.id),
        "name": "B Hack Catalog"
    })
    assert res.status_code == 404

    # 4. Tenant B tries to create a category in Tenant A catalog
    res = client.post(f'/api/v1/catalog/{catalog_a_id}/categories', headers=headers_b, json={
        "name": "Hack Category",
        "slug": "hack"
    })
    assert res.status_code == 404

def test_permission_enforcement():
    user = create_test_user('viewer@alpha.com')
    tenant = create_test_tenant('Viewer Corp')
    # Use VIEWER role which has catalog.read but not catalog.manage
    create_test_membership(tenant.id, user.id, 'VIEWER')
    seller = create_test_seller(tenant.id)
    headers = make_auth_headers(user, tenant)

    # Viewer tries to create catalog
    res = client.post('/api/v1/catalog', headers=headers, json={
        "seller_id": str(seller.id),
        "name": "Viewer Catalog"
    })
    assert res.status_code == 403

