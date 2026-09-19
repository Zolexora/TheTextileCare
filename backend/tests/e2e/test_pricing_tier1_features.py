"""Tier 1 E2E Feature Tests for TTC Phase 5: Pricing Engine Foundation.

Requirement Traceability:
- ORIGINAL_REQUEST.md: R1, R2, R3, R4, R5
- PROJECT.md: Features 1-6, 10, 11, 12, 13, 14, 15, 16
- survey_requirements.md: Sections 3, 4, 5, 6

This module exercises the primary happy paths for:
1. PriceBook CRUD (create, read, list/filter, update, delete) (>=5 tests)
2. PriceRule CRUD (create, list, update, delete, status toggle) (>=5 tests)
3. Calculation by Rule Type (FIXED, PER_ITEM, PER_UNIT, PER_WEIGHT, mixed) (>=5 tests)
4. 4-Tier Financial Breakdown (Base Price, Surcharge, Discount, Tax, and Invariant) (>=5 tests)
5. RBAC Permissions (pricing.manage, pricing.read, VIEWER mutation rejection, unauth rejection, member rejection) (>=5 tests)
6. AuditService Event Emission (Book created/updated, Rule created/updated/deleted) (>=5 tests)
"""
from __future__ import annotations

import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.models.audit import AuditEvent
from tests.e2e.conftest import (
    setup_tenant_and_actor,
    create_test_user,
    create_test_membership,
    make_auth_headers,
    assert_calculation_invariant,
)


def _activate_book(client: TestClient, book_id: str, headers: dict[str, str]) -> None:
    """Helper to activate a book either via /activate endpoint or PATCH/PUT status."""
    res = client.post(f"/api/v1/pricing/books/{book_id}/activate", headers=headers)
    if res.status_code != 200:
        # Try PATCH
        res_patch = client.patch(f"/api/v1/pricing/books/{book_id}", headers=headers, json={"status": "ACTIVE"})
        if res_patch.status_code != 200:
            client.put(f"/api/v1/pricing/books/{book_id}", headers=headers, json={"status": "ACTIVE"})


# ============================================================================
# FEATURE 1: PriceBook CRUD Lifecycle (>=5 tests)
# ============================================================================

def test_feature_price_book_create_success(client: TestClient):
    """F-01.1: Verify creation of a tenant seller price book."""
    env = setup_tenant_and_actor()
    payload = {
        "seller_id": str(env["seller"].id),
        "name": "Standard Seller Catalog Pricing",
        "description": "Base pricing book for primary seller",
        "currency": "USD",
        "is_default": True,
    }
    res = client.post("/api/v1/pricing/books", headers=env["headers"], json=payload)
    assert res.status_code == 201, f"Failed: {res.text}"
    data = res.json()
    assert data["name"] == "Standard Seller Catalog Pricing"
    assert data["seller_id"] == str(env["seller"].id)
    assert data["currency"] == "USD"
    assert "id" in data
    assert "tenant_id" in data
    assert data["tenant_id"] == str(env["tenant"].id)


def test_feature_price_book_get_by_id(client: TestClient):
    """F-01.2: Verify fetching a specific price book by ID."""
    env = setup_tenant_and_actor()
    res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Book for Lookup",
        "currency": "USD",
        "is_default": False,
    })
    assert res.status_code == 201
    book_id = res.json()["id"]

    get_res = client.get(f"/api/v1/pricing/books/{book_id}", headers=env["headers"])
    assert get_res.status_code == 200
    book_data = get_res.json()
    assert book_data["id"] == book_id
    assert book_data["name"] == "Book for Lookup"


