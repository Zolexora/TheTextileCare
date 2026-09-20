# Dispatch Task: Milestone 1 Explorer 2 — Driver Eligibility & 4-Tier Priority Resolution Engine

## Working Directory
`/workspaces/TheTextileCare/.agents/m1_phase8_explorer_2`

## Scope & Objective
Investigate the technical implementation strategy for Milestone 1:
- `DriverEligibilityService` in `backend/app/services/driver.py`: binary eligibility evaluation.
- `PriorityResolutionEngine` in `backend/app/services/priority_engine.py`: 4-tier lexicographical ranking algorithm.

## Inputs to Read
- `/workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md`
- `/workspaces/TheTextileCare/.agents/PROJECT.md`
- `/workspaces/TheTextileCare/.agents/survey_spec_miner_1/handoff.md`
- `/workspaces/TheTextileCare/.agents/survey_explorer_2/handoff.md`

## Specific Analysis Needed
1. **Eligibility Filter Rules**:
   - `driver.status == DriverStatus.ACTIVE`
   - `driver.availability_status == DriverAvailabilityStatus.AVAILABLE` (and/or on-duty flag)
   - Tenant / Seller authorization check via `driver_seller_authorizations` (or matching `seller_id`)
   - Compliance check: all required documents (`DL`, `RC`, `INSURANCE`, `BGC`) have `is_verified == True` and `valid_until >= current_date`
   - Workload limit: active duties strictly below `driver.max_active_duties`
2. **4-Tier Priority Engine Algorithm**:
   - Tier 1: Exact Address Familiarity: count of completed duties where destination address equals duty address (or coordinates $\le 25\text{m}$).
   - Tier 2: Customer Familiarity: count of completed duties for the order's `customer_id`.
   - Tier 3: Workload Balancing: fewest currently active duties (`ASSIGNED` or `IN_PROGRESS`).
   - Tier 4: Geographic Proximity: shortest Haversine distance from driver current position to destination.
   - Deterministic tie-breaking: `driver.created_at ASC`, `driver.id ASC`.
3. Design clean, performant SQL queries using SQLAlchemy 2.0 (avoid N+1 queries, aggregate completed duties via `func.count()`, compute Haversine formula in Python or SQL).

Write a complete, structured analysis in `/workspaces/TheTextileCare/.agents/m1_phase8_explorer_2/handoff.md` with concrete algorithm logic, query designs, and recommendations for the Worker.

## 2026-09-20T08:15:32Z
You are m1_phase8_explorer_2. Your working directory is /workspaces/TheTextileCare/.agents/m1_phase8_explorer_2.
Read your instructions in /workspaces/TheTextileCare/.agents/m1_phase8_explorer_2/DISPATCH.md, /workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md, and /workspaces/TheTextileCare/.agents/PROJECT.md.
Investigate Milestone 1 implementation strategy for Driver Eligibility Service and the 4-Tier Algorithmic Familiarity & Priority Engine.
Deliver your handoff report to /workspaces/TheTextileCare/.agents/m1_phase8_explorer_2/handoff.md and notify parent when complete.

