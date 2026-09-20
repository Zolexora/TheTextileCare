# Task Assignment: Implementer M1 — Database Migration, Domain Models & RBAC Foundation

## Working Directory
`/workspaces/TheTextileCare/.agents/worker_m1_1`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## Authoritative Context & Input Reports
Read:
- `/workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md` (specifically `## 2026-09-19T17:49:20Z`)
- `/workspaces/TheTextileCare/.agents/PROJECT.md` (specifically Milestone 1, Architecture, and Interface Contracts)
- Explorer Reports:
  - Migration & DDL: `/workspaces/TheTextileCare/.agents/explorer_m1_1/report.md`
  - Models & Schemas: `/workspaces/TheTextileCare/.agents/explorer_m1_2/report.md`
  - RBAC & Repositories: `/workspaces/TheTextileCare/.agents/explorer_m1_3/report.md`

## Scope & File Ownership
You exclusively own and must implement:
1. `backend/migrations/versions/b2c3d4e5f6a7_phase7_commercial_billing_payment.py`
   - Down revision: `a1b2c3d4e5f6`
   - Alter `orders` (add `reselected_from_order_id`, FK to `orders.id` SET NULL, indexed)
   - Tables: `order_pickups`, `seller_commercial_configs`, `seller_billing_invoices`, `seller_settlements`, `payments`, `refunds`
   - Enforce check constraints, foreign keys, unique constraint `(seller_id, invoice_month)` on invoices, and indexes per `explorer_m1_1/report.md`.
2. `backend/app/models/`:
   - `pickup.py`: `OrderPickup`, `PickupStatus` (`SCHEDULED`, `DETAILS_SUBMITTED`, `APPROVED`, `REJECTED`, `COMPLETED`)
   - `commercial.py`: `SellerCommercialConfiguration`, enums, adding `tenant_id`, penalty parameters, grace days, overdue thresholds
   - `payment.py`: `Payment`, `Refund`, enums, adding `seller_id`, `settled`, `settlement_id`, `paid_at`, `due_date`, `commission_deduction`
   - `billing.py`: `SellerBillingInvoice`, `SellerSettlement`, enums (including `SettlementStatus.SCHEDULED`), `UniqueConstraint("seller_id", "invoice_month")`
   - `order.py`: add relationships `reselected_from_order`, `pickup`, `payment`
   - `__init__.py`: export all models
3. `backend/app/schemas/`:
   - `pickup.py`: Pydantic v2 schemas for pickups
   - `commercial.py`: Pydantic v2 schemas for commercial configs (with mutual exclusivity validator)
   - `payment.py`: Pydantic v2 schemas for payments and refunds (with separate fee/tax ledger)
   - `billing.py`: Pydantic v2 schemas for invoices and penalties (with YYYY-MM validation)
   - `settlement.py`: Pydantic v2 schemas for settlements
   - `order.py`: add `OrderReselectRequest`
4. `backend/app/core/permissions/constants.py` & `backend/app/services/roles.py`:
   - Add 8 Phase 7 permissions, `RoleName.CUSTOMER`, `DEFAULT_ROLE_PERMISSIONS` matrix, `ROLE_DESCRIPTIONS`, and `PERMISSION_DESCRIPTIONS` per `explorer_m1_3/report.md`.
5. `backend/app/repositories/`:
   - `pickup.py` (`PickupRepository`)
   - `commercial.py` (`CommercialRepository`)
   - `payment.py` (`PaymentRepository`)
   - `billing.py` (`BillingRepository`)
   - `settlement.py` (`SettlementRepository`)
   - Multi-tenant query scoping via `tenant_id`, `flush()` on writes, no `commit()`.
6. `backend/tests/`:
   - `tests/conftest.py`: update model imports and add fixture helpers.
   - `tests/unit/test_phase7_models_schemas.py`: verify models, constraints, and schemas.
   - `tests/unit/test_phase7_repositories.py`: verify multi-tenant isolation across all 5 repositories.

## Verification Requirements
Before delivering your handoff, you MUST execute and document:
1. `alembic upgrade head` succeeds.
2. `alembic downgrade a1b2c3d4e5f6` and re-upgrade `alembic upgrade head` succeed.
3. `pytest tests/unit/test_phase7_*.py` passes with 100%.
4. Existing test suite passes with 0 regressions: `pytest tests/api/test_orders.py tests/api/test_cancellation.py tests/api/test_rejection.py tests/api/test_health.py`.
5. Code compilation passes without syntax or import errors: `python -m py_compile backend/app/models/*.py backend/app/schemas/*.py backend/app/repositories/*.py`.

Deliver your handoff report to `/workspaces/TheTextileCare/.agents/worker_m1_1/handoff.md`.
Keep `progress.md` updated. When complete, send a message to your caller.

## 2026-09-19T18:06:18Z
Task invoked by user/parent:
Implement Phase 7 Database Migration, Domain Models, Schemas, RBAC, Repositories, and Unit Tests per explorer reports.