def test_feature_price_book_list_and_filter(client: TestClient):
    """F-01.3: Verify listing price books with seller filter."""
    env = setup_tenant_and_actor()
    # Create Book 1 (seller level)
    client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Seller Level Book",
        "currency": "USD",
    })
    # Create Book 2 (branch level)
    client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "branch_id": str(env["downtown_branch"].id),
        "name": "Branch Level Book",
        "currency": "USD",
    })

    list_res = client.get(f"/api/v1/pricing/books?seller_id={env['seller'].id}", headers=env["headers"])
    assert list_res.status_code == 200
    items = list_res.json()
    assert isinstance(items, list)
    assert len(items) >= 2
    book_names = [b["name"] for b in items]
    assert "Seller Level Book" in book_names
    assert "Branch Level Book" in book_names


def test_feature_price_book_update(client: TestClient):
    """F-01.4: Verify updating price book metadata and description."""
    env = setup_tenant_and_actor()
    create_res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Original Name",
        "description": "Original Description",
        "currency": "USD",
    })
    assert create_res.status_code == 201
    book_id = create_res.json()["id"]

    # Try PATCH then PUT
    update_payload = {"name": "Updated Name", "description": "Updated Description"}
    update_res = client.patch(f"/api/v1/pricing/books/{book_id}", headers=env["headers"], json=update_payload)
    if update_res.status_code == 405 or update_res.status_code == 404:
        update_res = client.put(f"/api/v1/pricing/books/{book_id}", headers=env["headers"], json=update_payload)
    
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["name"] == "Updated Name"
    assert updated["description"] == "Updated Description"


def test_feature_price_book_delete(client: TestClient):
    """F-01.5: Verify soft or hard deletion of a price book."""
    env = setup_tenant_and_actor()
    create_res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "To Be Deleted",
        "currency": "USD",
    })
    assert create_res.status_code == 201
    book_id = create_res.json()["id"]

    del_res = client.delete(f"/api/v1/pricing/books/{book_id}", headers=env["headers"])
    assert del_res.status_code in (200, 204)

    # Subsequent get should return 404
    get_res = client.get(f"/api/v1/pricing/books/{book_id}", headers=env["headers"])
    assert get_res.status_code == 404


# ============================================================================
# FEATURE 2: PriceRule CRUD Lifecycle (>=5 tests)
# ============================================================================

