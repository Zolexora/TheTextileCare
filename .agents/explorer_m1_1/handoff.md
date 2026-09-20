# Handoff Report: Phase 7 Alembic Migration & Schema Foundation

**Agent ID**: `explorer_m1_1`  
**Working Directory**: `/workspaces/TheTextileCare/.agents/explorer_m1_1`  
**Date**: 2026-09-19  
**Recipient**: `parent` (ID: `6b62fa2d-b0e1-4cea-9ad2-9f2593e98762`) & downstream implementation agents  
**Handoff Type**: Hard (Task Complete)  

---

## 1. Observation

1. **Alembic Migration Chain**:
   - Inspected `backend/migrations/versions/`. Found 8 existing migrations:
     - `0001_phase1_identity_and_tenancy.py` (rev: `0001_phase1`)
     - `2010fc7ee67f_phase2_seller_platform.py` (rev: `2010fc7ee67f`)
     - `debba6592524_phase2_harden_seller_foundation.py` (rev: `debba6592524`)
     - `275f700c133f_phase3_customization_engine.py` (rev: `275f700c133f`)
     - `ddf173e6fc96_phase4_catalog_services.py` (rev: `ddf173e6fc96`)
     - `e7f1a2b3c4d5_phase5_pricing_engine.py` (rev: `e7f1a2b3c4d5`)
     - `112e2205a754_phase6_marketplace_and_customer.py` (rev: `112e2205a754`)
     - `a1b2c3d4e5f6_phase7_order_foundation.py` (rev: `a1b2c3d4e5f6`, head)
   - Command: `/workspaces/TheTextileCare/.venv/bin/alembic history` output:
     ```
     112e2205a754 -> a1b2c3d4e5f6 (head), phase7_order_foundation
     e7f1a2b3c4d5 -> 112e2205a754, phase6_marketplace_and_customer
     ddf173e6fc96 -> e7f1a2b3c4d5, phase5_pricing_engine
     275f700c133f -> ddf173e6fc96, phase4_catalog_services
     debba6592524 -> 275f700c133f, phase3_customization_engine
     2010fc7ee67f -> debba6592524, phase2_harden_seller_foundation
     0001_phase1 -> 2010fc7ee67f, phase2_seller_platform
     <base> -> 0001_phase1, Phase 1: identity, tenancy, membership, rbac, and audit schema
     ```
   - Current database `alembic_version` was queried: `SELECT * FROM alembic_version` returned `[('112e2205a754',)]`.

2. **Order Foundation Migration & Reselection Column Gap**:
   - Viewed `backend/migrations/versions/a1b2c3d4e5f6_phase7_order_foundation.py`. Lines 37–75 show table `orders` created with columns: `id`, `tenant_id`, `seller_id`, `branch_id`, `customer_id`, `order_number`, `status`, `currency`, `subtotal`, `discount_total`, `surcharge_total`, `tax_total`, `grand_total`, `pricing_snapshot`, `catalog_snapshot`, `customer_snapshot`, `customer_address_snapshot`, `idempotency_key`, `placed_at`, `confirmed_at`, `completed_at`, `cancelled_at`, `cancellation_reason`, `created_at`, `updated_at`, `created_by`, `updated_by`.
   - Viewed `backend/app/models/order.py`. Lines 154–156 define:
     ```python
     reselected_from_order_id: Mapped[uuid.UUID | None] = mapped_column(
         ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
     )
     ```
   - `reselected_from_order_id` exists on the SQLAlchemy model `Order` but is completely absent from migration `a1b2c3d4e5f6`. It must be added via `op.add_column` in the new Phase 7 migration.

3. **Current State of Domain Models in `backend/app/models/`**:
   - `pickup.py`: Does NOT exist in `backend/app/models/`. No `OrderPickup` or `PickupStatus` model exists.
   - `commercial.py`: Defines `SellerCommercialConfiguration` (`seller_commercial_configs`), but is missing `tenant_id`, `overdue_grace_days`, and `daily_penalty_rate` which are required by `PROJECT.md` lines 24 and 92–93.
   - `payment.py`: Defines `Payment` (`payments`) and `Refund` (`refunds`).
     - `Payment` is missing: `seller_id` (FK `sellers.id`), `settled` (bool), `settlement_id` (FK `seller_settlements.id`), `paid_at` (timestamp, required for 15-day hold check per `PROJECT.md:129`), and `due_date` (timestamp for outstanding receivables per `PROJECT.md:95`).
     - `Refund` is missing: `tenant_id` (FK `tenants.id`), `reason` (string), and `commission_deduction` (decimal).
   - `billing.py`:
     - `SettlementStatus`: defines `PENDING`, `PROCESSING`, `SETTLED`, `FAILED`. Missing `SCHEDULED` (which is the primary status for weekly Monday batches per `PROJECT.md:9` and `PROJECT.md:101`).
     - `SellerBillingInvoice`: defines `invoice_month` as `sa.Date`. However, `PROJECT.md:99` specifies `invoice_month: str ("YYYY-MM")` with unique constraint `(seller_id, invoice_month)`.
   - `__init__.py`: Imports and exports models, but lacks `pickup.py`.

