import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.api.test_orders import _create_user, _create_tenant, _make_seller_world, _customer_headers, _seller_headers, _order_payload

client = TestClient(app, raise_server_exceptions=False)

def test_customer_can_cancel_confirmed_order():
    tenant = _create_tenant(f"Can3-{uuid.uuid4().hex[:4]}")
    seller_user = _create_user(f"scan3-{uuid.uuid4().hex[:4]}@test.com")
    cust = _create_user(f"ccan3-{uuid.uuid4().hex[:4]}@test.com")
    world = _make_seller_world(tenant.id, seller_user.id)

    # 1. Customer creates order
    resp = client.post("/api/v1/orders", json=_order_payload(world), headers=_customer_headers(cust))
    order_id = resp.json()["id"]

    # 2. Seller confirms order
    client.post(f"/api/v1/seller/orders/{order_id}/confirm", json={}, headers=_seller_headers(seller_user, tenant.id))

    # 3. Customer cancels confirmed order
    cancel_resp = client.post(
        f"/api/v1/orders/{order_id}/cancel",
        json={"cancellation_reason": "Too late"},
        headers=_customer_headers(cust),
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"
    assert cancel_resp.json()["cancellation_reason"] == "CUSTOMER_CANCELLED: Too late"

def test_seller_can_cancel_confirmed_order():
    tenant = _create_tenant(f"Can4-{uuid.uuid4().hex[:4]}")
    seller_user = _create_user(f"scan4-{uuid.uuid4().hex[:4]}@test.com")
    cust = _create_user(f"ccan4-{uuid.uuid4().hex[:4]}@test.com")
    world = _make_seller_world(tenant.id, seller_user.id)

    resp = client.post("/api/v1/orders", json=_order_payload(world), headers=_customer_headers(cust))
    order_id = resp.json()["id"]

    client.post(f"/api/v1/seller/orders/{order_id}/confirm", json={}, headers=_seller_headers(seller_user, tenant.id))

    cancel_resp = client.post(
        f"/api/v1/seller/orders/{order_id}/cancel",
        json={"cancellation_reason": "Machine broke"},
        headers=_seller_headers(seller_user, tenant.id),
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "CANCELLED"
    assert cancel_resp.json()["cancellation_reason"] == "SELLER_CANCELLED: Machine broke"

def test_customer_cannot_cancel_completed_order():
    tenant = _create_tenant(f"Can5-{uuid.uuid4().hex[:4]}")
    seller_user = _create_user(f"scan5-{uuid.uuid4().hex[:4]}@test.com")
    cust = _create_user(f"ccan5-{uuid.uuid4().hex[:4]}@test.com")
    world = _make_seller_world(tenant.id, seller_user.id)

    resp = client.post("/api/v1/orders", json=_order_payload(world), headers=_customer_headers(cust))
    order_id = resp.json()["id"]

    client.post(f"/api/v1/seller/orders/{order_id}/confirm", json={}, headers=_seller_headers(seller_user, tenant.id))
    client.post(f"/api/v1/seller/orders/{order_id}/start", json={}, headers=_seller_headers(seller_user, tenant.id))
    client.post(f"/api/v1/seller/orders/{order_id}/complete", json={}, headers=_seller_headers(seller_user, tenant.id))

    cancel_resp = client.post(
        f"/api/v1/orders/{order_id}/cancel",
        json={"cancellation_reason": "I want a refund"},
        headers=_customer_headers(cust),
    )
    assert cancel_resp.status_code == 409
    assert "cannot be cancelled by the customer" in cancel_resp.json()["error"]["message"]

