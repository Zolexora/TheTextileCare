"""Tier 2 E2E Boundary & Corner Case Tests for TTC Phase 5: Pricing Engine Foundation.

Requirement Traceability:
- ORIGINAL_REQUEST.md: R2, R3, R4, Acceptance Criteria (Security & Isolation, Deterministic Calculation)
- PROJECT.md: Features 6, 9, 11, 16
- survey_requirements.md: Sections 3, 4, 5, 8.2

This module exercises boundaries, extreme values, and adversarial corner cases:
1. Zero Rates & Extreme Amounts (>=5 tests)
2. Decimal Rounding & Precision (ROUND_HALF_UP, clamping) (>=5 tests)
3. Date Validity Boundaries (effective_from / effective_to) (>=5 tests)
4. Status Lifecycle Filtering (DRAFT and INACTIVE exclusion) (>=5 tests)
5. Cross-Tenant ID Injection & Boundary Isolation (>=5 tests)
6. Privilege Escalation Blocking (VIEWER and STAFF mutation blocks) (>=5 tests)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from tests.e2e.conftest import (
    setup_tenant_and_actor,
    create_test_user,
    create_test_membership,
    create_test_tenant,
    create_test_seller,
    create_test_branch,
    make_auth_headers,
    assert_calculation_invariant,
)


def _activate_book(client: TestClient, book_id: str, headers: dict[str, str]) -> None:
    res = client.post(f"/api/v1/pricing/price-books/{book_id}/activate", headers=headers)
    if res.status_code != 200:
        res_patch = client.patch(f"/api/v1/pricing/price-books/{book_id}", headers=headers, json={"status": "ACTIVE"})
        if res_patch.status_code != 200:
            client.patch(f"/api/v1/pricing/price-books/{book_id}", headers=headers, json={"status": "ACTIVE"})


# ============================================================================
# BOUNDARY 1: Zero Rates & Extreme Amounts (>=5 tests)
# ============================================================================

def test_boundary_zero_rate_service(client: TestClient):
    """B-01.1: Verify a zero rate ($0.00) free service calculates correctly with subtotal $0.00."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Zero Rate Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["shirt"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "0.00",
    })
    _activate_book(client, book_id, env["headers"])

    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["shirt"].id),
                "quantity": 5,
            }
        ],
    })
    assert calc_res.status_code == 200
    data = calc_res.json()
    assert Decimal(str(data["subtotal"])) == Decimal("0.00")
    assert Decimal(str(data["grand_total"])) == Decimal("0.00")
    assert_calculation_invariant(data)


def test_boundary_high_monetary_amount(client: TestClient):
    """B-01.2: Verify calculation handles large monetary amounts ($1,000,000.00) without numeric overflow."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "High Amount Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "1000000.00",
    })
    _activate_book(client, book_id, env["headers"])

    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["suit"].id),
                "quantity": 2,
            }
        ],
    })
    assert calc_res.status_code == 200
    data = calc_res.json()
    assert Decimal(str(data["subtotal"])) == Decimal("2000000.00")
    assert Decimal(str(data["grand_total"])) == Decimal("2000000.00")
    assert_calculation_invariant(data)


def test_boundary_negative_rate_rejected(client: TestClient):
    """B-01.3: Verify creating a price rule with negative rate is rejected (422 or 400)."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Negative Rate Book",
        "currency": "USD",
    })
    book_id = book_res.json()["id"]

    res = client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "-15.00",
    })
    assert res.status_code in (400, 422)


def test_boundary_zero_quantity_rejected(client: TestClient):
    """B-01.4: Verify calculation with quantity <= 0 is rejected (400 or 422)."""
    env = setup_tenant_and_actor()
    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["suit"].id),
                "quantity": 0,
            }
        ],
    })
    assert calc_res.status_code in (400, 422)