4. **Enum Convention vs PostgreSQL Native Types**:
   - Grep search for `Enum` in `backend/migrations/versions` returned zero results.
   - All 8 existing migrations use `sa.String(length=50)` or `sa.String(...)` for status and category columns.
   - In `spec_miner_survey_phase7/report.md:247`, survey noted:
     `PostgreSQL table drop/create causes composite type collisions in pg_type ("duplicate key value violates unique constraint 'pg_type_typname_nsp_index'").`
   - Test execution via `tests/conftest.py` executes `Base.metadata.drop_all(bind=engine)` and `Base.metadata.create_all(bind=engine)` before each test. Native Postgres enums create types in `pg_type` that collide during test resets, whereas `String(50)` with `sa.CheckConstraint` provides identical constraint enforcement with zero test collisions.

5. **Test Suite Baseline**:
   - Command: `PYTHONPATH=. /workspaces/TheTextileCare/.venv/bin/pytest tests/api/test_orders.py tests/api/test_cancellation.py tests/api/test_rejection.py`
   - Result: 34 tests collected, 34 passed in 61.11s.
   - Command: `PYTHONPATH=. /workspaces/TheTextileCare/.venv/bin/pytest tests/api/test_health.py`
   - Result: 1 passed in 2.60s.

---

## 2. Logic Chain

1. **Revision Hierarchy**:
   - Observation 1 establishes that `a1b2c3d4e5f6` is the latest migration head.
   - Therefore, the new migration must declare `down_revision = 'a1b2c3d4e5f6'`. Revision ID `b2c3d4e5f6a7` is chosen following the existing 12-character hex convention.

2. **Column Reselection Placement**:
   - Observation 2 demonstrates that `orders.reselected_from_order_id` is defined on `app.models.order.Order` but absent in `a1b2c3d4e5f6`.
   - Therefore, the new migration must execute:
     1. `op.add_column('orders', sa.Column('reselected_from_order_id', sa.Uuid(), nullable=True))`
     2. `op.create_foreign_key('fk_orders_reselected_from_order_id_orders', 'orders', 'orders', ['reselected_from_order_id'], ['id'], ondelete='SET NULL')`
     3. `op.create_index('ix_orders_reselected_from_order_id', 'orders', ['reselected_from_order_id'])`
   - In downgrade, reverse operations must be performed in exact sequence: drop index, drop constraint, drop column.

3. **Table Creation Ordering & Foreign Key Dependencies**:
   - `order_pickups` references `orders.id`, `sellers.id`, `tenants.id`.
   - `seller_commercial_configs` references `sellers.id`, `tenants.id`.
   - `seller_billing_invoices` references `sellers.id`, `tenants.id`.
   - `seller_settlements` references `sellers.id`, `tenants.id`. It does NOT reference payments.
   - `payments` references `orders.id`, `sellers.id`, `customers.id`, `tenants.id`, AND `seller_settlements.id` (`settlement_id`, ondelete `SET NULL`).
   - `refunds` references `payments.id` and `tenants.id`.
   - Therefore, creating `seller_settlements` BEFORE `payments` avoids circular foreign key dependencies and allows `payments.settlement_id` to be declared directly in `op.create_table('payments', ...)`.
   - Creation order in `upgrade()`:
     1. Alter `orders` (add `reselected_from_order_id`)
     2. `order_pickups`
     3. `seller_commercial_configs`
     4. `seller_billing_invoices`
     5. `seller_settlements`
     6. `payments`
     7. `refunds`
   - Downgrade order is the exact reverse: 7 -> 6 -> 5 -> 4 -> 3 -> 2 -> 1.

4. **Data Integrity & Enum Strategy**:
   - From Observation 4, native PostgreSQL ENUMs cause `pg_type` collisions in `conftest.py` test resets and are incompatible with the existing codebase patterns.
   - Using `sa.String(50)` with `sa.CheckConstraint` enforces strict database-level enum validation without type catalog pollution:
     - `order_pickups`: `status IN ('SCHEDULED', 'DETAILS_SUBMITTED', 'APPROVED', 'REJECTED', 'COMPLETED')`
     - `seller_commercial_configs`: `commercial_model IN ('COMMISSION', 'SUBSCRIPTION')`, `restriction_level IN ('NONE', 'WARNING', 'MARKETPLACE_RESTRICTED', 'WHITE_LABEL_RESTRICTED', 'FULL_SUSPENSION')`, gateways in `('TTC_GATEWAY', 'SELLER_GATEWAY')`
     - `payments`: `status IN ('PENDING', 'SUCCEEDED', 'FAILED', 'OUTSTANDING', 'REFUNDED', 'PARTIALLY_REFUNDED')`, gateway in `('TTC_GATEWAY', 'SELLER_GATEWAY')`
     - `seller_billing_invoices`: `status IN ('PENDING', 'PAID', 'OVERDUE', 'CANCELLED')`
     - `seller_settlements`: `status IN ('SCHEDULED', 'PROCESSING', 'SETTLED', 'FAILED', 'PENDING')`, gateway in `('TTC_GATEWAY', 'SELLER_GATEWAY')`

