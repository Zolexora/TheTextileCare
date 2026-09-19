import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from tests.api.test_orders import _create_user, _create_tenant, _make_seller_world, _customer_headers, _seller_headers, _order_payload

client = TestClient(app, raise_server_exceptions=False)

class TestSellerRejection:
    def _make_order(self, user, world):
        resp = client.post("/api/v1/orders", json=_order_payload(world), headers=_customer_headers(user))
        assert resp.status_code == 201
        return resp.json()

    def test_seller_can_reject_pending_order(self):
        tenant = _create_tenant(f"Rej1-{uuid.uuid4().hex[:4]}")
        seller_user = _create_user(f"srej1-{uuid.uuid4().hex[:4]}@test.com")
        cust = _create_user(f"crej1-{uuid.uuid4().hex[:4]}@test.com")
        world = _make_seller_world(tenant.id, seller_user.id)
        order = self._make_order(cust, world)
        
        resp = client.post(
            f"/api/v1/seller/orders/{order['id']}/reject",
            json={"cancellation_reason": "Out of service area"},
            headers=_seller_headers(seller_user, tenant.id)
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "CANCELLED"
        assert resp.json()["cancellation_reason"] == "Out of service area"

    def test_seller_cannot_reject_confirmed_order(self):
        tenant = _create_tenant(f"Rej2-{uuid.uuid4().hex[:4]}")
        seller_user = _create_user(f"srej2-{uuid.uuid4().hex[:4]}@test.com")
        cust = _create_user(f"crej2-{uuid.uuid4().hex[:4]}@test.com")
        world = _make_seller_world(tenant.id, seller_user.id)
        order = self._make_order(cust, world)
        
        client.post(f"/api/v1/seller/orders/{order['id']}/confirm", json={}, headers=_seller_headers(seller_user, tenant.id))
        
        resp = client.post(
            f"/api/v1/seller/orders/{order['id']}/reject",
            json={"cancellation_reason": "Out of service area"},
            headers=_seller_headers(seller_user, tenant.id)
        )
        assert resp.status_code == 409
        assert "INVALID_ORDER_STATUS_TRANSITION" in resp.json()["error"]["code"]

    def test_seller_cannot_cancel_pending_order_via_cancel_endpoint(self):
        tenant = _create_tenant(f"Rej3-{uuid.uuid4().hex[:4]}")
        seller_user = _create_user(f"srej3-{uuid.uuid4().hex[:4]}@test.com")
        cust = _create_user(f"crej3-{uuid.uuid4().hex[:4]}@test.com")
        world = _make_seller_world(tenant.id, seller_user.id)
        order = self._make_order(cust, world)
        
        resp = client.post(
            f"/api/v1/seller/orders/{order['id']}/cancel",
            json={"cancellation_reason": "Mistake"},
            headers=_seller_headers(seller_user, tenant.id)
        )
        assert resp.status_code == 409
        assert "cannot be cancelled by the seller" in resp.json()["error"]["message"]

