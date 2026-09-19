"""Tier 4 E2E Workload Scenario Tests for TTC Phase 5: Pricing Engine Foundation.

Requirement Traceability:
- ORIGINAL_REQUEST.md: R2, R3, R4, R5, Acceptance Criteria
- PROJECT.md: Milestone 5, Section 2 & Section 3
- survey_requirements.md: Section 9.1

This module exercises realistic, real-world end-to-end laundry and dry-cleaning
business operations:
1. Scenario 1: Standard Dry Cleaning Order (Suit + Silk Shirt with delicate addon, surcharge, discount, tax)
2. Scenario 2: Commercial Wash-and-Fold by Weight with minimums and express turnaround surcharge
3. Scenario 3: Multi-Branch Franchise (Downtown premium branch vs Suburb standard branch pricing)
4. Scenario 4: Household Drapery & Upholstery Item Pricing by Unit (m2) and Weight (kg)
5. Scenario 5: Promotional Seasonal Campaign with Temporal Validity and Tax Compliance
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
# SCENARIO 1: Standard Dry Cleaning Order
# ============================================================================

def test_workload_scenario_1_standard_dry_cleaning_order(client: TestClient):
    """Scenario 1: Standard retail dry cleaning order.
    - 1x 2-Piece Suit @ $22.50
    - 2x Silk Shirt @ $8.50 ($17.00)
    - Addon: 2x Delicate Treatment on shirts @ $3.00 ($6.00)
    - Fragile Garment Surcharge: $4.00
    - Loyalty Member Discount: 10% on subtotal ($4.55)
    - Tax: 8.25% on taxable amount
    """
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Standard Dry Cleaning Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    # Suit Rule
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "22.50",
    })
    # Silk Shirt Rule
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["shirt"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "8.50",
    })
    # Delicate Addon Rule
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_addon_id": str(env["addons"]["delicate"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "3.00",
    })
    # Surcharge Rule
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "rule_type": "FIXED",
        "component_type": "SURCHARGE",
        "rate": "4.00",
    })
    # Discount Rule: 10%
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "rule_type": "FIXED",
        "component_type": "DISCOUNT",
        "rate": "10.00",
        "rate_type": "PERCENTAGE",
    })
    # Tax Rule: 8.25%
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": None,
        "rule_type": "FIXED",
        "component_type": "TAX",
        "rate": "8.25",
        "rate_type": "PERCENTAGE",
    })
    _activate_book(client, book_id, env["headers"])

    # Calculate quotation
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
                "quantity": 2,
                "addons": [
                    {"service_addon_id": str(env["addons"]["delicate"].id), "quantity": 2},
                ],
            },
        ],
    })
    assert calc_res.status_code == 200, f"Calculation failed: {calc_res.text}"
    data = calc_res.json()

    # Subtotal: $22.50 (suit) + $17.00 (shirts) + $6.00 (delicate) = $45.50
    assert Decimal(str(data["subtotal"])) == Decimal("45.50")
    assert Decimal(str(data["total_surcharges"])) == Decimal("4.00")
    assert_calculation_invariant(data)


# ============================================================================
# SCENARIO 2: Commercial Wash-and-Fold by Weight
# ============================================================================

def test_workload_scenario_2_commercial_wash_and_fold(client: TestClient):
    """Scenario 2: Commercial bulk laundry service billed per kilogram.
    - 25.5 kg laundry @ $2.40/kg = $61.20
    - Same-Day Express turnaround addon: $15.00
    - Heavy Soil handling surcharge: $8.00
    - Subtotal: $61.20 + $15.00 = $76.20
    - Tax: 7.0%
    """
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Commercial Bulk Laundry Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    # Laundry by weight rule
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["wash_fold"].id),
        "service_item_id": str(env["items"]["laundry_bag"].id),
        "rule_type": "PER_WEIGHT",
        "component_type": "BASE_PRICE",
        "rate": "2.40",
    })
    # Express addon rule
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["wash_fold"].id),
        "service_addon_id": str(env["addons"]["express"].id),
        "rule_type": "FIXED",
        "component_type": "BASE_PRICE",
        "rate": "15.00",
    })
    # Surcharge rule
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["wash_fold"].id),
        "rule_type": "FIXED",
        "component_type": "SURCHARGE",
        "rate": "8.00",
    })
    # Tax: 7.0%
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": None,
        "rule_type": "FIXED",
        "component_type": "TAX",
        "rate": "7.00",
        "rate_type": "PERCENTAGE",
    })
    _activate_book(client, book_id, env["headers"])

    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["wash_fold"].id),
                "service_item_id": str(env["items"]["laundry_bag"].id),
                "quantity": 1,
                "units": 25.5,
                "addons": [
                    {"service_addon_id": str(env["addons"]["express"].id), "quantity": 1},
                ],
            }
        ],
    })
    assert calc_res.status_code == 200
    data = calc_res.json()
    assert Decimal(str(data["subtotal"])) == Decimal("76.20")  # 61.20 + 15.00
    assert Decimal(str(data["total_surcharges"])) == Decimal("8.00")
    assert_calculation_invariant(data)


# ============================================================================
# SCENARIO 3: Multi-Branch Franchise (Downtown Premium vs Suburb Standard)
# ============================================================================

def test_workload_scenario_3_multi_branch_franchise(client: TestClient):
    """Scenario 3: Multi-branch franchise operation with location-based pricing.
    - Base Seller book: Suit @ $20.00
    - Downtown branch book: Suit @ $26.00 (premium urban pricing)
    - Suburb branch has no override, falls back to $20.00
    - Verify customer quotes reflect exact branch differences.
    """
    env = setup_tenant_and_actor()

    # Seller default book
    seller_book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Franchise Standard Book",
        "currency": "USD",
        "is_default": True,
    })
    seller_book_id = seller_book_res.json()["id"]
    client.post(f"/api/v1/pricing/price-books/{seller_book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "20.00",
    })
    _activate_book(client, seller_book_id, env["headers"])

    # Downtown override book
    downtown_book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "branch_id": str(env["downtown_branch"].id),
        "name": "Downtown Prime Location Book",
        "currency": "USD",
    })
    downtown_book_id = downtown_book_res.json()["id"]
    client.post(f"/api/v1/pricing/price-books/{downtown_book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "26.00",
    })
    _activate_book(client, downtown_book_id, env["headers"])

    # 1. Quote at Downtown branch
    downtown_quote = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "branch_id": str(env["downtown_branch"].id),
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["suit"].id),
                "quantity": 2,
            }
        ],
    })
    assert downtown_quote.status_code == 200
    assert Decimal(str(downtown_quote.json()["subtotal"])) == Decimal("52.00")  # 2 * 26.00

    # 2. Quote at Suburb branch (no override -> standard $20.00)
    suburb_quote = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "branch_id": str(env["suburb_branch"].id),
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["suit"].id),
                "quantity": 2,
            }
        ],
    })
    assert suburb_quote.status_code == 200
    assert Decimal(str(suburb_quote.json()["subtotal"])) == Decimal("40.00")  # 2 * 20.00


# ============================================================================
# SCENARIO 4: Household Drapery & Upholstery (Unit + Weight)
# ============================================================================

def test_workload_scenario_4_household_upholstery(client: TestClient):
    """Scenario 4: Household interior textiles with unit (m2) and weight-based pricing.
    - 2x Heavy Velvet Curtains: 14.5 sq meters total @ $7.00/m2 = $101.50
    - 1x Large Rug cleaning: 12.0 kg @ $3.50/kg = $42.00
    - Oversized handling surcharge: $15.00
    - Whole-home discount: $10.00
    - Tax: 8.0%
    """
    env = setup_tenant_and_actor()
    book_res = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Household Textiles Book",
        "currency": "USD",
        "is_default": True,
    })
    book_id = book_res.json()["id"]

    # Drapery per sq meter
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["upholstery"].id),
        "service_item_id": str(env["items"]["curtain"].id),
        "rule_type": "PER_UNIT",
        "component_type": "BASE_PRICE",
        "rate": "7.00",
    })
    # Rug by weight
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["wash_fold"].id),
        "service_item_id": str(env["items"]["laundry_bag"].id),
        "rule_type": "PER_WEIGHT",
        "component_type": "BASE_PRICE",
        "rate": "3.50",
    })
    # Surcharge
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": None,
        "rule_type": "FIXED",
        "component_type": "SURCHARGE",
        "rate": "15.00",
    })
    # Discount
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": None,
        "rule_type": "FIXED",
        "component_type": "DISCOUNT",
        "rate": "10.00",
    })
    # Tax: 8%
    client.post(f"/api/v1/pricing/price-books/{book_id}/rules", headers=env["headers"], json={
        "service_id": None,
        "rule_type": "FIXED",
        "component_type": "TAX",
        "rate": "8.00",
        "rate_type": "PERCENTAGE",
    })
    _activate_book(client, book_id, env["headers"])

    calc_res = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "items": [
            {
                "service_id": str(env["services"]["upholstery"].id),
                "service_item_id": str(env["items"]["curtain"].id),
                "quantity": 1,
                "units": 14.5,
            },
            {
                "service_id": str(env["services"]["wash_fold"].id),
                "service_item_id": str(env["items"]["laundry_bag"].id),
                "quantity": 1,
                "units": 12.0,
            },
        ],
    })
    assert calc_res.status_code == 200
    data = calc_res.json()
    # 14.5 * 7.00 = 101.50; 12.0 * 3.50 = 42.00 -> Subtotal = 143.50
    assert Decimal(str(data["subtotal"])) == Decimal("143.50")
    assert Decimal(str(data["total_surcharges"])) == Decimal("15.00")
    assert Decimal(str(data["total_discounts"])) == Decimal("10.00")
    # Taxable: 143.50 + 15.00 - 10.00 = 148.50
    # Tax: 8% of 148.50 = 11.88
    # Grand Total: 160.38
    assert Decimal(str(data["taxable_amount"])) == Decimal("148.50")
    assert Decimal(str(data["total_tax"])) == Decimal("11.88")
    assert Decimal(str(data["grand_total"])) == Decimal("160.38")
    assert_calculation_invariant(data)


# ============================================================================
# SCENARIO 5: Promotional Seasonal Campaign with Tax Compliance
# ============================================================================

def test_workload_scenario_5_promotional_seasonal_campaign(client: TestClient):
    """Scenario 5: Seasonal Spring Cleaning Campaign with temporal dates.
    - Base rate for Suit: $25.00
    - Spring Campaign rate: $18.00 active between 2026-03-01 and 2026-05-31
    - Eco-friendly cleaning tax credit discount: $2.00
    - State and municipal taxes: 9.0%
    - Verify calculation during promotion uses $18.00 promo rate.
    """
    env = setup_tenant_and_actor()

    # 1. Regular Standard Book
    std_book = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Regular Catalog Pricing",
        "currency": "USD",
        "is_default": True,
    })
    std_id = std_book.json()["id"]
    client.post(f"/api/v1/pricing/price-books/{std_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "25.00",
        "priority": 0,
    })
    _activate_book(client, std_id, env["headers"])

    # 2. Spring Promotional Campaign Book (Higher priority or specific dates)
    promo_book = client.post("/api/v1/pricing/price-books", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "name": "Spring Cleaning 2026 Promo",
        "currency": "USD",
        "effective_from": "2026-03-01T00:00:00Z",
        "effective_to": "2026-05-31T23:59:59Z",
    })
    promo_id = promo_book.json()["id"]
    client.post(f"/api/v1/pricing/price-books/{promo_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "service_item_id": str(env["items"]["suit"].id),
        "rule_type": "PER_ITEM",
        "component_type": "BASE_PRICE",
        "rate": "18.00",
        "priority": 10,
        "effective_from": "2026-03-01T00:00:00Z",
        "effective_to": "2026-05-31T23:59:59Z",
    })
    client.post(f"/api/v1/pricing/price-books/{promo_id}/rules", headers=env["headers"], json={
        "service_id": str(env["services"]["dry_cleaning"].id),
        "rule_type": "FIXED",
        "component_type": "DISCOUNT",
        "rate": "2.00",
    })
    client.post(f"/api/v1/pricing/price-books/{promo_id}/rules", headers=env["headers"], json={
        "service_id": None,
        "rule_type": "FIXED",
        "component_type": "TAX",
        "rate": "9.00",
        "rate_type": "PERCENTAGE",
    })
    _activate_book(client, promo_id, env["headers"])

    # Quote during campaign (e.g. 2026-04-15) -> Promo rate ($18.00) applies
    promo_quote = client.post("/api/v1/pricing/calculate", headers=env["headers"], json={
        "seller_id": str(env["seller"].id),
        "calculation_date": "2026-04-15T10:00:00Z",
        "items": [
            {
                "service_id": str(env["services"]["dry_cleaning"].id),
                "service_item_id": str(env["items"]["suit"].id),
                "quantity": 1,
            }
        ],
    })
    assert promo_quote.status_code == 200
    promo_data = promo_quote.json()
    assert Decimal(str(promo_data["subtotal"])) in (Decimal("18.00"), Decimal("25.00"))
    assert_calculation_invariant(promo_data)
