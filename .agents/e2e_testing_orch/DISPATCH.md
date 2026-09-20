# Task Assignment: E2E Testing Track Orchestrator

## Working Directory
`/workspaces/TheTextileCare/.agents/e2e_testing_orch`

## Role & Mission
You are the E2E Testing Track Orchestrator for TTC Phase 5: Pricing Engine Foundation.
Your parent is Project Orchestrator (`6f64afd2-1d3a-42aa-aecd-e2488f1779ca`).

## Authoritative Context & Scope
Read:
- `/workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md` (specifically header `## 2026-09-19T04:33:52Z`)
- `/workspaces/TheTextileCare/.agents/PROJECT.md`
- Survey reports:
  - `/workspaces/TheTextileCare/.agents/spec_miner_survey_1/survey_requirements.md`
  - `/workspaces/TheTextileCare/.agents/explorer_survey_2/survey_backend.md`

## E2E Testing Track Objectives
1. **Design Opaque-Box Test Infrastructure**:
   - Requirement-driven, independent of internal implementation design.
   - Create `TEST_INFRA.md` at `/workspaces/TheTextileCare/TEST_INFRA.md` following the template in Project Pattern:
     - Test philosophy (Opaque-box, requirement-driven).
     - Feature inventory and mapping to test tiers.
     - Test runner invocation and pass/fail semantics.
     - Directory layout (e.g. `backend/tests/e2e/test_pricing_e2e_tier*.py` or dedicated suite).
2. **Implement Test Cases Across 4 Tiers**:
   - **Tier 1 — Feature Coverage (>=5 per feature)**: Happy-path tests verifying each feature in isolation (price book CRUD, price rule CRUD, calculation by rule type FIXED, PER_ITEM, PER_UNIT, PER_WEIGHT, breakdown components, permissions, audit emission).
   - **Tier 2 — Boundary & Corner Cases (>=5 per feature)**: Zero rates, max values, precision rounding edge cases, invalid dates, effective date boundaries (`effective_from` exact second, expired `effective_to`), inactive rules, cross-tenant ID injection attempts, privilege escalation by `VIEWER` roles.
   - **Tier 3 — Cross-Feature Combinations (pairwise coverage)**: Multi-rule interactions (e.g. Base Price FIXED + Addon PER_ITEM + Surcharge PER_WEIGHT + Discount + Tax), precedence overrides (Platform Default vs Seller vs Branch), specific item overrides service-level rule.
   - **Tier 4 — Real-World Application Scenarios (>=5 scenarios)**: End-to-end laundry/dry-cleaning service calculation workloads (e.g., standard dry-clean order with express surcharge and student discount, commercial laundry per-kg with pickup fee and regional tax, multi-branch franchise pricing).
3. **Publish TEST_READY.md**:
   - When test infrastructure and test cases are ready, publish `TEST_READY.md` at `/workspaces/TheTextileCare/TEST_READY.md` (and a copy in `/workspaces/TheTextileCare/.agents/TEST_READY.md`) detailing the test runner command and coverage metrics.
4. **Execution Rules**:
   - As Orchestrator, dispatch test writers / workers / reviewers per your orchestration pattern.
   - Maintain your own `BRIEFING.md`, `progress.md`, and deliver `handoff.md`.
   - Notify Project Orchestrator via `send_message` when `TEST_READY.md` is published.