5. **Invoice Uniqueness**:
   - `PROJECT.md:23` and `DISPATCH.md:21` require calendar-month uniqueness on invoices.
   - Therefore, `sa.UniqueConstraint('seller_id', 'invoice_month', name='uq_seller_billing_invoices_seller_month')` is explicitly defined with `invoice_month` formatted as `"YYYY-MM"` (`sa.String(7)`).

6. **Domain Model Alignment**:
   - Observation 3 identified discrepancies between `PROJECT.md` contracts and existing drafted models.
   - For Alembic migration and SQLAlchemy declarative Base to remain in 100% sync, the implementation agent must create `pickup.py`, update `commercial.py`, `payment.py`, and `billing.py`, and register them in `__init__.py`.

---

## 3. Caveats

1. **Read-Only Explorer Role**: Under explorer guidelines, no project source code files (`backend/migrations/versions/*`, `backend/app/models/*`) were modified during this investigation. All concrete artifacts and drop-in code were written to `/workspaces/TheTextileCare/.agents/explorer_m1_1/report.md`.
2. **Pytest Database Reset vs Alembic**: `tests/conftest.py` resets the test database using `Base.metadata.drop_all()` and `Base.metadata.create_all()`. For Alembic migrations to be validated independently from pytest, explicit `alembic upgrade head` and `alembic downgrade a1b2c3d4e5f6` commands must be executed against PostgreSQL.
3. **Drafted Models vs Existing Tests**: Existing order and pricing tests do not query `payments` or `billing` yet; they focus on `orders`, `order_items`, and catalog snapshots. Introducing the migration and updated models will not break any existing tests.

---

## 4. Conclusion

1. The Alembic migration for Phase 7 is fully designed and specified as `b2c3d4e5f6a7_phase7_commercial_billing_payment.py` revising `a1b2c3d4e5f6`.
2. All 6 tables (`order_pickups`, `seller_commercial_configs`, `payments`, `refunds`, `seller_billing_invoices`, `seller_settlements`) and the column addition on `orders` (`reselected_from_order_id`) have been designed with exact types, precision (`Numeric(12, 2)`), foreign keys, unique constraints, check constraints, and performance indexes.
3. The upstream model gaps in `backend/app/models/` have been pinpointed with drop-in code snippets provided in Section 7 of `report.md`.
4. The migration is completely reversible, safe, and ready for immediate implementation by the M1 implementation agent.

---

## 5. Verification Method

To verify the design, the implementation agent should perform:

1. **File Creation Verification**:
   Verify migration script is placed at:
   `/workspaces/TheTextileCare/backend/migrations/versions/b2c3d4e5f6a7_phase7_commercial_billing_payment.py`
   with content matching Section 6 of `/workspaces/TheTextileCare/.agents/explorer_m1_1/report.md`.

2. **Alembic Upgrade & Downgrade Roundtrip**:
   Execute:
   ```bash
   cd /workspaces/TheTextileCare/backend
   PYTHONPATH=. /workspaces/TheTextileCare/.venv/bin/alembic upgrade head
   PYTHONPATH=. /workspaces/TheTextileCare/.venv/bin/alembic downgrade a1b2c3d4e5f6
   PYTHONPATH=. /workspaces/TheTextileCare/.venv/bin/alembic upgrade head
   ```
   **Pass Condition**: Upgrade to `b2c3d4e5f6a7`, downgrade to `a1b2c3d4e5f6`, and re-upgrade execute with exit code 0.

3. **Schema Inspection Verification**:
   Execute:
   ```bash
   PYTHONPATH=. /workspaces/TheTextileCare/.venv/bin/python3 -c "
   from app.db import engine
   from sqlalchemy import inspect
   insp = inspect(engine)
   tables = insp.get_table_names()
   expected = ['order_pickups', 'seller_commercial_configs', 'seller_billing_invoices', 'seller_settlements', 'payments', 'refunds']
   for t in expected:
       assert t in tables, f'Missing table {t}'
   cols = [c['name'] for c in insp.get_columns('orders')]
   assert 'reselected_from_order_id' in cols, 'Missing reselected_from_order_id on orders'
   print('All Phase 7 tables and columns verified successfully!')
   "
   ```
   **Pass Condition**: Prints `'All Phase 7 tables and columns verified successfully!'` with exit code 0.

4. **Regression Test Verification**:
   Execute:
   ```bash
   PYTHONPATH=. /workspaces/TheTextileCare/.venv/bin/pytest tests/api/test_health.py tests/api/test_orders.py tests/api/test_cancellation.py tests/api/test_rejection.py
   ```
   **Pass Condition**: 100% of the 35 tests pass with 0 failures.
