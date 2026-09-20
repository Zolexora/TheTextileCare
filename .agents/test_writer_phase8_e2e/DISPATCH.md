# Dispatch Task: E2E Test Writer — Opaque-Box Test Suite (Tiers 1–4)

## 2026-09-20T08:15:31Z
You are test_writer_phase8_e2e. Your working directory is /workspaces/TheTextileCare/.agents/test_writer_phase8_e2e.
Read your instructions in /workspaces/TheTextileCare/.agents/test_writer_phase8_e2e/DISPATCH.md, /workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md, /workspaces/TheTextileCare/.agents/PROJECT.md, and /workspaces/TheTextileCare/.agents/TEST_INFRA.md.
Implement the comprehensive E2E test suite (Tiers 1–4) and write TEST_READY.md.
Deliver your handoff report to /workspaces/TheTextileCare/.agents/test_writer_phase8_e2e/handoff.md and notify parent when complete.

## Objective
Author the authoritative, opaque-box E2E test suite for TTC Driver Assignment, Reassignment, and Notifications (Q51–Q100 / R1–R4) across Tiers 1–4, and publish `TEST_READY.md`.

## Inputs to Read
- `/workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md` (specifically `## 2026-09-20T08:01:28Z`)
- `/workspaces/TheTextileCare/.agents/PROJECT.md`
- `/workspaces/TheTextileCare/.agents/TEST_INFRA.md`
- Survey reports:
  - `/workspaces/TheTextileCare/.agents/survey_spec_miner_1/handoff.md`
  - `/workspaces/TheTextileCare/.agents/survey_explorer_2/handoff.md`
  - `/workspaces/TheTextileCare/.agents/survey_explorer_3/handoff.md`

## Deliverables
1. **Test Fixtures & Helpers**:
   - In `backend/tests/e2e/test_driver_helpers.py` (or shared test helper):
     - `create_test_driver(...)`
     - `create_test_driver_vehicle(...)`
     - `create_test_driver_compliance(...)`
     - `create_test_duty(...)`
     - `create_test_assignment(...)`
     - Helper to simulate customer orders and completed duty history for familiarity scoring.
2. **Tier 1 — Feature Coverage Test Suite** (`backend/tests/e2e/test_driver_tier1_features.py`):
   - At least 5 test cases per feature for Features 1–16 listed in `TEST_INFRA.md`:
     - Driver profiles, vehicles, compliance documents.
     - Eligibility gates (active, shift, capacity, compliance validity).
     - 4-Tier priority scoring in isolation (address familiarity, customer familiarity, workload, distance).
     - Authoritative assignment (no accept/reject state).
     - Concurrency row-locking (`FOR UPDATE`) and partial unique index.
     - Reassignment with mandatory reason.
     - Pre-duty unavailability auto-reassign + alert.
     - Post-duty unavailability & late start manual alert.
     - Immediate notifications with driver name, vehicle, unmasked phone.
     - Notification failure decoupling (no assignment rollback).
     - Tenant and seller isolation.
     - Payment decoupling (assignment before payment).
3. **Tier 2 — Boundary & Corner Case Test Suite** (`backend/tests/e2e/test_driver_tier2_boundaries.py`):
   - Boundary value tests: compliance document expiring today vs tomorrow vs yesterday; workload capacity at limit (`active == max_duties`); empty/whitespace reassignment reasons (HTTP 422); ties in priority ranking broken by seniority (`created_at`) and `id`; duty late start detection exact minute boundary.
4. **Tier 3 — Cross-Feature Interaction Test Suite** (`backend/tests/e2e/test_driver_tier3_combinations.py`):
   - Multi-feature interactions: Pre-duty reassignment triggering priority engine + customer notification update + replaced driver deactivation; candidate pool expansion from primary branch to secondary pool; concurrent reassignment attempts.
5. **Tier 4 — Real-World Application Workloads** (`backend/tests/e2e/test_driver_tier4_scenarios.py`):
   - The 6 real-world scenarios defined in `TEST_INFRA.md` (Peak Pickup Dispatch, Pre-duty Flat Tire Auto-Reassignment, Post-duty Breakdown Emergency Alert, Flash Sale Concurrency Race, Network Outage Resilience, Cross-Tenant Security Attack).
6. **Publish `TEST_READY.md`**:
   - Write `/workspaces/TheTextileCare/.agents/TEST_READY.md` summarizing total test counts per tier, runner command (`pytest -v backend/tests/e2e/test_driver_*.py`), and coverage checklist.
7. **Write Handoff**:
   - Write `/workspaces/TheTextileCare/.agents/test_writer_phase8_e2e/handoff.md` and send message to parent when done.
