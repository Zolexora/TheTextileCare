# Handoff Report: Phase 7 RBAC Permissions, Test Fixtures & Multi-Tenant Repositories

**Agent**: Milestone 1 Explorer 3 (`explorer_m1_3`)  
**Target Milestone**: Phase 7 Milestone 1 — Database Migration, Domain Models & RBAC Foundation  
**Working Directory**: `/workspaces/TheTextileCare/.agents/explorer_m1_3`  
**Handoff Type**: Hard (Task Complete)  
**Date**: 2026-09-19  

---

## 1. Observation

Direct observations from codebase inspection:

1. **Permissions & Roles State (`backend/app/core/permissions/constants.py`)**:
   - Lines 62-72:
     ```python
     # Phase 5 Pricing Permissions
     PRICING_READ = 'pricing.read'
     PRICING_MANAGE = 'pricing.manage'

     # Phase 7 Order Permissions
     ORDER_READ = 'order.read'
     ORDER_MANAGE = 'order.manage'
     ORDER_CONFIRM = 'order.confirm'
     ORDER_PROCESS = 'order.process'
     ORDER_CANCEL = 'order.cancel'
     ```
     Phase 7 permissions for commercial (`commercial.read`, `commercial.manage`), payments (`payment.read`, `payment.process`), billing (`billing.read`, `billing.manage`), and settlements (`settlement.read`, `settlement.process`) are currently missing.
   - Lines 6-19:
     ```python
     class RoleName(str, Enum):
         PLATFORM_ADMIN = 'PLATFORM_ADMIN'
         PLATFORM_SUPPORT = 'PLATFORM_SUPPORT'
         TENANT_OWNER = 'TENANT_OWNER'
         TENANT_ADMIN = 'TENANT_ADMIN'
         TENANT_MEMBER = 'TENANT_MEMBER'
         TENANT_VIEWER = 'TENANT_VIEWER'
         SELLER_OWNER = 'SELLER_OWNER'
         SELLER_ADMIN = 'SELLER_ADMIN'
         STAFF = 'STAFF'
         VIEWER = 'VIEWER'
     ```
     `CUSTOMER` is not yet represented in `RoleName` despite retail customer interactions requiring authentication and role-governed actions.

2. **Role Descriptions & Seeding (`backend/app/services/roles.py`)**:
   - Lines 15-26 & 28-70:
     `ROLE_DESCRIPTIONS` and `PERMISSION_DESCRIPTIONS` define descriptions for default roles and permissions.
   - Lines 78-105:
     ```python
     def seed_defaults(self) -> None:
         # 1. Seed Permissions from PERMISSION_DESCRIPTIONS
         # 2. Seed Roles and Mappings from DEFAULT_ROLE_PERMISSIONS
     ```
     Every entry in `DEFAULT_ROLE_PERMISSIONS` and `PERMISSION_DESCRIPTIONS` is seeded idempotently on every test run.

3. **Test Fixtures & Database Reset (`backend/tests/conftest.py`)**:
   - Lines 6-25:
     ```python
     import pytest
     import app.models  # noqa: F401
     from app.db import Base, SessionLocal, engine
     ...
     @pytest.fixture(autouse=True)
     def reset_database():
         Base.metadata.drop_all(bind=engine)
         Base.metadata.create_all(bind=engine)
         with SessionLocal() as db:
             RoleService(db).seed_defaults()
         yield
     ```
     The test runner drops and re-creates all tables registered under `Base.metadata` via `import app.models`.

4. **Model Export State (`backend/app/models/__init__.py`)**:
   - Lines 33-36:
     ```python
     from app.models.commercial import PaymentGatewayType, SellerCommercialModel, SellerRestrictionLevel, SellerCommercialConfiguration
     from app.models.payment import PaymentStatus, Payment, Refund
     from app.models.billing import InvoiceStatus, SellerBillingInvoice, SettlementStatus, SellerSettlement
     ```
     `OrderPickup` and `PickupStatus` are not imported or exported in `__init__.py`. As a result, `reset_database` will fail to create the `order_pickups` table until `app.models.pickup` is imported.