def test_feature_price_rule_create(client: TestClient):
    """F-02.1: Verify creating a price rule attached to a price book."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Rule Test Book",
        "currency": "USD",
    })
    book_id = book_res.json()["id"]

    rule_payload = {
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "14.50",
        "rate_type": "FLAT",
        "priority": 10,
    }
    rule_res = client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json=rule_payload)
    assert rule_res.status_code == 201, f"Failed: {rule_res.text}"
    rule_data = rule_res.json()
    assert "id" in rule_data
    assert rule_data["price_book_id"] == book_id
    assert Decimal(str(rule_data["rate"])) == Decimal("14.50")
    assert rule_data["rule_type"] == "PER_ITEM"


def test_feature_price_rule_list(client: TestClient):
    """F-02.2: Verify listing all rules belonging to a specific price book."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Rule Listing Book",
        "currency": "USD",
    })
    book_id = book_res.json()["id"]

    # Add Rule 1
    client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "15.00",
    })
    # Add Rule 2
    client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["shirt"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "6.50",
    })

    list_res = client.get(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"])
    assert list_res.status_code == 200
    rules = list_res.json()
    assert isinstance(rules, list)
    assert len(rules) >= 2


def test_feature_price_rule_update(client: TestClient):
    """F-02.3: Verify updating an existing price rule rate and priority."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Rule Update Book",
        "currency": "USD",
    })
    book_id = book_res.json()["id"]

    create_rule_res = client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "rule_type": "FIXED",
        "component_type": "BASE_PRICE",
        "rate": "10.00",
        "priority": 1,
    })
    rule_id = create_rule_res.json()["id"]

    # Try updating rule via PUT /rules/{id} or PATCH /books/{id}/rules/{id}
    update_payload = {"rate": "12.75", "priority": 5}
    upd_res = client.put(f"/api/v1/pricing/rules/{rule_id}", headers=env["headers"], json=update_payload)
    if upd_res.status_code in (404, 405):
        upd_res = client.patch(f"/api/v1/pricing/books/{book_id}/rules/{rule_id}", headers=env["headers"], json=update_payload)

    assert upd_res.status_code == 200
    updated_rule = upd_res.json()
    assert Decimal(str(updated_rule["rate"])) == Decimal("12.75")
    assert updated_rule["priority"] == 5


def test_feature_price_rule_delete(client: TestClient):
    """F-02.4: Verify deleting a price rule removes it from the book."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Rule Deletion Book",
        "currency": "USD",
    })
    book_id = book_res.json()["id"]

    rule_res = client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "rule_type": "FIXED",
        "component_type": "BASE_PRICE",
        "rate": "20.00",
    })
    rule_id = rule_res.json()["id"]

    del_res = client.delete(f"/api/v1/pricing/rules/{rule_id}", headers=env["headers"])
    if del_res.status_code in (404, 405):
        del_res = client.delete(f"/api/v1/pricing/books/{book_id}/rules/{rule_id}", headers=env["headers"])
    assert del_res.status_code in (200, 204)

    # Listing rules on book should now be empty
    list_res = client.get(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"])
    assert list_res.status_code == 200
    rules = list_res.json()
    assert not any(r["id"] == rule_id for r in rules)


def test_feature_price_rule_addon_attachment(client: TestClient):
    """F-02.5: Verify creating a rule targeting a specific catalog add-on."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Addon Rule Book",
        "currency": "USD",
    })
    book_id = book_res.json()["id"]

    addon_rule_res = client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_addon_id": str(env["addons"]["delicate"].id),
        "rule_type": "PER_ITEM",
        "component_type": "SURCHARGE",
        "rate": "3.50",
        "rate_type": "FLAT",
    })
    assert addon_rule_res.status_code == 201
    rule_data = addon_rule_res.json()
    assert rule_data["service_addon_id"] == str(env["addons"]["delicate"].id)
    assert Decimal(str(rule_data["rate"])) == Decimal("3.50")


# ============================================================================
# FEATURE 3: Calculation by Rule Type (>=5 tests)
# ============================================================================

def test_feature_calc_fixed_rule(client: TestClient):
    """F-03.1: Verify calculation for FIXED rule type applies a constant base rate."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Fixed Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "FIXED",
        "component_type": "BASE_PRICE",
        "rate": "25.00",
    })
    _activate_book(client, book_id, env["headers"])

    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "currency": "USD",
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["suit"].id),
                "quantity": 1,
            }
        ],
    })
    assert calc_res.status_code == 200, f"Error: {calc_res.text}"
    data = calc_res.json()
    assert Decimal(str(data["subtotal"])) == Decimal("25.00")
    assert Decimal(str(data["grand_total"])) == Decimal("25.00")
    assert_calculation_invariant(data)


def test_feature_calc_per_item_rule(client: TestClient):
    """F-03.2: Verify calculation for PER_ITEM multiplies rate by integer quantity."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Per Item Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["shirt"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "7.50",
    })
    _activate_book(client, book_id, env["headers"])

    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["shirt"].id),
                "quantity": 4,  # 4 shirts * 7.50 = 30.00
            }
        ],
    })
    assert calc_res.status_code == 200
    data = calc_res.json()
    assert Decimal(str(data["subtotal"])) == Decimal("30.00")
    assert Decimal(str(data["grand_total"])) == Decimal("30.00")
    assert_calculation_invariant(data)


def test_feature_calc_per_unit_rule(client: TestClient):
    """F-03.3: Verify calculation for PER_UNIT multiplies rate by measurable unit."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Per Unit Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["upholstery"].id),
        "service_item_id": str(env["items"]["curtain"].id),
        "rule_type": "PER_UNIT",
        "component_type": "BASE_PRICE",
        "rate": "12.00",
    })
    _activate_book(client, book_id, env["headers"])

    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["upholstery"].id),
                "service_item_id": str(env["items"]["curtain"].id),
                "quantity": 1,
                "units": 4.5,  # 4.5 sq meters * 12.00 = 54.00
            }
        ],
    })
    assert calc_res.status_code == 200
    data = calc_res.json()
    assert Decimal(str(data["subtotal"])) == Decimal("54.00")
    assert Decimal(str(data["grand_total"])) == Decimal("54.00")
    assert_calculation_invariant(data)


