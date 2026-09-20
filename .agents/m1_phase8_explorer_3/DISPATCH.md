# Dispatch Task: Milestone 1 Explorer 3 — Driver REST APIs & Unit Testing Strategy

## Working Directory
`/workspaces/TheTextileCare/.agents/m1_phase8_explorer_3`

## Scope & Objective
Investigate the technical implementation strategy for Milestone 1:
- Driver management REST APIs under `/api/v1/seller/drivers` and `/api/v1/platform/drivers`.
- Unit and service-level test suite for Milestone 1 (`backend/tests/unit/test_driver_eligibility.py` and `backend/tests/unit/test_driver_priority_engine.py`).

## Inputs to Read
- `/workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md`
- `/workspaces/TheTextileCare/.agents/PROJECT.md`
- `/workspaces/TheTextileCare/.agents/survey_spec_miner_1/handoff.md`
- `/workspaces/TheTextileCare/.agents/survey_explorer_2/handoff.md`
- `/workspaces/TheTextileCare/.agents/survey_explorer_3/handoff.md`

## Specific Analysis Needed
1. **REST Endpoints Architecture**:
   - Platform endpoints (`/api/v1/platform/drivers`): onboard driver, list all drivers, view compliance documents, verify compliance documents.
   - Seller endpoints (`/api/v1/seller/drivers`): list authorized drivers for seller, update driver shift/availability status, link driver to seller branch.
   - Role & permission security dependencies (`require_permission`, `TenantContext`).
2. **Unit & Service Testing Strategy**:
   - Unit tests for `DriverEligibilityService`:
     - Test inactive driver rejected.
     - Test offline driver rejected.
     - Test expired compliance document (`DL`, `RC`, etc.) rejected.
     - Test unverified compliance document rejected.
     - Test driver at capacity (`active_duties >= max_active_duties`) rejected.
     - Test fully compliant, available driver accepted.
   - Unit tests for `PriorityResolutionEngine`:
     - Test address familiarity wins over customer familiarity.
     - Test customer familiarity wins when address familiarity is tied.
     - Test workload balancing wins when customer familiarity is tied.
     - Test proximity wins when workload is tied.
     - Test deterministic tie-break by registration date and ID.
3. Test fixture integration and CI validation command requirements.

## Output Requirements
Write a complete, structured analysis in `/workspaces/TheTextileCare/.agents/m1_phase8_explorer_3/handoff.md` with endpoint signatures, test cases, and recommendations for the Worker.

## 2026-09-20T08:15:32Z
You are m1_phase8_explorer_3. Your working directory is /workspaces/TheTextileCare/.agents/m1_phase8_explorer_3.
Read your instructions in /workspaces/TheTextileCare/.agents/m1_phase8_explorer_3/DISPATCH.md, /workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md, and /workspaces/TheTextileCare/.agents/PROJECT.md.
Investigate Milestone 1 implementation strategy for Driver REST APIs and unit test suites.
Deliver your handoff report to /workspaces/TheTextileCare/.agents/m1_phase8_explorer_3/handoff.md and notify parent when complete.

