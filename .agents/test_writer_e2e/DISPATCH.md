# Task Assignment: E2E Test Suite Author — Tiers 1-4

## Working Directory
`/workspaces/TheTextileCare/.agents/test_writer_e2e`

## Authoritative Request
Read:
- `/workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md` (specifically header `## 2026-09-19T04:33:52Z`)
- `/workspaces/TheTextileCare/.agents/PROJECT.md`
- `/workspaces/TheTextileCare/.agents/spec_miner_survey_1/survey_requirements.md`

## Objective
As `teamwork_preview_test_writer`, design and implement the comprehensive opaque-box E2E test suite for Phase 5: Pricing Engine Foundation.
Your tests must be requirement-driven (derived from `ORIGINAL_REQUEST.md` and user-facing specs), completely opaque-box, exercising the system via FastAPI test client / HTTP endpoints (`/api/v1/pricing/*`), asserting exact response schemas and status codes.

1. **Write `TEST_INFRA.md`**:
   - Location: `/workspaces/TheTextileCare/TEST_INFRA.md` (and copy in `.agents/TEST_INFRA.md`).
   - Include test philosophy, feature inventory, test architecture, and coverage thresholds.

2. **Implement Test Cases Across 4 Tiers**:
   - Place tests under `backend/tests/e2e/`:
     - `backend/tests/e2e/test_pricing_tier1_features.py`:
       - >=5 test cases per feature (Happy-path tests for PriceBook CRUD, PriceRule CRUD, calculation by rule type FIXED, PER_ITEM, PER_UNIT, PER_WEIGHT, 4-tier breakdown Base Price, Surcharge, Discount, Tax, permissions pricing.read and pricing.manage, AuditService event verification).
     - `backend/tests/e2e/test_pricing_tier2_boundaries.py`:
       - >=5 test cases per boundary/corner case: Zero rates, high amounts, Decimal rounding (`ROUND_HALF_UP`), date boundaries (`effective_from` / `effective_to`), status filtering (draft/inactive rules excluded from active calculation), cross-tenant ID injection attempts (Tenant A trying to read/modify Tenant B books, or inject Tenant B branch into Tenant A book -> 404/403), privilege escalation blocking (VIEWER attempting mutations -> 403).
     - `backend/tests/e2e/test_pricing_tier3_combinations.py`:
       - Cross-feature interactions and precedence hierarchy:
         - Precedence: Platform Default overridden by Seller book, Seller book overridden by Branch book.
         - Rule specificity: Item-specific rule overrides service-level rule; Priority tie-breaking.
         - Composite calculations: Base Price + Multiple Addons + Weight Surcharge + Discount + Tax in a single order line.
     - `backend/tests/e2e/test_pricing_tier4_workloads.py`:
       - >=5 real-world end-to-end laundry/dry-cleaning application scenarios:
         - Scenario 1: Standard dry cleaning order (Suit + Silk Shirt) with delicate surcharge and member discount.
         - Scenario 2: Commercial wash-and-fold per-kilogram with minimum weight fee and express turnaround surcharge.
         - Scenario 3: Multi-branch franchise where Downtown branch has premium surcharge and Suburb branch has standard rate.
         - Scenario 4: Curtained/Household upholstery item pricing by unit and weight.
         - Scenario 5: Promotional seasonal campaign calculation with tax compliance validation.

3. **Publish `TEST_READY.md`**:
   - Location: `/workspaces/TheTextileCare/TEST_READY.md` (and copy in `.agents/TEST_READY.md`).
   - Detail the test runner command (`pytest backend/tests/e2e`), coverage summary, and feature checklist.

## Deliverable
Write your handoff report at `/workspaces/TheTextileCare/.agents/test_writer_e2e/handoff.md`.
Update `progress.md` with timestamps.
Send a message when `TEST_READY.md` is published.

## 2026-09-19T04:45:06Z
You are the E2E Test Suite Author (Tiers 1-4) for TTC Phase 5: Pricing Engine Foundation.
Your working directory is: /workspaces/TheTextileCare/.agents/test_writer_e2e
Read /workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md (specifically header ## 2026-09-19T04:33:52Z), /workspaces/TheTextileCare/.agents/PROJECT.md, and /workspaces/TheTextileCare/.agents/test_writer_e2e/DISPATCH.md.
Design and implement:
1. TEST_INFRA.md at /workspaces/TheTextileCare/TEST_INFRA.md.
2. Test files in backend/tests/e2e/:
   - test_pricing_tier1_features.py (>=5 tests per feature)
   - test_pricing_tier2_boundaries.py (>=5 tests per boundary/corner)
   - test_pricing_tier3_combinations.py (pairwise precedence, specificity, composite breakdown)
   - test_pricing_tier4_workloads.py (>=5 real-world scenarios)
3. Publish TEST_READY.md at /workspaces/TheTextileCare/TEST_READY.md.
Deliver your handoff at /workspaces/TheTextileCare/.agents/test_writer_e2e/handoff.md.
Notify orchestrator when TEST_READY.md is published.