5. **Repository Architecture Pattern (`backend/app/repositories/base.py` & `order.py`)**:
   - `backend/app/repositories/base.py:6-8`:
     ```python
     class BaseRepository:
         def __init__(self, db: Session) -> None:
             self.db = db
     ```
   - `backend/app/repositories/order.py:108-160`:
     All database access methods use SQLAlchemy 2.0 `select(...)`, apply `flush()` on write (never calling `commit()`), strictly filter on `tenant_id` and `seller_id`, and return `tuple[Sequence[Model], int]` for paginated listings.

---

## 2. Logic Chain

1. **From Observation 1 to Permission Design**:
   Because Phase 7 introduces commercial agreements, payment processing post-pickup approval, monthly seller billing, and weekly Monday settlement batches, 8 fine-grained permissions (`commercial.read`, `commercial.manage`, `payment.read`, `payment.process`, `billing.read`, `billing.manage`, `settlement.read`, `settlement.process`) must be added to `PermissionName`.
2. **From Observation 1 & 2 to Role & Matrix Design**:
   Because `RoleService.seed_defaults()` relies on `DEFAULT_ROLE_PERMISSIONS` to populate the database, `RoleName` is extended with `CUSTOMER = 'CUSTOMER'`. Under least-privilege principles:
   - `PLATFORM_ADMIN` receives all 8 permissions.
   - `PLATFORM_SUPPORT` receives all 4 read permissions (`commercial.read`, `payment.read`, `billing.read`, `settlement.read`).
   - `TENANT_OWNER`, `TENANT_ADMIN`, `SELLER_OWNER`, `SELLER_ADMIN` receive `commercial.read`, `commercial.manage`, `payment.read`, `payment.process`, `billing.read`, and `settlement.read`.
   - `SETTLEMENT_PROCESS` is strictly withheld from seller and tenant roles, reserved exclusively for `PLATFORM_ADMIN` to prevent merchants from executing self-disbursements.
   - `CUSTOMER` receives only `payment.read` and `payment.process` (along with `order.read` and `order.cancel`), completely denying visibility into seller commercial configurations or billing invoices.
3. **From Observation 3 & 4 to Test Fixture Registration**:
   Because `conftest.py:reset_database` issues `Base.metadata.create_all(bind=engine)`, any model not imported during `import app.models` will not have its table created. Therefore, `app/models/__init__.py` must import `OrderPickup` and `PickupStatus` from `app.models.pickup`. Adding standardized Phase 7 fixture helpers (`create_test_commercial_config`, `create_test_pickup`, `create_test_payment`, `create_test_billing_invoice`, `create_test_settlement`) into `conftest.py` ensures seamless test execution across all subsequent milestones.
4. **From Observation 5 to Multi-Tenant Repository Blueprints**:
   Because `BaseRepository` establishes the standard session-injected pattern, all 5 Phase 7 repositories (`CommercialRepository`, `PickupRepository`, `PaymentRepository`, `BillingRepository`, `SettlementRepository`) extend `BaseRepository`. By enforcing `Model.tenant_id == tenant_id` and `Model.seller_id == seller_id` on all queries, cross-tenant data access returns `None`, shielding the application against ID injection and enumeration attacks.

---

## 3. Caveats

1. **Model Synchronization**:
   Explorer M1.2 is finalizing the model attributes for `OrderPickup` (`backend/app/models/pickup.py`) and refining `SellerCommercialConfiguration`, `Payment`, `Refund`, `SellerBillingInvoice`, and `SellerSettlement`. The repository specifications in `report.md` use the standardized field names defined in `PROJECT.md:88-104`. If Explorer M1.2 introduces any field name variants (e.g. `is_settled` vs `settled`), the repository column mappings should be aligned accordingly.