def test_feature_calc_per_weight_rule(client: TestClient):
    """F-03.4: Verify calculation for PER_WEIGHT multiplies rate by kilograms."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Per Weight Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["wash_fold"].id),
        "service_item_id": str(env["items"]["laundry_bag"].id),
        "rule_type": "PER_WEIGHT",
        "component_type": "BASE_PRICE",
        "rate": "2.75",
    })
    _activate_book(client, book_id, env["headers"])

    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["wash_fold"].id),
                "service_item_id": str(env["items"]["laundry_bag"].id),
                "quantity": 1,
                "units": 8.0,  # 8.0 kg * 2.75 = 22.00
            }
        ],
    })
    assert calc_res.status_code == 200
    data = calc_res.json()
    assert Decimal(str(data["subtotal"])) == Decimal("22.00")
    assert Decimal(str(data["grand_total"])) == Decimal("22.00")
    assert_calculation_invariant(data)


def test_feature_calc_mixed_rule_types_in_single_request(client: TestClient):
    """F-03.5: Verify calculation with mixed rule types (PER_ITEM and PER_WEIGHT) simultaneously."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Mixed Rule Types Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    # Rule 1: Shirt dry cleaning (PER_ITEM @ $6.00)
    client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["shirt"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "6.00",
    })
    # Rule 2: Wash & fold (PER_WEIGHT @ $3.00/kg)
    client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["wash_fold"].id),
        "service_item_id": str(env["items"]["laundry_bag"].id),
        "rule_type": "PER_WEIGHT",
        "component_type": "BASE_PRICE",
        "rate": "3.00",
    })
    _activate_book(client, book_id, env["headers"])

    # 3 shirts ($18.00) + 5 kg laundry ($15.00) = $33.00 subtotal
    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["shirt"].id),
                "quantity": 3,
            },
            {
                "service_id": str(env["services"]["wash_fold"].id),
                "service_item_id": str(env["items"]["laundry_bag"].id),
                "quantity": 1,
                "units": 5.0,
            },
        ],
    })
    assert calc_res.status_code == 200
    data = calc_res.json()
    assert Decimal(str(data["subtotal"])) == Decimal("33.00")
    assert Decimal(str(data["grand_total"])) == Decimal("33.00")
    assert len(data["line_items"]) == 2
    assert_calculation_invariant(data)


# ============================================================================
# FEATURE 4: 4-Tier Financial Breakdown (>=5 tests)
# ============================================================================

def test_feature_breakdown_base_price_and_addons(client: TestClient):
    """F-04.1: Verify breakdown captures base item price and addon amounts in subtotal."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Base and Addons Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    # Suit base: $20.00
    client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "20.00",
    })
    # Stain removal addon: $5.00
    client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_addon_id": str(env["addons"]["stain"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "5.00",
    })
    _activate_book(client, book_id, env["headers"])

    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["suit"].id),
                "quantity": 2,  # 2 suits * 20 = 40.00
                "addons": [
                    {
                        "service_addon_id": str(env["addons"]["stain"].id),
                        "quantity": 2,  # 2 stain removals * 5 = 10.00
                    }
                ],
            }
        ],
    })
    assert calc_res.status_code == 200
    data = calc_res.json()
    assert Decimal(str(data["subtotal"])) == Decimal("50.00")
    assert Decimal(str(data["grand_total"])) == Decimal("50.00")
    line = data["line_items"][0]
    assert Decimal(str(line["base_amount"])) == Decimal("40.00")
    assert Decimal(str(line["addons_amount"])) == Decimal("10.00")
    assert_calculation_invariant(data)


def test_feature_breakdown_surcharges(client: TestClient):
    """F-04.2: Verify surcharge component adds to total_surcharges."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Surcharge Breakdown Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    # Base price: $30.00
    client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "30.00",
    })
    # Rush Surcharge: $7.50
    client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "rule_type": "FIXED",
        "component_type": "SURCHARGE",
        "rate": "7.50",
    })
    _activate_book(client, book_id, env["headers"])

    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["suit"].id),
                "quantity": 1,
            }
        ],
    })
    assert calc_res.status_code == 200
    data = calc_res.json()
    assert Decimal(str(data["subtotal"])) == Decimal("30.00")
    assert Decimal(str(data["total_surcharges"])) == Decimal("7.50")
    assert Decimal(str(data["grand_total"])) == Decimal("37.50")
    assert_calculation_invariant(data)