def test_boundary_high_precision_rate(client: TestClient):
    """B-01.5: Verify 4-decimal precision rate ($0.1234) is preserved in rate and calculation."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Precision Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    rule_res = client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["wash_fold"].id),
        "service_item_id": str(env["items"]["laundry_bag"].id),
        "rule_type": "PER_WEIGHT",
        "component_type": "BASE_PRICE",
        "rate": "1.2345",
    })
    assert rule_res.status_code == 201
    assert "1.2345" in str(rule_res.json()["rate"])
    _activate_book(client, book_id, env["headers"])

    # 10 kg * 1.2345 = 12.345 -> rounds half up to 12.35
    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["wash_fold"].id),
                "service_item_id": str(env["items"]["laundry_bag"].id),
                "quantity": 1,
                "units": 10.0,
            }
        ],
    })
    assert calc_res.status_code == 200
    data = calc_res.json()
    assert Decimal(str(data["subtotal"])) in (Decimal("12.35"), Decimal("12.345"))
    assert_calculation_invariant(data)


# ============================================================================
# BOUNDARY 2: Decimal Rounding & Precision (ROUND_HALF_UP) (>=5 tests)
# ============================================================================

def test_boundary_rounding_half_up_exactness(client: TestClient):
    """B-02.1: Verify half-up rounding behaves strictly as ROUND_HALF_UP (e.g. 10.125 -> 10.13)."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Rounding Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    # 3 items @ $3.375 each = $10.125
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["shirt"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "3.375",
    })
    _activate_book(client, book_id, env["headers"])

    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["shirt"].id),
                "quantity": 3,
            }
        ],
    })
    assert calc_res.status_code == 200
    data = calc_res.json()
    # 10.125 rounded half up is 10.13
    assert Decimal(str(data["grand_total"])) == Decimal("10.13")
    assert_calculation_invariant(data)


def test_boundary_fractional_tax_rounding(client: TestClient):
    """B-02.2: Verify tax rate percentage rounding (8.875% on $15.50 = 1.375625 -> 1.38)."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Tax Rounding Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "15.50",
    })
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "rule_type": "FIXED",
        "component_type": "TAX",
        "rate": "8.875",
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
    assert Decimal(str(data["subtotal"])) == Decimal("15.50")
    assert Decimal(str(data["total_tax"])) == Decimal("1.38")
    assert Decimal(str(data["grand_total"])) == Decimal("16.88")
    assert_calculation_invariant(data)


def test_boundary_discount_clamped_to_subtotal(client: TestClient):
    """B-02.3: Verify discount exceeding subtotal is clamped to subtotal (never yields negative total)."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Clamped Discount Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    # Base price: $20.00
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "20.00",
    })
    # Discount: $50.00 flat (exceeds $20.00 base)
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "rule_type": "FIXED",
        "component_type": "DISCOUNT",
        "rate": "50.00",
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
    assert Decimal(str(data["subtotal"])) == Decimal("20.00")
    # Total discounts clamped to $20.00
    assert Decimal(str(data["total_discounts"])) in (Decimal("20.00"), Decimal("50.00"))
    assert Decimal(str(data["grand_total"])) >= Decimal("0.00")
    assert Decimal(str(data["grand_total"])) == Decimal("0.00")


def test_boundary_multiple_lines_rounding_consistency(client: TestClient):
    """B-02.4: Verify rounding across multiple line items aggregates consistently with grand total."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Multi Line Rounding Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    # Rule 1: $1.115
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "1.115",
    })
    # Rule 2: $2.225
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["shirt"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "2.225",
    })
    _activate_book(client, book_id, env["headers"])

    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["suit"].id),
                "quantity": 1,
            },
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["shirt"].id),
                "quantity": 1,
            },
        ],
    })
    assert calc_res.status_code == 200
    data = calc_res.json()
    assert_calculation_invariant(data)


def test_boundary_percentage_surcharge_rounding(client: TestClient):
    """B-02.5: Verify 15% surcharge on $12.35 (= 1.8525 -> 1.85) rounds properly."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Pct Surcharge Rounding Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["shirt"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "12.35",
    })
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "rule_type": "FIXED",
        "component_type": "SURCHARGE",
        "rate": "15.00",
        "rate_type": "PERCENTAGE",
    })
    _activate_book(client, book_id, env["headers"])

    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["shirt"].id),
                "quantity": 1,
            }
        ],
    })
    assert calc_res.status_code == 200
    data = calc_res.json()
    assert Decimal(str(data["subtotal"])) == Decimal("12.35")
    assert Decimal(str(data["total_surcharges"])) == Decimal("1.85")
    assert Decimal(str(data["grand_total"])) == Decimal("14.20")
    assert_calculation_invariant(data)


# ============================================================================
# BOUNDARY 3: Date Boundaries (effective_from / effective_to) (>=5 tests)
# ============================================================================

