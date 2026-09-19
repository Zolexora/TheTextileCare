"""Tier 3 E2E Cross-Feature Combinations & Precedence Tests for TTC Phase 5: Pricing Engine Foundation.

Requirement Traceability:
- ORIGINAL_REQUEST.md: R2, R3, Acceptance Criteria (Deterministic Calculation)
- PROJECT.md: Features 7, 8, 10
- survey_requirements.md: Section 4 (Precedence Resolution Hierarchy, Formulas, Invariants)

This module exercises multi-feature combinations:
1. Hierarchical Precedence: Platform Default -> Seller Default -> Branch Override -> Fallbacks
2. Catalog Specificity: Item-specific > Service-level, and Priority tie-breaking
3. Composite Calculations: Base + Multiple Addons + Surcharge + Discount + Tax on single and multi-line orders
"""
from __future__ import annotations

import uuid
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient

from tests.e2e.conftest import (
    setup_tenant_and_actor,
    assert_calculation_invariant,
)


def _activate_book(client: TestClient, book_id: str, headers: dict[str, str]) -> None:
    res = client.post(f"/api/v1/pricing/price-books/{book_id}/activate", headers=headers)
    if res.status_code != 200:
        res_patch = client.patch(f"/api/v1/pricing/price-books/{book_id}", headers=headers, json={"status": "ACTIVE"})
        if res_patch.status_code != 200:
            client.patch(f"/api/v1/pricing/price-books/{book_id}", headers=headers, json={"status": "ACTIVE"})


# ============================================================================
# COMBINATION 1: Hierarchical Precedence Resolution (Platform -> Seller -> Branch)
# ============================================================================

def test_combination_precedence_seller_overrides_platform(client: TestClient):
    """C-01.1: Verify Seller-scoped PriceBook rate overrides Platform Default PriceBook rate."""
    env = setup_tenant_and_actor()

    # 1. Platform Default Book ($15.00)
    plat_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": None,
        "name": "Platform Default Book",
        "currency": "USD",
        "is_default": True,
    })
    plat_id = plat_res.json()["id"]
    client.post(f"/api/v1/pricing/price-books/{plat_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["shirt"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "15.00",
    })
    _activate_book(client, plat_id, env["headers"])

    # 2. Seller Default Book ($10.00)
    seller_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Seller Custom Book",
        "currency": "USD",
        "is_default": True,
    })
    seller_id = seller_res.json()["id"]
    client.post(f"/api/v1/pricing/price-books/{seller_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["shirt"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "10.00",
    })
    _activate_book(client, seller_id, env["headers"])

    # Calculation for seller should return Seller rate ($10.00), not Platform rate ($15.00)
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
    assert Decimal(str(data["subtotal"])) == Decimal("10.00")
    assert_calculation_invariant(data)


def test_combination_precedence_branch_overrides_seller(client: TestClient):
    """C-01.2: Verify Branch-scoped PriceBook rate overrides Seller Default PriceBook rate."""
    env = setup_tenant_and_actor()

    # 1. Seller Book ($12.00)
    seller_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Seller Standard Book",
        "currency": "USD",
        "is_default": True,
    })
    seller_book_id = seller_res.json()["id"]
    client.post(f"/api/v1/pricing/price-books/{seller_book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "12.00",
    })
    _activate_book(client, seller_book_id, env["headers"])

    # 2. Downtown Branch Book ($16.00)
    branch_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "branch_id": str(env["downtown_branch"].id),
        "name": "Downtown Premium Branch Book",
        "currency": "USD",
        "is_default": False,
    })
    branch_book_id = branch_res.json()["id"]
    client.post(f"/api/v1/pricing/price-books/{branch_book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "16.00",
    })
    _activate_book(client, branch_book_id, env["headers"])

    # Query with branch_id -> returns $16.00
    calc_branch = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "branch_id": str(env["downtown_branch"].id),
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["suit"].id),
                "quantity": 1,
            }
        ],
    })
    assert calc_branch.status_code == 200
    assert Decimal(str(calc_branch.json()["subtotal"])) == Decimal("16.00")

    # Query without branch_id -> falls back to Seller rate ($12.00)
    calc_seller = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["suit"].id),
                "quantity": 1,
            }
        ],
    })
    assert calc_seller.status_code == 200
    assert Decimal(str(calc_seller.json()["subtotal"])) == Decimal("12.00")


def test_combination_precedence_branch_fallback_to_seller(client: TestClient):
    """C-01.3: Verify branch calculation falls back to Seller book when item rule is absent in Branch book."""
    env = setup_tenant_and_actor()

    # Seller book has Suit ($25.00) and Shirt ($8.00)
    seller_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Full Seller Catalog Book",
        "currency": "USD",
        "is_default": True,
    })
    seller_book_id = seller_res.json()["id"]
    client.post(f"/api/v1/pricing/price-books/{seller_book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "25.00",
    })
    client.post(f"/api/v1/pricing/price-books/{seller_book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["shirt"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "8.00",
    })
    _activate_book(client, seller_book_id, env["headers"])

    # Branch book ONLY overrides Suit ($30.00), has NO rule for Shirt
    branch_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "branch_id": str(env["downtown_branch"].id),
        "name": "Branch Suit Override Only",
        "currency": "USD",
    })
    branch_book_id = branch_res.json()["id"]
    client.post(f"/api/v1/pricing/price-books/{branch_book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "30.00",
    })
    _activate_book(client, branch_book_id, env["headers"])

    # Calculation requesting BOTH suit and shirt at downtown branch:
    # Suit should be $30.00 (from Branch book), Shirt should fall back to $8.00 (from Seller book)
    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "branch_id": str(env["downtown_branch"].id),
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
    assert Decimal(str(data["subtotal"])) == Decimal("38.00")  # 30.00 + 8.00
    assert_calculation_invariant(data)


