# Handoff Report: TTC Phase 5 Pricing Engine Foundation Specification

**Agent**: `teamwork_preview_spec_miner` (Specification Miner)  
**Date**: 2026-09-19  
**Target Milestone**: Phase 5 — Pricing Engine Foundation  
**Deliverable Document**: `/workspaces/TheTextileCare/.agents/spec_miner_survey_1/survey_requirements.md`  

---

## 1. Observation

1. **User Requirements & Phase 5 Objectives**:
   In `/workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md` (header `## 2026-09-19T04:33:52Z` lines 35-88), the user prompt requests implementing the **Pricing Engine Foundation** as a reusable, deterministic, tenant-isolated pricing domain answering "How much does it cost?", structurally separated from the catalog ("What is being offered?"). Requirements R1-R5 mandate:
   - R1: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL psycopg3, modular monolith, tenant isolation, RBAC. No microservices, Kafka, EAV tables, or rewrites of Phase 1-4 migrations.
   - R2: `price_books` and `price_rules` referencing Phase 4 catalog items without duplicating data; rule types `FIXED`, `PER_ITEM`, `PER_UNIT`, `PER_WEIGHT`; 4-tier breakdown (`Base Price`, `Surcharge`, `Discount`, `Tax`) using `Decimal` calculations exclusively.
   - R3: Deterministic calculation algorithm resolving precedence (`Platform Default → Seller → Branch → Rule`), enforcing `effective_from`/`effective_to`, applying surcharges/discounts/taxes, validating tenant/seller/branch, returning breakdown without order persistence.
   - R4: Strict tenant isolation via `TenantContext`, prevention of cross-tenant ID injection, granular permissions `pricing.read` and `pricing.manage`, and `AuditService` lifecycle events.
   - R5: REST endpoints under `/api/v1/pricing/`, shared TypeScript types in `@ttc/types` (`packages/types`), and minimal pricing management foundation in `apps/seller-web`.

2. **Catalog Domain Architecture**:
   Inspection of `backend/app/models/catalog.py` (lines 1-157) confirms that Catalog entities (`catalogs`, `catalog_categories`, `services`, `service_items`, `service_addons`, `service_branch_availability`) contain **zero price or currency fields**. Pricing is completely separated.

3. **Current Alembic Revision**:
   Inspection of `backend/migrations/versions/ddf173e6fc96_phase4_catalog_services.py` (lines 15-16) confirms that the current Alembic revision head is `ddf173e6fc96`. Any new Phase 5 migration must specify `down_revision = 'ddf173e6fc96'`.

4. **RBAC Seed & Role Matrix**:
   Inspection of `backend/app/core/permissions/constants.py` (lines 21-62 and 80-334) and `backend/app/services/roles.py` (lines 28-63) confirms how permissions and roles are declared and mapped. `test_seed_creates_all_expected_roles_and_permissions` in `backend/tests/unit/test_rbac_seed.py` (lines 19-35) requires that every enum in `PermissionName` is described in `PERMISSION_DESCRIPTIONS` and correctly mapped in `DEFAULT_ROLE_PERMISSIONS`.

5. **Test Fixture Discovery (`conftest.py`)**:
   During test suite execution (`.venv/bin/pytest backend/tests`), tests initially failed with `psycopg.errors.UndefinedTable: relation "role_permissions" does not exist`. Direct inspection of `backend/tests/conftest.py` revealed that `conftest.py` only imported `Membership`, `Tenant`, and `User`, omitting `import app.models`. When tested via python with `import app.models` pre-loaded, `Base.metadata.create_all()` successfully created all 22 platform tables, and 48 tests passed.

6. **Monorepo Build State**:
   Running `pnpm typecheck` executed cleanly across all 13 monorepo packages (`@ttc/admin-web`, `@ttc/api-client`, `@ttc/auth`, `@ttc/branding`, `@ttc/config`, `@ttc/driver-mobile`, `@ttc/marketplace-mobile`, `@ttc/marketplace-web`, `@ttc/seller-mobile`, `@ttc/seller-web`, `@ttc/tenant`, `@ttc/types`, `@ttc/ui`) with 0 errors.

---

## 2. Logic Chain

1. **Isolation of Pricing and Catalog**:
   From Observation 2, catalog tables have no price fields. To satisfy R2 and R3 without violating catalog domain integrity, `price_rules` must use foreign keys `service_id`, `service_item_id`, and `service_addon_id` (all nullable, pointing to the catalog tables) to establish rates without schema alterations to catalog tables.

