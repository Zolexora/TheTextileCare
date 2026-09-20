# TTC Phase 5: Pricing Engine Foundation — Test Ready Publication (TEST_READY.md)

**Document Status**: PUBLISHED & READY FOR VERIFICATION  
**Author**: E2E Test Suite Author (`teamwork_preview_test_writer`)  
**Date**: 2026-09-19  
**Location**: `/workspaces/TheTextileCare/TEST_READY.md` (and `.agents/TEST_READY.md`)  
**Target Milestone**: Phase 5 — Pricing Engine Foundation (M1–M5)  

---

## 1. Executive Summary

The complete, opaque-box End-to-End (E2E) Test Suite for **Phase 5: Pricing Engine Foundation** is fully designed, implemented, and validated. The suite encompasses **72 distinct test cases** spanning **Tiers 1 through 4**, strictly adhering to the requirements set forth in `ORIGINAL_REQUEST.md` (Header `## 2026-09-19T04:33:52Z`), `PROJECT.md`, and `survey_requirements.md`.

All tests interact exclusively through the external HTTP API (`/api/v1/pricing/*`) using FastAPI's `TestClient` with authenticated multi-tenant context (`X-User-Id`, `X-Tenant-Id`), treating internal database tables, services, and repositories as pure black boxes.

---

## 2. Test Execution Commands

The E2E test suite can be executed with standard `pytest` commands inside the project's Python virtual environment:

```bash
# Execute entire E2E test suite across all 4 tiers (72 tests)
.venv/bin/pytest backend/tests/e2e/ -v

# Execute with short tracebacks
.venv/bin/pytest backend/tests/e2e/ -q --tb=short

# Execute Tier 1: Functional Features (30 tests)
.venv/bin/pytest backend/tests/e2e/test_pricing_tier1_features.py -v

# Execute Tier 2: Boundaries, Corners & Security (30 tests)
.venv/bin/pytest backend/tests/e2e/test_pricing_tier2_boundaries.py -v

# Execute Tier 3: Precedence & Cross-Feature Combinations (7 tests)
.venv/bin/pytest backend/tests/e2e/test_pricing_tier3_combinations.py -v

# Execute Tier 4: Real-World Application Workloads (5 scenarios)
.venv/bin/pytest backend/tests/e2e/test_pricing_tier4_workloads.py -v
```

---

## 3. Test Suite Inventory by Tier

```
backend/tests/e2e/
├── __init__.py
├── conftest.py                          # Fixtures: isolated DB reset, catalog tree setup, invariant assertions
├── test_pricing_tier1_features.py       # Tier 1: 30 tests (>=5 tests per feature across 6 features)
├── test_pricing_tier2_boundaries.py     # Tier 2: 30 tests (>=5 tests per corner across 6 boundaries)
├── test_pricing_tier3_combinations.py   # Tier 3: 7 tests (Precedence, Specificity, Composite Calculations)
└── test_pricing_tier4_workloads.py      # Tier 4: 5 tests (End-to-End Business Workload Scenarios)
```

### 3.1 Tier 1: Functional Feature Coverage (30 Tests)
Located in `backend/tests/e2e/test_pricing_tier1_features.py`:
- **PriceBook CRUD Lifecycle** (5 tests):
  - `test_feature_price_book_create_success`: Successful creation of seller-scoped price book with currency and metadata.
  - `test_feature_price_book_get_by_id`: Lookup of specific price book by ID.
  - `test_feature_price_book_list_and_filter`: Filtering price books by `seller_id`.
  - `test_feature_price_book_update`: Updating price book name and description via PATCH/PUT.
  - `test_feature_price_book_delete`: Deleting price book and verifying subsequent 404 response.
- **PriceRule CRUD Lifecycle** (5 tests):
  - `test_feature_price_rule_create`: Creating a rule on a price book linked to a catalog service item.
  - `test_feature_price_rule_list`: Listing all rules attached to a price book.
  - `test_feature_price_rule_update`: Updating rule rate and priority.
  - `test_feature_price_rule_delete`: Removing rule from book and verifying empty rule set.
  - `test_feature_price_rule_addon_attachment`: Creating surcharge rule attached to a catalog addon.
- **Calculation by Rule Type** (5 tests):
  - `test_feature_calc_fixed_rule`: Verifying flat rate computation independent of quantity.
  - `test_feature_calc_per_item_rule`: Verifying multiplication by piece count (`rate * quantity`).
  - `test_feature_calc_per_unit_rule`: Verifying multiplication by measurable unit (`rate * units`).
  - `test_feature_calc_per_weight_rule`: Verifying multiplication by scale weight (`rate * weight_kg`).
  - `test_feature_calc_mixed_rule_types_in_single_request`: Aggregating per-item and per-weight services simultaneously.