def test_feature_breakdown_discounts(client: TestClient):
    """F-04.3: Verify discount component reduces subtotal in total_discounts."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Discount Breakdown Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "40.00",
    })
    client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "rule_type": "FIXED",
        "component_type": "DISCOUNT",
        "rate": "5.00",
    })
    _activate_book(client, book_id, env["headers"])

    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["suit"].id),
                "quantity": 1,
            }
        ],
    })
    assert calc_res.status_code == 200
    data = calc_res.json()
    assert Decimal(str(data["subtotal"])) == Decimal("40.00")
    assert Decimal(str(data["total_discounts"])) == Decimal("5.00")
    assert Decimal(str(data["grand_total"])) == Decimal("35.00")
    assert_calculation_invariant(data)


def test_feature_breakdown_tax(client: TestClient):
    """F-04.4: Verify tax component computation on taxable subtotal."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Tax Breakdown Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "100.00",
    })
    client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "rule_type": "FIXED",
        "component_type": "TAX",
        "rate": "8.25",
        "rate_type": "PERCENTAGE",
    })
    _activate_book(client, book_id, env["headers"])

    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["suit"].id),
                "quantity": 1,
            }
        ],
    })
    assert calc_res.status_code == 200
    data = calc_res.json()
    assert Decimal(str(data["subtotal"])) == Decimal("100.00")
    assert Decimal(str(data["total_tax"])) == Decimal("8.25")
    assert Decimal(str(data["grand_total"])) == Decimal("108.25")
    assert_calculation_invariant(data)