2. **Precedence Engine Determinism**:
   From Observation 1 (R3), the hierarchy `Platform Default → Seller → Branch → Rule` means that price resolution must query the most specific active `PriceBook` first (Branch, then Seller, then Platform default), and within that book pick the most specific active `PriceRule` (Item-specific > Service-specific > Addon-specific, ordered by descending `priority`).

3. **Mathematical Invariant & Precision**:
   From Observation 1 (R2, R3), all monetary arithmetic must use Python `Decimal` to avoid floating-point drift. The system must strictly enforce:
   $$\text{grand\_total} \equiv \text{subtotal} + \text{total\_surcharges} - \text{total\_discounts} + \text{total\_tax}$$
   and round to 2 decimal places using `ROUND_HALF_UP` for currency representations.

4. **Security & Permissions**:
   From Observation 1 and 4, adding `PermissionName.PRICING_READ = 'pricing.read'` and `PermissionName.PRICING_MANAGE = 'pricing.manage'` and updating `PERMISSION_DESCRIPTIONS` allows mapping `pricing.manage` to `PLATFORM_ADMIN`, `TENANT_OWNER`, `TENANT_ADMIN`, `SELLER_OWNER`, and `SELLER_ADMIN`, while denying it to `VIEWER` and `STAFF`, satisfying the least-privilege acceptance criteria.

5. **Test Stability Dependency**:
   From Observation 5, when new pricing models (`PriceBook`, `PriceRule`) are created in `backend/app/models/pricing.py`, they must be imported in `backend/app/models/__init__.py`. In addition, `backend/tests/conftest.py` must import `import app.models` so that `Base.metadata.create_all()` always registers and creates the complete table schema before tests run.

---

## 3. Caveats

1. **PostgreSQL Concurrent Connection Locks in Tests**: Running the entire test suite sequentially with `drop_all` / `create_all` per test can occasionally hit table lock contention if uncommitted transactions from preceding tests are not closed. The test suite runner should ensure proper session closing or transaction rollback.
2. **Coupon / Promotion Engine**: While discounts are supported as a core component type in `PriceRule`, complex voucher tracking, coupon code redemption limits, and user-specific usage counters belong to a future marketing/promotion phase. For Phase 5, discount rules operate via standard `PriceRule` matching.

---

## 4. Conclusion

The specification extraction for **TTC Phase 5: Pricing Engine Foundation** is complete, highly detailed, and fully verified against existing codebase patterns. 

All specifications are delivered in `/workspaces/TheTextileCare/.agents/spec_miner_survey_1/survey_requirements.md`, detailing:
1. Requirements Traceability Matrix for R1-R5.
2. Entity models for `PriceBook` and `PriceRule` with column definitions, enums, indexes, and foreign keys.
3. Precedence hierarchy and resolution algorithm (`Platform Default → Seller → Branch → Rule`).
4. Strict `Decimal` arithmetic formulas and 4-tier normalized breakdown invariants.
5. Security constraints, RBAC permission seed definitions, and `AuditService` event types.
6. Complete REST API contract under `/api/v1/pricing/` including `/api/v1/pricing/calculate`.
7. TypeScript interfaces for `@ttc/types` and seller-web UI integration strategy.
8. Discovered Features (21 items) and Edge Cases (12 items) tables.

---

## 5. Verification Method

To verify the findings and specifications in this report:

1. **Review Specification Report**:
   Inspect `/workspaces/TheTextileCare/.agents/spec_miner_survey_1/survey_requirements.md` to confirm all R1-R5 requirements, schemas, formulas, tables, and interfaces.

2. **Verify Monorepo TypeScript Health**:
   ```bash
   pnpm typecheck
   ```
   Must pass with 10/10 tasks successful.

3. **Verify Existing Catalog & Model Metadata**:
   ```bash
   .venv/bin/python -c "from app.db import Base; import app.models; print(len(Base.metadata.tables))"
   ```
   Must output `22`, confirming all existing Phase 1-4 tables are present.

4. **Verify Existing Tests**:
   ```bash
   cd /workspaces/TheTextileCare/backend && ../.venv/bin/python -c "import app.models; import pytest; exit(pytest.main(['tests/api/test_catalog.py']))"
   ```
   Must output `3 passed in tests/api/test_catalog.py`.
