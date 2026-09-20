# Task Assignment: E2E Test Suite Author — Phase 7 (Tiers 1-4)

## Working Directory
`/workspaces/TheTextileCare/.agents/test_writer_phase7_e2e`

## Authoritative Request & Specifications
Read:
- `/workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md` (specifically `## 2026-09-19T17:49:20Z`)
- `/workspaces/TheTextileCare/.agents/PROJECT.md`
- Survey Reports:
  - `/workspaces/TheTextileCare/.agents/spec_miner_survey_phase7/report.md`
  - `/workspaces/TheTextileCare/.agents/explorer_survey_phase7_2/report.md`
  - `/workspaces/TheTextileCare/.agents/explorer_survey_phase7_3/report.md`

## Mission
As `teamwork_preview_test_writer`, design and implement the comprehensive opaque-box E2E test suite for Phase 7: Commercial Billing, Payment Timing, Settlement Logic, and Seller Restrictions.
Your tests must be requirement-driven (derived from `ORIGINAL_REQUEST.md` and `PROJECT.md`), completely opaque-box, exercising the system via FastAPI test client / HTTP endpoints or domain service APIs, asserting exact behaviors, states, and mathematical calculations.

1. **Write `TEST_INFRA.md`**:
   - Location: `/workspaces/TheTextileCare/TEST_INFRA.md` (and copy in `/workspaces/TheTextileCare/.agents/TEST_INFRA.md`).
   - Include test philosophy, feature inventory, test architecture, and coverage thresholds.

2. **Implement Test Cases Across 4 Tiers in `backend/tests/e2e/`**:
   - `backend/tests/e2e/test_phase7_tier1_features.py`:
     - ≥5 test cases per feature across R1 to R5 (happy paths in isolation):
       - Feature 1: No payment charge at order creation (`OrderStatus.PENDING`, zero payment transactions created).
       - Feature 2: Customer pickup details submission and approval triggers payment creation.
       - Feature 3: Payment failure mode 1: hard gate (`payment_required_before_pickup = True`) blocks pickup completion / transition to `IN_PROGRESS`.
       - Feature 4: Payment failure mode 2: permissive mode (`outstanding_receivable_allowed = True`) permits pickup completion and sets payment to `OUTSTANDING`.
       - Feature 5: Dual gateway accounting: `TTC_GATEWAY` vs `SELLER_GATEWAY`, recording separate columns for `gateway_fee`, `gateway_tax`, `ttc_commission`, `ttc_commission_tax`.
       - Feature 6: Proportional commission recalculation on partial and full refunds based on `retained_amount = amount - refunded_amount`.
       - Feature 7: Commercial models: Model 1 (Commission %) vs Model 2 (Monthly Subscription) mutual exclusivity enforcement.
       - Feature 8: Monthly billing statements (`SellerBillingInvoice`) generation with unique `(seller_id, invoice_month)` constraint.
       - Feature 9: Idempotent daily late penalty calculation: $(\text{subtotal} + \text{tax\_total}) \times \text{daily\_penalty\_rate} \times \text{days\_overdue}$.
       - Feature 10: 15-day cooling hold logic for `TTC_GATEWAY` funds (`paid_at <= now - 15 days`).
       - Feature 11: Weekly Monday batch settlement payouts (`SellerSettlement`) for `TTC_GATEWAY`.
       - Feature 12: Direct settlement bypass for `SELLER_GATEWAY` (zero hold, zero settlement records created).
       - Feature 13: Transition to `MARKETPLACE_RESTRICTED` upon overdue invoice threshold.
       - Feature 14: Automated cancellation of `PENDING` marketplace orders with reason `SELLER_RESTRICTED`.
       - Feature 15: Preservation of operational orders (`CONFIRMED`, `IN_PROGRESS`) when seller is restricted.
       - Feature 16: Customer seller re-selection (`POST /api/v1/orders/{order_id}/reselect`) creating new order linked via `reselected_from_order_id`.
       - Feature 17: Zero-refund verification on re-selection (since `PENDING` orders were uncharged).
       - Feature 18: Operational `OrderStatus` separation from `PaymentStatus`, `InvoiceStatus`, and `SellerRestrictionLevel`.
       - Feature 19: Strict tenant isolation (reject cross-tenant references).
       - Feature 20: Financial idempotency checks.
   - `backend/tests/e2e/test_phase7_tier2_boundaries.py`:
     - Boundary and corner cases (≥5 per feature domain):
       - Exact 15-day boundary for cooling hold (day 14 ineligible, day 15 eligible).
       - Settlement payout on Monday vs Sunday vs Tuesday.
       - 0-day overdue vs 1-day overdue penalty calculations.
       - 100% refund (commission becomes 0.00) vs 1-cent refund vs partial refunds with rounding.
       - Boundary commission rates (0.01%, 99.99%) and subscription fees.
       - Re-selection attempts on non-cancelled orders or already-reselected orders (400/409).
       - Re-selection with invalid or inactive new seller.
       - Cross-tenant payment or invoice mutation attempts (403/404).
   - `backend/tests/e2e/test_phase7_tier3_combinations.py`:
     - Pairwise combinations across Gateway Type × Commercial Model × Failure Mode × Restriction Status.
   - `backend/tests/e2e/test_phase7_tier4_workloads.py`:
     - ≥5 end-to-end realistic user journeys:
       - Scenario 1: Standard customer journey with TTC Gateway: order placed -> pickup inspected & approved -> payment charged -> 15-day hold -> Monday settlement payout.
       - Scenario 2: Seller-owned gateway journey with Model 2 subscription: order placed -> pickup approved -> payment via seller gateway -> zero TTC hold -> monthly subscription billing.
       - Scenario 3: Payment failure with hard gate vs customer retry -> successful completion.
       - Scenario 4: Overdue seller restriction: marketplace discovery suppression -> auto-cancellation of pending orders -> operational orders completed -> customer re-selects alternative seller.
       - Scenario 5: Partial garment defect -> customer partial refund -> commission proportional recalculation -> net settlement adjustment.