def test_feature_breakdown_all_four_tiers_with_invariant(client: TestClient):
    """F-04.5: Verify full 4-tier combination (Base + Surcharge - Discount + Tax) satisfies invariant."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Complete 4-Tier Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    # Base: $100.00
    client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "100.00",
    })
    # Surcharge: $10.00
    client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "rule_type": "FIXED",
        "component_type": "SURCHARGE",
        "rate": "10.00",
    })
    # Discount: $20.00
    client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "rule_type": "FIXED",
        "component_type": "DISCOUNT",
        "rate": "20.00",
    })
    # Tax: 10% on taxable (100 + 10 - 20 = 90.00 -> 9.00 tax)
    client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "rule_type": "FIXED",
        "component_type": "TAX",
        "rate": "10.00",
        "rate_type": "PERCENTAGE",
    })
    _activate_book(client, book_id, env["headers"])

    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["suit"].id),
                "quantity": 1,
            }
        ],
    })
    assert calc_res.status_code == 200
    data = calc_res.json()
    assert Decimal(str(data["subtotal"])) == Decimal("100.00")
    assert Decimal(str(data["total_surcharges"])) == Decimal("10.00")
    assert Decimal(str(data["total_discounts"])) == Decimal("20.00")
    assert Decimal(str(data["taxable_amount"])) == Decimal("90.00")
    assert Decimal(str(data["total_tax"])) == Decimal("9.00")
    assert Decimal(str(data["grand_total"])) == Decimal("99.00")
    assert_calculation_invariant(data)


# ============================================================================
# FEATURE 5: RBAC Permissions & Security (>=5 tests)
# ============================================================================

def test_feature_rbac_pricing_manage_allows_mutation(client: TestClient):
    """F-05.1: Verify user with pricing.manage permission can create books and rules."""
    env = setup_tenant_and_actor(role="TENANT_ADMIN")
    res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Admin Managed Book",
        "currency": "USD",
    })
    assert res.status_code == 201


def test_feature_rbac_pricing_read_allows_listing_and_calculation(client: TestClient):
    """F-05.2: Verify user with pricing.read (e.g. VIEWER) can list books and calculate."""
    env = setup_tenant_and_actor()
    viewer_user = create_test_user("viewer_only@ttclaundry.com")
    create_test_membership(env["tenant"].id, viewer_user.id, "VIEWER")
    viewer_headers = make_auth_headers(viewer_user, env["tenant"])

    list_res = client.get("/api/v1/pricing/books", headers=viewer_headers)
    assert list_res.status_code == 200

    calc_res = client.post("/api/v1/pricing/calculate", headers=viewer_headers, json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["suit"].id),
                "quantity": 1,
            }
        ],
    })
    # Calculation permitted (even if empty book returns 0 or 200)
    assert calc_res.status_code in (200, 422)


def test_feature_rbac_viewer_denied_mutation(client: TestClient):
    """F-05.3: Verify user with VIEWER role cannot create a price book (403 Forbidden)."""
    env = setup_tenant_and_actor()
    viewer_user = create_test_user("viewer_denied@ttclaundry.com")
    create_test_membership(env["tenant"].id, viewer_user.id, "VIEWER")
    viewer_headers = make_auth_headers(viewer_user, env["tenant"])

    res = client.post("/api/v1/pricing/books", headers=viewer_headers, json={
        "seller_id": str(env["seller"].id),
        "name": "Illegal Book",
        "currency": "USD",
    })
    assert res.status_code == 403


def test_feature_rbac_tenant_member_denied_all(client: TestClient):
    """F-05.4: Verify user with TENANT_MEMBER role has neither read nor manage (403 Forbidden)."""
    env = setup_tenant_and_actor()
    member_user = create_test_user("member_no_perms@ttclaundry.com")
    create_test_membership(env["tenant"].id, member_user.id, "TENANT_MEMBER")
    member_headers = make_auth_headers(member_user, env["tenant"])

    # Read denied
    res_get = client.get("/api/v1/pricing/books", headers=member_headers)
    assert res_get.status_code == 403

    # Create denied
    res_post = client.post("/api/v1/pricing/books", headers=member_headers, json={
        "seller_id": str(env["seller"].id),
        "name": "Member Blocked Book",
        "currency": "USD",
    })
    assert res_post.status_code == 403


def test_feature_rbac_unauthenticated_request_rejected(client: TestClient):
    """F-05.5: Verify unauthenticated requests lacking headers are rejected."""
    res_get = client.get("/api/v1/pricing/books")
    assert res_get.status_code in (401, 403)

    res_post = client.post("/api/v1/pricing/books", json={"name": "No Auth Book"})
    assert res_post.status_code in (401, 403)


# ============================================================================
# FEATURE 6: AuditService Event Verification (>=5 tests)
# ============================================================================

def test_feature_audit_book_created_logged(client: TestClient):
    """F-06.1: Verify AuditService logs PRICING_BOOK_CREATED on book creation."""
    env = setup_tenant_and_actor()
    res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Audited Creation Book",
        "currency": "USD",
    })
    assert res.status_code == 201
    book_id = res.json()["id"]

    with SessionLocal() as db:
        events = db.query(AuditEvent).filter(
            AuditEvent.tenant_id == env["tenant"].id,
            AuditEvent.event_type.in_(["PRICING_BOOK_CREATED", "PRICE_BOOK_CREATED"]),
        ).all()
        assert len(events) >= 1
        payloads = [e.payload for e in events]
        assert any(str(p.get("book_id", "")) == book_id or str(p.get("id", "")) == book_id for p in payloads)


def test_feature_audit_book_updated_logged(client: TestClient):
    """F-06.2: Verify AuditService logs PRICING_BOOK_UPDATED on book modification."""
    env = setup_tenant_and_actor()
    res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Audit Update Book",
        "currency": "USD",
    })
    book_id = res.json()["id"]

    update_payload = {"name": "Audit Update Book Renamed"}
    upd_res = client.patch(f"/api/v1/pricing/books/{book_id}", headers=env["headers"], json=update_payload)
    if upd_res.status_code in (404, 405):
        client.put(f"/api/v1/pricing/books/{book_id}", headers=env["headers"], json=update_payload)

    with SessionLocal() as db:
        events = db.query(AuditEvent).filter(
            AuditEvent.tenant_id == env["tenant"].id,
            AuditEvent.event_type.in_(["PRICING_BOOK_UPDATED", "PRICE_BOOK_UPDATED"]),
        ).all()
        assert len(events) >= 1


def test_feature_audit_rule_created_logged(client: TestClient):
    """F-06.3: Verify AuditService logs PRICING_RULE_CREATED on rule creation."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Audit Rule Book",
        "currency": "USD",
    })
    book_id = book_res.json()["id"]

    rule_res = client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "rule_type": "FIXED",
        "component_type": "BASE_PRICE",
        "rate": "12.00",
    })
    assert rule_res.status_code == 201
    rule_id = rule_res.json()["id"]

    with SessionLocal() as db:
        events = db.query(AuditEvent).filter(
            AuditEvent.tenant_id == env["tenant"].id,
            AuditEvent.event_type.in_(["PRICING_RULE_CREATED", "PRICE_RULE_CREATED"]),
        ).all()
        assert len(events) >= 1
        payloads = [e.payload for e in events]
        assert any(str(p.get("rule_id", "")) == rule_id or str(p.get("id", "")) == rule_id for p in payloads)