2. **Alembic Migration Dependency**:
   In test environments, `conftest.py:reset_database()` runs `Base.metadata.create_all(bind=engine)` which constructs tables directly from ORM models. However, for production and migration tests, the Alembic migration script designed by Explorer M1.1 (`<rev>_phase7_commercial_billing_payment.py`) must be executed.
3. **Sequential Test Runner Requirement**:
   As identified in `spec_miner_survey_phase7/report.md:275`, tests must run sequentially without `-n` parallel workers to avoid PostgreSQL `pg_type` composite type collision during concurrent `reset_database` executions.

---

## 4. Conclusion

A complete, production-ready implementation blueprint for Phase 7 RBAC permissions, role descriptions, test fixture registration, and 5 multi-tenant repositories has been delivered in `/workspaces/TheTextileCare/.agents/explorer_m1_3/report.md`.

Key Deliverables:
- Exact code additions for `backend/app/core/permissions/constants.py` (8 permissions, `RoleName.CUSTOMER`, full `DEFAULT_ROLE_PERMISSIONS` matrix).
- Exact dictionary updates for `backend/app/services/roles.py` (`ROLE_DESCRIPTIONS`, `PERMISSION_DESCRIPTIONS`).
- Model import requirements in `backend/app/models/__init__.py` and Phase 7 test fixtures for `backend/tests/conftest.py`.
- Complete drop-in code implementations for `CommercialRepository`, `PickupRepository`, `PaymentRepository`, `BillingRepository`, and `SettlementRepository` with strict `tenant_id` scoping and defense-in-depth isolation.

---

## 5. Verification Method

To independently verify the blueprint once implemented by Implementer M1:

1. **Syntax and Static Compilation**:
   ```bash
   cd /workspaces/TheTextileCare/backend
   python -m py_compile app/core/permissions/constants.py
   python -m py_compile app/services/roles.py
   python -m py_compile app/repositories/commercial.py
   python -m py_compile app/repositories/pickup.py
   python -m py_compile app/repositories/payment.py
   python -m py_compile app/repositories/billing.py
   python -m py_compile app/repositories/settlement.py
   ```
2. **Database Reset & Role Seeding Verification**:
   Verify that running a test seeds all 8 new permissions and the `CUSTOMER` role:
   ```bash
   cd /workspaces/TheTextileCare/backend
   .venv/bin/pytest tests/api/test_health.py -k test_health
   ```
   Inspect seeded database records:
   ```bash
   python -c "
   from app.db import SessionLocal
   from app.models.permission import Permission
   from app.models.role import Role
   with SessionLocal() as db:
       perms = [p.name for p in db.query(Permission).all()]
       assert 'commercial.read' in perms
       assert 'payment.process' in perms
       assert 'billing.manage' in perms
       assert 'settlement.process' in perms
       roles = [r.name for r in db.query(Role).all()]
       assert 'CUSTOMER' in roles
       print('Verification SUCCESS: All Phase 7 permissions and roles seeded.')
   "
   ```
3. **Repository Multi-Tenant Isolation Tests**:
   - `CommercialRepository`: Query config for `seller_a` with `tenant_b` ID -> Must return `None`.
   - `PickupRepository`: Query pickup for `order_a` with `tenant_b` ID -> Must return `None`.
   - `PaymentRepository`: Query eligible cooling payments for `seller_a` -> Must not return payments belonging to `seller_b`.
   - `BillingRepository`: Query invoice for `seller_a` in month `2026-09-01` -> Idempotent lookup prevents duplicate billing.
   - `SettlementRepository`: Query settlements for `seller_a` with `tenant_b` ID -> Must return `None`.
4. **Full Test Suite Regression Run**:
   ```bash
   cd /workspaces/TheTextileCare/backend
   .venv/bin/pytest tests/api/test_orders.py tests/api/test_cancellation.py tests/api/test_rejection.py
   ```