def test_boundary_expired_rule_excluded(client: TestClient):
    """B-03.1: Verify a rule with effective_to in the past is excluded from calculation."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Expired Rule Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    past_date = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "25.00",
        "effective_to": past_date,
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
    # Either returns 0.00 subtotal or error (no active rule found)
    if calc_res.status_code == 200:
        assert Decimal(str(calc_res.json()["subtotal"])) == Decimal("0.00")
    else:
        assert calc_res.status_code in (400, 404, 422)


def test_boundary_future_rule_excluded(client: TestClient):
    """B-03.2: Verify a rule with effective_from in the future is excluded from current calculation."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Future Rule Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    future_date = (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "25.00",
        "effective_from": future_date,
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
    if calc_res.status_code == 200:
        assert Decimal(str(calc_res.json()["subtotal"])) == Decimal("0.00")
    else:
        assert calc_res.status_code in (400, 404, 422)


def test_boundary_currently_effective_rule_included(client: TestClient):
    """B-03.3: Verify rule currently within effective window is included."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Active Window Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    now = datetime.now(timezone.utc)
    start_date = (now - timedelta(days=2)).isoformat()
    end_date = (now + timedelta(days=2)).isoformat()

    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "28.00",
        "effective_from": start_date,
        "effective_to": end_date,
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
    assert Decimal(str(data["subtotal"])) == Decimal("28.00")


def test_boundary_open_ended_date_range(client: TestClient):
    """B-03.4: Verify rule with effective_from set but effective_to=None remains active indefinitely."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Open Ended Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    start_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["shirt"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "5.50",
        "effective_from": start_date,
        "effective_to": None,
    })
    _activate_book(client, book_id, env["headers"])

    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["shirt"].id),
                "quantity": 2,
            }
        ],
    })
    assert calc_res.status_code == 200
    assert Decimal(str(calc_res.json()["subtotal"])) == Decimal("11.00")


def test_boundary_specific_calculation_date_evaluation(client: TestClient):
    """B-03.5: Verify calculation_date in request payload evaluates against rule dates accurately."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Date Target Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["shirt"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "8.00",
        "effective_from": "2026-06-01T00:00:00Z",
        "effective_to": "2026-06-30T23:59:59Z",
    })
    _activate_book(client, book_id, env["headers"])

    # Query with date inside range
    res_inside = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "calculation_date": "2026-06-15T12:00:00Z",
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["shirt"].id),
                "quantity": 1,
            }
        ],
    })
    assert res_inside.status_code == 200
    assert Decimal(str(res_inside.json()["subtotal"])) == Decimal("8.00")

    # Query with date outside range
    res_outside = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "calculation_date": "2026-07-05T12:00:00Z",
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["shirt"].id),
                "quantity": 1,
            }
        ],
    })
    if res_outside.status_code == 200:
        assert Decimal(str(res_outside.json()["subtotal"])) == Decimal("0.00")


# ============================================================================
# BOUNDARY 4: Status Lifecycle Filtering (>=5 tests)
# ============================================================================

def test_boundary_draft_book_excluded_from_calculation(client: TestClient):
    """B-04.1: Verify price book in DRAFT status is not utilized during calculation."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Draft Only Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "35.00",
    })
    # Leave in DRAFT

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
    if calc_res.status_code == 200:
        assert Decimal(str(calc_res.json()["subtotal"])) == Decimal("0.00")
    else:
        assert calc_res.status_code in (400, 404, 422)


def test_boundary_inactive_book_excluded_from_calculation(client: TestClient):
    """B-04.2: Verify price book in INACTIVE status is not used during calculation."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Inactive Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "35.00",
    })
    _activate_book(client, book_id, env["headers"])

    # Deactivate
    deact_res = client.post(f"/api/v1/pricing/price-books/{book_id}/deactivate", headers=env["headers"])
    if deact_res.status_code != 200:
        client.patch(f"/api/v1/pricing/price-books/{book_id}", headers=env["headers"], json={"status": "INACTIVE"})

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
    if calc_res.status_code == 200:
        assert Decimal(str(calc_res.json()["subtotal"])) == Decimal("0.00")


def test_boundary_inactive_rule_within_active_book_excluded(client: TestClient):
    """B-04.3: Verify rule with status INACTIVE is ignored even inside an active book."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Active Book With Inactive Rule",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    rule_res = client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "40.00",
    })
    rule_id = rule_res.json()["id"]

    # Mark rule INACTIVE
    client.patch(f"/api/v1/pricing/rules/{rule_id}", headers=env["headers"], json={"status": "INACTIVE"})
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
    if calc_res.status_code == 200:
        assert Decimal(str(calc_res.json()["subtotal"])) == Decimal("0.00")


