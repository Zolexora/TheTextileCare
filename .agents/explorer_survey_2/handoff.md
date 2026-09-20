# Handoff Report: Backend Architecture Survey for TTC Phase 5 Pricing Engine Foundation

**Explorer**: Backend Architecture Explorer (`explorer_survey_2`)  
**Target Repository**: `/workspaces/TheTextileCare`  
**Working Directory**: `/workspaces/TheTextileCare/.agents/explorer_survey_2`  
**Associated Survey Document**: `/workspaces/TheTextileCare/.agents/explorer_survey_2/survey_backend.md`  

---

## 1. Observation

Direct observations from the codebase investigation:

1. **FastAPI Entrypoint & Routing**:
   - `backend/app/main.py` lines 14-33 sets up FastAPI with `CORSMiddleware`, `SecurityHeadersMiddleware`, and `add_request_id` (`X-Request-Id`).
   - `backend/app/api/router.py` lines 17-25 mounts all v1 routers with `prefix='/api/v1'`, including `catalog_router` at `/api/v1/catalog`.
   - `backend/app/db.py` lines 12-25 defines SQLAlchemy 2 `DeclarativeBase` as `Base`, initializes `SessionLocal`, and provides `get_db()`.

2. **Tenant Isolation & Security**:
   - `backend/app/core/tenant/resolver.py` lines 49-125 resolves `TenantContext` using the `X-Tenant-Id` header and validates membership via `MembershipRepository.get_by_tenant_and_user`. Unaffiliated non-platform requests raise `ApiError(status_code=403, code='ACCESS_DENIED')`.
   - `backend/app/repositories/catalog.py` lines 11-23 enforces `where(Catalog.tenant_id == tenant_id)` on all queries.
   - `backend/app/services/catalog.py` lines 45-47 validates foreign references against the authenticated tenant:
     `seller = self.db.query(Seller).filter(Seller.id == data.seller_id, Seller.tenant_id == tenant_id).first()`
     raising 404 if a caller supplies an entity ID belonging to another tenant.

3. **Authentication & RBAC**:
   - `backend/app/core/permissions/constants.py` defines `RoleName` (lines 6-19), `PermissionName` (lines 21-61), and `DEFAULT_ROLE_PERMISSIONS` (lines 80-334).
   - `backend/app/services/roles.py` lines 28-63 defines `PERMISSION_DESCRIPTIONS` and `seed_defaults()` which synchronizes permissions to roles.
   - `backend/tests/unit/test_rbac_seed.py` lines 27-28 explicitly asserts:
     ```python
     perms = {p.name: p for p in db.query(Permission).all()}
     assert set(perms.keys()) == {p.value for p in PermissionName}
     ```
     Any new permission in `PermissionName` must have a description in `PERMISSION_DESCRIPTIONS` or this test will fail.

4. **Phase 4 Catalog Domain**:
   - `backend/app/models/catalog.py` defines `Catalog`, `Category`, `Service`, `ServiceItem`, `ServiceAddon`, and `ServiceBranchAvailability`.
   - Verified: **Zero** pricing, cost, amount, fee, or discount columns exist on catalog tables. Catalog models represent only "What is being offered".

5. **AuditService**:
   - `backend/app/models/audit.py` lines 17-37 defines `AuditEvent` with `tenant_id`, `actor_user_id`, `event_type`, `entity_type`, `entity_id`, and `payload` (JSON).
   - `backend/app/services/audit.py` lines 12-33 provides `AuditService.log_event(...)`.
   - `backend/app/services/catalog.py` line 64 demonstrates standard event emission:
     `self.audit_service.log_event(event_type="CATALOG_CREATED", tenant_id=tenant_id, actor_user_id=user_id, payload={"message": ...})`

6. **Database & Alembic Migrations**:
   - `backend/migrations/env.py` line 5 imports `app.models` and line 18 sets `target_metadata = Base.metadata`.
   - Running `/workspaces/TheTextileCare/backend/.venv/bin/alembic heads` reports current head: `ddf173e6fc96 (head)` (`phase4_catalog_services`).
   - Prior migrations: `0001` -> `2010fc7ee67f` -> `debba6592524` -> `275f700c133f` -> `ddf173e6fc96`.

7. **Test Suite Status**:
   - Running `/workspaces/TheTextileCare/backend/.venv/bin/pytest` yields:
     `53 passed, 2 warnings in 92.26s` (100% pass rate).
   - `backend/tests/conftest.py` lines 16-24 resets database schemas and runs `RoleService(db).seed_defaults()` before every test.
   - Running `pnpm typecheck` in workspace root passes (10/10 tasks successful).
   - Running `pnpm lint` in workspace root passes (0 warnings, 0 errors).

---

## 2. Logic Chain

1. **Architectural Pattern Preservation**:
   - Observation 1 establishes that the backend strictly adheres to a layered modular monolith: Models -> Schemas -> Repositories -> Services -> API Routers.
   - Therefore, the Phase 5 Pricing Engine must follow this exact convention by introducing:
     - `app/models/pricing.py`
     - `app/schemas/pricing.py`
     - `app/repositories/pricing.py`
     - `app/services/pricing.py` (CRUD, lifecycle, audit)
     - `app/services/pricing_calculator.py` (deterministic precedence and Decimal arithmetic)
     - `app/api/v1/pricing.py` (mounted at `/api/v1/pricing` in `app/api/router.py`).