- **4-Tier Financial Breakdown** (5 tests):
  - `test_feature_breakdown_base_price_and_addons`: Verifying base item charges and addon fees in subtotal.
  - `test_feature_breakdown_surcharges`: Verifying flat and percentage surcharges in `total_surcharges`.
  - `test_feature_breakdown_discounts`: Verifying discount deductions in `total_discounts`.
  - `test_feature_breakdown_tax`: Verifying sales tax computation on taxable subtotal.
  - `test_feature_breakdown_all_four_tiers_with_invariant`: Verifying complete breakdown and mathematical invariant.
- **RBAC Permissions & Security** (5 tests):
  - `test_feature_rbac_pricing_manage_allows_mutation`: `TENANT_ADMIN` role creates books and rules.
  - `test_feature_rbac_pricing_read_allows_listing_and_calculation`: `VIEWER` role queries and calculates prices.
  - `test_feature_rbac_viewer_denied_mutation`: `VIEWER` role blocked from mutating pricing books (403).
  - `test_feature_rbac_tenant_member_denied_all`: `TENANT_MEMBER` blocked from reading or managing pricing (403).
  - `test_feature_rbac_unauthenticated_request_rejected`: Missing headers rejected with 401/403.
- **AuditService Event Trails** (5 tests):
  - `test_feature_audit_book_created_logged`: Verified `PRICING_BOOK_CREATED` event in `audit_events`.
  - `test_feature_audit_book_updated_logged`: Verified `PRICING_BOOK_UPDATED` event in `audit_events`.
  - `test_feature_audit_rule_created_logged`: Verified `PRICING_RULE_CREATED` event in `audit_events`.
  - `test_feature_audit_rule_updated_logged`: Verified `PRICING_RULE_UPDATED` event in `audit_events`.
  - `test_feature_audit_rule_deleted_logged`: Verified `PRICING_RULE_DELETED` event in `audit_events`.

### 3.2 Tier 2: Boundary & Corner Conditions (30 Tests)
Located in `backend/tests/e2e/test_pricing_tier2_boundaries.py`:
- **Zero Rates & Extreme Amounts** (5 tests):
  - `test_boundary_zero_rate_service`: $0.00 free service computation.
  - `test_boundary_high_monetary_amount`: $1,000,000.00 rate arithmetic without overflow.
  - `test_boundary_negative_rate_rejected`: Negative rate payload rejected with 400/422.
  - `test_boundary_zero_quantity_rejected`: Quantity <= 0 rejected with 400/422.
  - `test_boundary_high_precision_rate`: 4-decimal precision rate ($1.2345) verified and calculated.
- **Decimal Rounding & Precision** (5 tests):
  - `test_boundary_rounding_half_up_exactness`: Strict `ROUND_HALF_UP` verification (e.g. 10.125 -> 10.13).
  - `test_boundary_fractional_tax_rounding`: Exact fractional tax rounding (8.875% on $15.50 = 1.38).
  - `test_boundary_discount_clamped_to_subtotal`: Clamping discount so grand total never drops below $0.00.
  - `test_boundary_multiple_lines_rounding_consistency`: Multi-line rounding sums match grand total.
  - `test_boundary_percentage_surcharge_rounding`: Exact half-up rounding on percentage surcharges.
- **Date Validity Boundaries** (5 tests):
  - `test_boundary_expired_rule_excluded`: Past `effective_to` excluded from calculation.
  - `test_boundary_future_rule_excluded`: Future `effective_from` excluded from current calculation.
  - `test_boundary_currently_effective_rule_included`: Active window rule applied.
  - `test_boundary_open_ended_date_range`: `effective_to=None` remains valid indefinitely.
  - `test_boundary_specific_calculation_date_evaluation`: Historic/future date query accurately matched.
- **Status Lifecycle Filtering** (5 tests):
  - `test_boundary_draft_book_excluded_from_calculation`: Book in `DRAFT` ignored during calculation.
  - `test_boundary_inactive_book_excluded_from_calculation`: Book in `INACTIVE` ignored during calculation.
  - `test_boundary_inactive_rule_within_active_book_excluded`: Inactive rule within active book skipped.
  - `test_boundary_transition_draft_to_active_enables_calculation`: Book activation immediately enables pricing.
  - `test_boundary_status_filter_in_list_api`: Status query parameter filters book results.
- **Cross-Tenant ID Injection & Boundary Isolation** (5 tests):
  - `test_boundary_cross_tenant_book_read_denied`: Tenant B reading Tenant A book returns 404.
  - `test_boundary_cross_tenant_book_update_denied`: Tenant B updating Tenant A book returns 404.
  - `test_boundary_cross_tenant_book_delete_denied`: Tenant B deleting Tenant A book returns 404.
  - `test_boundary_id_injection_foreign_seller`: Attaching foreign `seller_id` rejected (400/404).
  - `test_boundary_id_injection_foreign_branch`: Attaching foreign `branch_id` rejected (400/404).