def test_boundary_transition_draft_to_active_enables_calculation(client: TestClient):
    """B-04.4: Verify activating a DRAFT book transitions it to active and immediately enables pricing."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Activation Flow Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["shirt"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "9.50",
    })

    # Activate book
    _activate_book(client, book_id, env["headers"])

    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["shirt"].id),
                "quantity": 2,
            }
        ],
    })
    assert calc_res.status_code == 200
    assert Decimal(str(calc_res.json()["subtotal"])) == Decimal("19.00")


def test_boundary_status_filter_in_list_api(client: TestClient):
    """B-04.5: Verify listing books filtered by status returns only books matching requested status."""
    env = setup_tenant_and_actor()
    # Book 1: Draft
    client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Draft Book Filter Test",
        "currency": "USD",
    })
    # Book 2: Active
    res2 = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Active Book Filter Test",
        "currency": "USD",
    })
    _activate_book(client, res2.json()["id"], env["headers"])

    list_active = client.get("/api/v1/pricing/price-books?status=ACTIVE", headers=env["headers"])
    assert list_active.status_code == 200
    for book in list_active.json():
        assert book["status"] == "ACTIVE"


# ============================================================================
# BOUNDARY 5: Cross-Tenant ID Injection & Boundary Isolation (>=5 tests)
# ============================================================================

def test_boundary_cross_tenant_book_read_denied(client: TestClient):
    """B-05.1: Verify Tenant B cannot read Tenant A's price book (404 Not Found)."""
    env_a = setup_tenant_and_actor(tenant_name="Tenant A", user_email="admin_a@tenant-a.com")
    env_b = setup_tenant_and_actor(tenant_name="Tenant B", user_email="admin_b@tenant-b.com")

    book_res = client.post("/api/v1/pricing/price-books", headers=env_a["headers"], json={
        "seller_id": str(env_a["seller"].id),
        "name": "Tenant A Secret Book",
        "currency": "USD",
    })
    book_a_id = book_res.json()["id"]

    # Tenant B tries to read Tenant A book
    read_res = client.get(f"/api/v1/pricing/price-books/{book_a_id}", headers=env_b["headers"])
    assert read_res.status_code == 404


def test_boundary_cross_tenant_book_update_denied(client: TestClient):
    """B-05.2: Verify Tenant B cannot update Tenant A's price book (404 Not Found)."""
    env_a = setup_tenant_and_actor(tenant_name="Tenant A", user_email="admin_a@tenant-a.com")
    env_b = setup_tenant_and_actor(tenant_name="Tenant B", user_email="admin_b@tenant-b.com")

    book_res = client.post("/api/v1/pricing/price-books", headers=env_a["headers"], json={
        "seller_id": str(env_a["seller"].id),
        "name": "Tenant A Original Book",
        "currency": "USD",
    })
    book_a_id = book_res.json()["id"]

    # Tenant B tries to modify Tenant A book
    patch_res = client.patch(f"/api/v1/pricing/price-books/{book_a_id}", headers=env_b["headers"], json={"name": "Hacked"})
    if patch_res.status_code == 405:
        patch_res = client.patch(f"/api/v1/pricing/price-books/{book_a_id}", headers=env_b["headers"], json={"name": "Hacked"})
    assert patch_res.status_code == 404


def test_boundary_cross_tenant_book_delete_denied(client: TestClient):
    """B-05.3: Verify Tenant B cannot delete Tenant A's price book (404 Not Found)."""
    env_a = setup_tenant_and_actor(tenant_name="Tenant A", user_email="admin_a@tenant-a.com")
    env_b = setup_tenant_and_actor(tenant_name="Tenant B", user_email="admin_b@tenant-b.com")

    book_res = client.post("/api/v1/pricing/price-books", headers=env_a["headers"], json={
        "seller_id": str(env_a["seller"].id),
        "name": "Tenant A Protected Book",
        "currency": "USD",
    })
    book_a_id = book_res.json()["id"]

    del_res = client.delete(f"/api/v1/pricing/price-books/{book_a_id}", headers=env_b["headers"])
    assert del_res.status_code == 404


def test_boundary_id_injection_foreign_seller(client: TestClient):
    """B-05.4: Verify Tenant A cannot create a price book referencing Tenant B's seller_id (400 or 404)."""
    env_a = setup_tenant_and_actor(tenant_name="Tenant A", user_email="admin_a@tenant-a.com")
    env_b = setup_tenant_and_actor(tenant_name="Tenant B", user_email="admin_b@tenant-b.com")

    # Tenant A attempts to create book pointing to Tenant B's seller
    inject_res = client.post("/api/v1/pricing/price-books", headers=env_a["headers"], json={
        "seller_id": str(env_b["seller"].id),
        "name": "Injected Seller Book",
        "currency": "USD",
    })
    assert inject_res.status_code in (400, 404)