2. **Decoupling Catalog and Pricing**:
   - Observation 4 confirms catalog entities have no price fields.
   - By creating `price_rules` that reference `service_id`, `service_item_id`, `service_addon_id`, and `category_id` as foreign keys without duplicating names, descriptions, or unit types, the system cleanly separates catalog offerings from dynamic pricing models.

3. **Multi-Tenant Security & ID Injection Prevention**:
   - Observation 2 demonstrates that tenant isolation requires:
     1. Deriving `tenant_id` exclusively from `ctx.tenant.id` via `require_tenant_context` / `require_permission`.
     2. Enforcing `where(Model.tenant_id == tenant_id)` on all repository queries.
     3. Pre-validating any foreign reference (`seller_id`, `branch_id`, `service_id`, `service_item_id`) against `ctx.tenant.id` to prevent cross-tenant ID injection.
   - Following this ensures Tenant A cannot view or manipulate Tenant B's pricing, returning 404/403.

4. **RBAC & Privilege Escalation Mitigation**:
   - Observation 3 shows how permissions are mapped and tested.
   - Adding `PRICING_READ = 'pricing.read'` and `PRICING_MANAGE = 'pricing.manage'` to `PermissionName`, updating `DEFAULT_ROLE_PERMISSIONS`, and adding descriptions to `PERMISSION_DESCRIPTIONS` in `services/roles.py`:
     - Blocks users with `VIEWER` or `TENANT_VIEWER` roles from mutating price books or rules (they only receive `pricing.read`).
     - Grants mutation capabilities to `TENANT_OWNER`, `TENANT_ADMIN`, `SELLER_OWNER`, `SELLER_ADMIN`, and `PLATFORM_ADMIN`.
     - Preserves 100% pass rate in `test_rbac_seed.py`.

5. **Alembic Migration Integrity**:
   - Observation 6 establishes that the current head is `ddf173e6fc96`.
   - Therefore, Phase 5 migration must specify `down_revision = 'ddf173e6fc96'` and must not touch or rewrite existing migrations 0001 through ddf173e6fc96.
   - Registering `PriceBook` and `PriceRule` in `backend/app/models/__init__.py` ensures Alembic and test fixtures automatically detect the new tables.

6. **Deterministic Calculation & Breakdown**:
   - Using Python `Decimal` with `ROUND_HALF_UP` for all calculations (`Base Price`, `Surcharge`, `Discount`, `Tax`, `Grand Total`) guarantees mathematically exact results without floating-point errors.
   - Formula `grand_total = subtotal + surcharges - discounts + tax` will be strictly validated.
   - The calculation endpoint remains completely stateless; no customer order or cart records are persisted.

---

## 3. Caveats

1. **Database Session in Tests**:
   - The test suite uses `engine` pointing to PostgreSQL (`postgresql+psycopg://postgres:postgres@localhost:5432/the_textile_care`). A running PostgreSQL database on localhost:5432 is required to execute tests.
2. **Platform Default Price Books**:
   - Platform defaults (precedence Level 1) should have `tenant_id = None` (or `is_default = True`). Query logic must allow selecting rules where `(tenant_id == ctx.tenant.id OR tenant_id IS NULL)` to support platform fallbacks while restricting mutations to tenant owners for their own books.
3. **Frontend Scope**:
   - `apps/seller-web` requires a minimal management UI. Client code must never perform price calculations locally; it must call `POST /api/v1/pricing/calculate`.

---

## 4. Conclusion

The existing backend architecture is exceptionally clean and well-prepared for Phase 5. The architectural separation between Catalog ("What is being offered?") and Pricing Engine ("How much does it cost?") is fully preserved.

The implementation blueprint in `/workspaces/TheTextileCare/.agents/explorer_survey_2/survey_backend.md` defines every model, schema, repository, service, router, permission, and test required to implement Phase 5 Pricing Engine Foundation with zero regressions.

---

## 5. Verification Method

To independently verify the findings and current system health:

1. **Verify Backend Pytest Suite**:
   ```bash
   /workspaces/TheTextileCare/backend/.venv/bin/pytest
   ```
   *Expected outcome*: 53 passed, 2 warnings.

2. **Verify Current Alembic Head**:
   ```bash
   /workspaces/TheTextileCare/backend/.venv/bin/alembic heads
   ```
   *Expected outcome*: `ddf173e6fc96 (head)`.

3. **Verify Absence of Pricing in Catalog Models**:
   Inspect `backend/app/models/catalog.py` and search for any pricing columns:
   ```bash
   grep -Ei "price|cost|amount|currency" /workspaces/TheTextileCare/backend/app/models/catalog.py
   ```
   *Expected outcome*: No matches found.

4. **Verify Monorepo TypeScript & Lint**:
   ```bash
   pnpm typecheck
   pnpm lint
   ```
   *Expected outcome*: All packages pass without errors.
