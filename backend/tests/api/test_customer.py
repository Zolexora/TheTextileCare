from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import create_test_user, make_auth_headers

client = TestClient(app)


def test_customer_profile_creation():
    user = create_test_user("cust1@example.com")
    headers = make_auth_headers(user)
    
    # Get profile (should create automatically)
    response = client.get("/api/v1/customer/profile", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ACTIVE"
    assert data["display_name"] == user.name
    
    # Update profile
    update_resp = client.patch(
        "/api/v1/customer/profile",
        headers=headers,
        json={"first_name": "John", "last_name": "Doe"}
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["first_name"] == "John"


def test_customer_address_management():
    user = create_test_user("cust2@example.com")
    headers = make_auth_headers(user)
    
    # Create first address (should become default)
    addr1 = client.post(
        "/api/v1/customer/addresses",
        headers=headers,
        json={
            "address_line_1": "123 Main St",
            "city": "Mumbai",
            "state": "MH",
            "postal_code": "400001",
            "label": "Home"
        }
    ).json()
    assert addr1["is_default"] is True
    
    # Create second address, explicit default
    addr2 = client.post(
        "/api/v1/customer/addresses",
        headers=headers,
        json={
            "address_line_1": "456 Office Rd",
            "city": "Mumbai",
            "state": "MH",
            "postal_code": "400002",
            "label": "Work",
            "is_default": True
        }
    ).json()
    assert addr2["is_default"] is True
    
    # First address should now not be default
    addresses = client.get("/api/v1/customer/addresses", headers=headers).json()
    assert len(addresses) == 2
    for a in addresses:
        if a["id"] == addr1["id"]:
            assert a["is_default"] is False
        if a["id"] == addr2["id"]:
            assert a["is_default"] is True


def test_customer_isolation():
    user1 = create_test_user("iso1@example.com")
    user2 = create_test_user("iso2@example.com")
    
    headers1 = make_auth_headers(user1)
    headers2 = make_auth_headers(user2)
    
    # User 1 creates an address
    addr1 = client.post(
        "/api/v1/customer/addresses",
        headers=headers1,
        json={
            "address_line_1": "User 1 St",
            "city": "Mumbai",
            "state": "MH",
            "postal_code": "400001"
        }
    ).json()
    
    # User 2 tries to read it (via update or direct list)
    addresses2 = client.get("/api/v1/customer/addresses", headers=headers2).json()
    assert len(addresses2) == 0
    
    # User 2 tries to update User 1's address
    update_resp = client.patch(
        f"/api/v1/customer/addresses/{addr1['id']}",
        headers=headers2,
        json={"label": "Hacked"}
    )
    assert update_resp.status_code == 404