3. **Publish `TEST_READY.md`**:
   - Location: `/workspaces/TheTextileCare/TEST_READY.md` (and copy in `/workspaces/TheTextileCare/.agents/TEST_READY.md`).
   - Detail the test runner command, total test count across tiers, and feature checklist.

Deliver your handoff at `/workspaces/TheTextileCare/.agents/test_writer_phase7_e2e/handoff.md`.
Keep `progress.md` updated. Send a message when `TEST_READY.md` is published.

## 2026-09-19T17:59:51Z
You are test_writer_phase7_e2e.
Your working directory is: /workspaces/TheTextileCare/.agents/test_writer_phase7_e2e
Read /workspaces/TheTextileCare/.agents/test_writer_phase7_e2e/DISPATCH.md, /workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md (specifically ## 2026-09-19T17:49:20Z), and /workspaces/TheTextileCare/.agents/PROJECT.md.
Design and implement:
1. TEST_INFRA.md at /workspaces/TheTextileCare/TEST_INFRA.md (and copy to /workspaces/TheTextileCare/.agents/TEST_INFRA.md).
2. Comprehensive opaque-box E2E test files in backend/tests/e2e/:
   - test_phase7_tier1_features.py (>=5 tests per feature across R1 to R5)
   - test_phase7_tier2_boundaries.py (>=5 tests per boundary/corner)
   - test_phase7_tier3_combinations.py (pairwise combinations)
   - test_phase7_tier4_workloads.py (>=5 realistic application scenarios)
3. Publish TEST_READY.md at /workspaces/TheTextileCare/TEST_READY.md (and copy to /workspaces/TheTextileCare/.agents/TEST_READY.md).
Deliver your handoff at /workspaces/TheTextileCare/.agents/test_writer_phase7_e2e/handoff.md.
Keep progress.md updated. When TEST_READY.md is published, send a message to your caller.