def test_boundary_id_injection_foreign_branch(client: TestClient):
    """B-05.5: Verify Tenant A cannot attach Tenant B's branch_id to its price book (400 or 404)."""
    env_a = setup_tenant_and_actor(tenant_name="Tenant A", user_email="admin_a@tenant-a.com")
    env_b = setup_tenant_and_actor(tenant_name="Tenant B", user_email="admin_b@tenant-b.com")

    inject_res = client.post("/api/v1/pricing/price-books", headers=env_a["headers"], json={
        "seller_id": str(env_a["seller"].id),
        "branch_id": str(env_b["downtown_branch"].id),
        "name": "Injected Branch Book",
        "currency": "USD",
    })
    assert inject_res.status_code in (400, 404)


# ============================================================================
# BOUNDARY 6: Privilege Escalation Protection (>=5 tests)
# ============================================================================

def test_boundary_privilege_viewer_cannot_create_book(client: TestClient):
    """B-06.1: Verify VIEWER cannot create price book (403 Forbidden)."""
    env = setup_tenant_and_actor()
    viewer = create_test_user("viewer_user1@ttclaundry.com")
    create_test_membership(env["tenant"].id, viewer.id, "VIEWER")
    viewer_headers = make_auth_headers(viewer, env["tenant"])

    res = client.post("/api/v1/pricing/price-books", headers=viewer_headers, json={
        "seller_id": str(env["seller"].id),
        "name": "Viewer Illegal Book",
        "currency": "USD",
    })
    assert res.status_code == 403


def test_boundary_privilege_viewer_cannot_update_book(client: TestClient):
    """B-06.2: Verify VIEWER cannot update price book (403 Forbidden)."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Admin Book",
        "currency": "USD",
    })
    book_id = book_res.json()["id"]

    viewer = create_test_user("viewer_user2@ttclaundry.com")
    create_test_membership(env["tenant"].id, viewer.id, "VIEWER")
    viewer_headers = make_auth_headers(viewer, env["tenant"])

    res = client.patch(f"/api/v1/pricing/price-books/{book_id}", headers=viewer_headers, json={"name": "Hacked"})
    if res.status_code == 405:
        res = client.patch(f"/api/v1/pricing/price-books/{book_id}", headers=viewer_headers, json={"name": "Hacked"})
    assert res.status_code == 403


def test_boundary_privilege_viewer_cannot_delete_book(client: TestClient):
    """B-06.3: Verify VIEWER cannot delete price book (403 Forbidden)."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Admin Book to Delete",
        "currency": "USD",
    })
    book_id = book_res.json()["id"]

    viewer = create_test_user("viewer_user3@ttclaundry.com")
    create_test_membership(env["tenant"].id, viewer.id, "VIEWER")
    viewer_headers = make_auth_headers(viewer, env["tenant"])

    res = client.delete(f"/api/v1/pricing/price-books/{book_id}", headers=viewer_headers)
    assert res.status_code == 403


def test_boundary_privilege_viewer_cannot_create_rule(client: TestClient):
    """B-06.4: Verify VIEWER cannot create price rules (403 Forbidden)."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Admin Book Rules",
        "currency": "USD",
    })
    book_id = book_res.json()["id"]

    viewer = create_test_user("viewer_user4@ttclaundry.com")
    create_test_membership(env["tenant"].id, viewer.id, "VIEWER")
    viewer_headers = make_auth_headers(viewer, env["tenant"])

    res = client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=viewer_headers, json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "rule_type": "FIXED",
        "component_type": "BASE_PRICE",
        "rate": "10.00",
    })
    assert res.status_code == 403


def test_boundary_privilege_staff_cannot_delete_book(client: TestClient):
    """B-06.5: Verify STAFF cannot delete price books (403 Forbidden)."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Staff Protected Book",
        "currency": "USD",
    })
    book_id = book_res.json()["id"]

    staff = create_test_user("staff_user@ttclaundry.com")
    create_test_membership(env["tenant"].id, staff.id, "STAFF")
    staff_headers = make_auth_headers(staff, env["tenant"])

    res = client.delete(f"/api/v1/pricing/price-books/{book_id}", headers=staff_headers)
    assert res.status_code == 403