def test_feature_audit_rule_updated_logged(client: TestClient):
    """F-06.4: Verify AuditService logs PRICING_RULE_UPDATED on rule update."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Audit Rule Upd Book",
        "currency": "USD",
    })
    book_id = book_res.json()["id"]

    rule_res = client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "rule_type": "FIXED",
        "component_type": "BASE_PRICE",
        "rate": "12.00",
    })
    rule_id = rule_res.json()["id"]

    upd_res = client.put(f"/api/v1/pricing/rules/{rule_id}", headers=env["headers"], json={"rate": "14.00"})
    if upd_res.status_code in (404, 405):
        client.patch(f"/api/v1/pricing/books/{book_id}/rules/{rule_id}", headers=env["headers"], json={"rate": "14.00"})

    with SessionLocal() as db:
        events = db.query(AuditEvent).filter(
            AuditEvent.tenant_id == env["tenant"].id,
            AuditEvent.event_type.in_(["PRICING_RULE_UPDATED", "PRICE_RULE_UPDATED"]),
        ).all()
        assert len(events) >= 1


def test_feature_audit_rule_deleted_logged(client: TestClient):
    """F-06.5: Verify AuditService logs PRICING_RULE_DELETED on rule deletion."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Audit Rule Del Book",
        "currency": "USD",
    })
    book_id = book_res.json()["id"]

    rule_res = client.post(f"/api/v1/pricing/books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "rule_type": "FIXED",
        "component_type": "BASE_PRICE",
        "rate": "15.00",
    })
    rule_id = rule_res.json()["id"]

    del_res = client.delete(f"/api/v1/pricing/rules/{rule_id}", headers=env["headers"])
    if del_res.status_code in (404, 405):
        client.delete(f"/api/v1/pricing/books/{book_id}/rules/{rule_id}", headers=env["headers"])

    with SessionLocal() as db:
        events = db.query(AuditEvent).filter(
            AuditEvent.tenant_id == env["tenant"].id,
            AuditEvent.event_type.in_(["PRICING_RULE_DELETED", "PRICE_RULE_DELETED"]),
        ).all()
        assert len(events) >= 1