- **Privilege Escalation Protection** (5 tests):
  - `test_boundary_privilege_viewer_cannot_create_book`: `VIEWER` creating book returns 403.
  - `test_boundary_privilege_viewer_cannot_update_book`: `VIEWER` updating book returns 403.
  - `test_boundary_privilege_viewer_cannot_delete_book`: `VIEWER` deleting book returns 403.
  - `test_boundary_privilege_viewer_cannot_create_rule`: `VIEWER` creating rule returns 403.
  - `test_boundary_privilege_staff_cannot_delete_book`: `STAFF` deleting book returns 403.

### 3.3 Tier 3: Precedence & Cross-Feature Combinations (7 Tests)
Located in `backend/tests/e2e/test_pricing_tier3_combinations.py`:
- **Precedence Hierarchy**:
  - `test_combination_precedence_seller_overrides_platform`: Seller book overrides Platform default.
  - `test_combination_precedence_branch_overrides_seller`: Branch book overrides Seller default.
  - `test_combination_precedence_branch_fallback_to_seller`: Branch book missing an item falls back to Seller book.
- **Specificity & Priority Tie-Breaking**:
  - `test_combination_specificity_item_overrides_service_level`: Item-specific rule overrides generic service rule.
  - `test_combination_priority_tie_breaking`: Rule with `priority=20` overrides rule with `priority=10`.
- **Composite Calculations**:
  - `test_combination_composite_single_line_full_breakdown`: Single order line combining Base + 2 Addons + Surcharge + Discount + Tax.
  - `test_combination_composite_multi_item_order`: Multi-line order combining per-item garments and per-weight wash-and-fold.

### 3.4 Tier 4: Real-World Business Workloads (5 Tests)
Located in `backend/tests/e2e/test_pricing_tier4_workloads.py`:
- **Scenario 1**: Standard Retail Dry Cleaning
  - `test_workload_scenario_1_standard_dry_cleaning_order`: 1x 2-Piece Suit ($22.50) + 2x Silk Shirts ($17.00) + 2x Delicate Addons ($6.00) + Fragile Surcharge ($4.00) - 10% Member Discount + 8.25% Sales Tax.
- **Scenario 2**: Commercial Wash-and-Fold Bulk by Weight
  - `test_workload_scenario_2_commercial_wash_and_fold`: 25.5 kg laundry @ $2.40/kg ($61.20) + Same-Day Express turnaround ($15.00) + Heavy Soil surcharge ($8.00) + 7.0% Sales Tax.
- **Scenario 3**: Multi-Branch Franchise (Downtown vs Suburb)
  - `test_workload_scenario_3_multi_branch_franchise`: Identical dry cleaning order evaluated at Downtown branch ($26.00/suit) vs Suburb branch ($20.00/suit).
- **Scenario 4**: Household Drapery & Upholstery
  - `test_workload_scenario_4_household_upholstery`: 14.5 m² Velvet Curtains ($101.50) + 12.0 kg Rug Cleaning ($42.00) + Oversized Handling ($15.00) - Household Discount ($10.00) + 8.0% Tax.
- **Scenario 5**: Promotional Seasonal Campaign with Tax Compliance
  - `test_workload_scenario_5_promotional_seasonal_campaign`: Spring Cleaning promo active during date window with promotional discount and sales tax calculation.

---

## 4. Requirements Traceability Matrix

| Requirement | Description | E2E Verification Coverage |
|---|---|---|
| **R1** | Modular monolith integrity | Validated across all tests executing within single application process. |
| **R2** | Core pricing model & Decimal precision | `test_pricing_tier1_features.py` (CRUD, 4 types), `test_pricing_tier2_boundaries.py` (Rounding). |
| **R3** | Deterministic calculation engine & precedence | `test_pricing_tier3_combinations.py` (Precedence & Specificity), `test_pricing_tier4_workloads.py`. |
| **R4** | Tenant isolation, ID injection, RBAC & Audit | `test_pricing_tier1_features.py` (RBAC, Audit), `test_pricing_tier2_boundaries.py` (Injection, Roles). |
| **R5** | REST APIs under `/api/v1/pricing/*` | All 72 tests exercise REST endpoints exclusively. |

---

## 5. Invariant Mathematical Guarantee

Every calculation response across all test tiers is automatically validated against the fundamental financial equation:

$$\text{grand\_total} \equiv \text{subtotal} + \text{total\_surcharges} - \text{total\_discounts} + \text{total\_tax}$$

$$\text{taxable\_amount} \equiv \text{subtotal} + \text{total\_surcharges} - \text{total\_discounts}$$

All values are evaluated using Python's `Decimal` class with `ROUND_HALF_UP` rounding to 2 decimal places ($0.01$). Any discrepancy triggers an explicit assertion failure.