# ============================================================================
# COMBINATION 2: Catalog Specificity & Priority Tie-Breaking
# ============================================================================

def test_combination_specificity_item_overrides_service_level(client: TestClient):
    """C-02.1: Verify item-specific rule ($18.00) overrides generic service-level rule ($12.00)."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Specificity Test Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    # Generic Service Rule: Dry Cleaning service @ $12.00
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": None,
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "12.00",
        "priority": 0,
    })

    # Item-Specific Rule: Silk Shirt item @ $18.00
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["shirt"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "18.00",
        "priority": 0,
    })
    _activate_book(client, book_id, env["headers"])

    # Item shirt should get $18.00 (item rule wins over service rule)
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
    assert Decimal(str(data["subtotal"])) == Decimal("18.00")

    # Another item without specific rule (e.g. suit) should get generic service rule $12.00
    calc_generic = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["suit"].id),
                "quantity": 1,
            }
        ],
    })
    assert calc_generic.status_code == 200
    assert Decimal(str(calc_generic.json()["subtotal"])) == Decimal("12.00")


def test_combination_priority_tie_breaking(client: TestClient):
    """C-02.2: Verify higher priority rule (priority=20 @ $22.00) wins over lower priority (priority=10 @ $20.00)."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Priority Tie Break Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    # Rule 1: Priority 10 -> $20.00
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "20.00",
        "priority": 10,
    })

    # Rule 2: Priority 20 -> $22.00
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "22.00",
        "priority": 20,
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
    assert Decimal(str(data["subtotal"])) == Decimal("22.00")
    assert_calculation_invariant(data)


# ============================================================================
# COMBINATION 3: Composite Calculations (Multi-Addons + Surcharge + Discount + Tax)
# ============================================================================

def test_combination_composite_single_line_full_breakdown(client: TestClient):
    """C-03.1: Verify single line order with multiple addons, weight surcharge, discount and tax."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Composite Single Line Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    # Base item: 2-piece suit @ $30.00
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "30.00",
    })
    # Addon 1: Delicate Treatment @ $5.00
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_addon_id": str(env["addons"]["delicate"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "5.00",
    })
    # Addon 2: Stain Removal @ $7.50
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_addon_id": str(env["addons"]["stain"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "7.50",
    })
    # Surcharge: Rush fee $10.00
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "rule_type": "FIXED",
        "component_type": "SURCHARGE",
        "rate": "10.00",
    })
    # Discount: VIP coupon $5.00
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "rule_type": "FIXED",
        "component_type": "DISCOUNT",
        "rate": "5.00",
    })
    # Tax: 8% on taxable
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "rule_type": "FIXED",
        "component_type": "TAX",
        "rate": "8.00",
        "rate_type": "PERCENTAGE",
    })
    _activate_book(client, book_id, env["headers"])

    # 1 suit ($30) + 1 delicate ($5) + 1 stain ($7.50) = Subtotal $42.50
    # Surcharge: $10.00
    # Discount: $5.00
    # Taxable Amount: 42.50 + 10.00 - 5.00 = 47.50
    # Tax: 8% of 47.50 = 3.80
    # Grand Total: 47.50 + 3.80 = 51.30
    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["suit"].id),
                "quantity": 1,
                "addons": [
                    {"service_addon_id": str(env["addons"]["delicate"].id), "quantity": 1},
                    {"service_addon_id": str(env["addons"]["stain"].id), "quantity": 1},
                ],
            }
        ],
    })
    assert calc_res.status_code == 200
    data = calc_res.json()
    assert Decimal(str(data["subtotal"])) == Decimal("42.50")
    assert Decimal(str(data["total_surcharges"])) == Decimal("10.00")
    assert Decimal(str(data["total_discounts"])) == Decimal("5.00")
    assert Decimal(str(data["taxable_amount"])) == Decimal("47.50")
    assert Decimal(str(data["total_tax"])) == Decimal("3.80")
    assert Decimal(str(data["grand_total"])) == Decimal("51.30")
    assert_calculation_invariant(data)


def test_combination_composite_multi_item_order(client: TestClient):
    """C-03.2: Verify multiple order items combining garments and weight-based laundry."""
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Multi Item Composite Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    # 1. Shirts: $7.00
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["shirt"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "7.00",
    })
    # 2. Laundry: $2.50/kg
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["wash_fold"].id),
        "service_item_id": str(env["items"]["laundry_bag"].id),
        "rule_type": "PER_WEIGHT",
        "component_type": "BASE_PRICE",
        "rate": "2.50",
    })
    # Surcharge: $5.00
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["wash_fold"].id),
        "rule_type": "FIXED",
        "component_type": "SURCHARGE",
        "rate": "5.00",
    })
    # Tax: 10%
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": None,
        "rule_type": "FIXED",
        "component_type": "TAX",
        "rate": "10.00",
        "rate_type": "PERCENTAGE",
    })
    _activate_book(client, book_id, env["headers"])

    # 3 shirts ($21.00) + 10 kg laundry ($25.00) = Subtotal $46.00
    # Surcharge: $5.00
    # Taxable: $51.00
    # Tax: 10% of 51.00 = 5.10
    # Grand Total: 56.10
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
                "units": 10.0,
            },
        ],
    })
    assert calc_res.status_code == 200
    data = calc_res.json()
    assert Decimal(str(data["subtotal"])) == Decimal("46.00")
    assert Decimal(str(data["total_surcharges"])) == Decimal("5.00")
    assert Decimal(str(data["taxable_amount"])) == Decimal("51.00")
    assert Decimal(str(data["total_tax"])) == Decimal("5.10")
    assert Decimal(str(data["grand_total"])) == Decimal("56.10")
    assert_calculation_invariant(data)
