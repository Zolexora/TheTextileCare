# Dispatch Task: Milestone 1 Worker — Driver Domain Foundation, Compliance & Priority Engine

## Working Directory
`/workspaces/TheTextileCare/.agents/m1_phase8_worker_1`

## Role & Mission
You are the implementation Worker for Milestone 1: Driver Domain Foundation, Compliance & Priority Engine.
Your parent is Project Orchestrator (`orchestrator_3`).

## Mandatory Integrity Warning
> DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Inputs to Read Before Starting
1. `/workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md` (specifically `## 2026-09-20T08:01:28Z`)
2. `/workspaces/TheTextileCare/.agents/PROJECT.md` (Milestone 1, Interface Contracts, Code Layout)
3. Explorer Handoff Reports:
   - `/workspaces/TheTextileCare/.agents/m1_phase8_explorer_1/handoff.md` (Schema, Alembic migration, models, schemas, RBAC)
   - `/workspaces/TheTextileCare/.agents/m1_phase8_explorer_2/handoff.md` (Eligibility service & 4-tier priority engine)
   - `/workspaces/TheTextileCare/.agents/m1_phase8_explorer_3/handoff.md` (REST APIs & unit test blueprints)

## Write Ownership (Exclusively Owned Files)
You own and may create/edit these files:
- `backend/migrations/versions/c3d4e5f6a7b8_phase8_driver_domain.py`
- `backend/app/models/driver.py`
- `backend/app/models/__init__.py`
- `backend/app/schemas/driver.py`
- `backend/app/core/permissions/constants.py`
- `backend/app/services/roles.py`
- `backend/app/services/driver.py`
- `backend/app/services/priority_engine.py`
- `backend/app/api/v1/driver.py`
- `backend/app/api/router.py`
- `backend/tests/unit/test_driver_eligibility.py`
- `backend/tests/unit/test_driver_priority_engine.py`

## Detailed Implementation Tasks
1. **RBAC & Role Seeding**:
   - In `backend/app/core/permissions/constants.py`:
     - Add `RoleName.DRIVER = "DRIVER"`
     - Add `PermissionName.DRIVER_MANAGE = "driver.manage"`
     - Add `PermissionName.DRIVER_VIEW = "driver.view"`
     - Add `PermissionName.DUTY_MANAGE = "duty.manage"`
     - Add `PermissionName.DUTY_VIEW = "duty.view"`
     - Add `PermissionName.DUTY_REASSIGN = "duty.reassign"`
     - Add `PermissionName.OPERATIONS_ALERT_VIEW = "operations_alert.view"`
     - Update `DEFAULT_ROLE_PERMISSIONS` to map these permissions across `PLATFORM_ADMIN`, `TENANT_OWNER`, `TENANT_ADMIN`, `SELLER_OWNER`, `SELLER_ADMIN`, `STAFF`, `VIEWER`, and `DRIVER`.
   - In `backend/app/services/roles.py`:
     - Add `RoleName.DRIVER` to `ROLE_DESCRIPTIONS`
     - Add all new permissions to `PERMISSION_DESCRIPTIONS`
2. **Database Models & Alembic Migration**:
   - Create `backend/migrations/versions/c3d4e5f6a7b8_phase8_driver_domain.py` with `down_revision = 'b2c3d4e5f6a7'`.
   - Implement tables: `drivers`, `driver_vehicles`, `driver_seller_authorizations`, and `driver_compliance_documents` with all required columns, foreign keys, indexes, and unique constraints.
   - Implement SQLAlchemy 2.0 models in `backend/app/models/driver.py`:
     - `Driver`, `DriverVehicle`, `DriverSellerAuthorization`, `DriverComplianceDocument`
     - Enums: `DriverStatus`, `DriverAvailabilityStatus`, `ComplianceDocumentType`, `VehicleType`.
   - Register models in `backend/app/models/__init__.py`.
3. **Pydantic Schemas**:
   - In `backend/app/schemas/driver.py`: define request/response schemas for onboarding, updating shifts, vehicle attributes, compliance documents, and customer-facing driver details (with unmasked phone number).
4. **Services**:
   - In `backend/app/services/driver.py`:
     - `DriverService`: CRUD operations, onboarding, shift status management, compliance verification.
     - `DriverEligibilityService`: strict binary gate evaluation (`status == ACTIVE`, `is_on_duty == True`, `availability_status == AVAILABLE`, valid non-expired verified compliance for `DL`, `RC`, `INSURANCE`, `BGC`, seller authorization, `active_duties < max_active_duties`).
   - In `backend/app/services/priority_engine.py`:
     - `PriorityResolutionEngine`: deterministic 4-tier lexicographical ranking:
       $$\text{Exact Address Familiarity} \succ \text{Customer Familiarity} \succ \text{Workload Balancing} \succ \text{Geographic Proximity}$$
       Tie-break by seniority (`created_at ASC`) and `id ASC`.
5. **REST Endpoints**:
   - In `backend/app/api/v1/driver.py`:
     - `platform_router`: `/api/v1/platform/drivers` (onboard, list, get, verify compliance).
     - `seller_router`: `/api/v1/seller/drivers` (list seller drivers, update shift/availability, assign branch).
   - In `backend/app/api/router.py`: mount both routers.
6. **Verification & Tests**:
   - Implement comprehensive unit tests in:
     - `backend/tests/unit/test_driver_eligibility.py`
     - `backend/tests/unit/test_driver_priority_engine.py`
   - Run verification commands:
     - `PYTHONPATH=. alembic upgrade head`
     - `pytest backend/tests/unit/test_driver_eligibility.py backend/tests/unit/test_driver_priority_engine.py backend/tests/unit/test_rbac_seed.py -v`
     - `ruff check app`
   - Ensure all existing unit tests and new tests pass cleanly with zero errors.

## Output Requirements
Write a complete, structured report to `/workspaces/TheTextileCare/.agents/m1_phase8_worker_1/handoff.md` detailing:
- Files modified/created
- Migration verification output (`alembic upgrade head`)
- Test commands and passing results
- Linters and code verification results
Notify parent via `send_message` when done.

## 2026-09-20T08:19:26Z
Implement Milestone 1: Driver domain migration, models, schemas, RBAC permissions, eligibility service, 4-tier priority engine, REST APIs, and unit tests. Run migrations and tests to verify.
Deliver your handoff report to /workspaces/TheTextileCare/.agents/m1_phase8_worker_1/handoff.md and notify parent when done.

