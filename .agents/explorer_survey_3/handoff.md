# Handoff Report: Frontend, Shared Types, & Monorepo Tooling Survey

**Agent**: Frontend Tooling Explorer (`teamwork_preview_explorer`)  
**Working Directory**: `/workspaces/TheTextileCare/.agents/explorer_survey_3`  
**Target Milestone**: TTC Phase 5: Pricing Engine Foundation  
**Handoff Type**: Hard (Investigation complete)  

---

## 1. Observation

1. **Shared Types (`packages/types`)**:
   - `packages/types/package.json`: Lines 5-6 configure `"main": "./src/index.ts"` and `"types": "./src/index.ts"`. It has only a `typecheck` script (`tsc -p tsconfig.json --noEmit`) and no `build` or `dist/` script.
   - `packages/types/src/index.ts`: Lines 1-5 export `common`, `api`, `tenant`, and `catalog`.
   - `packages/types/src/catalog.ts`: Defines interfaces for Phase 4 (`Catalog`, `Category`, `Service`, `ServiceItem`, `ServiceAddon`).
   - `packages/types/src/tenant.ts`: Lines 5-14 define `PermissionName` but currently only contain Phase 1 permissions (`tenant.*`, `membership.*`, `role.*`, `user.*`, `audit.*`). It lacks `pricing.*` permissions.
   - `@ttc/types` is not listed in `dependencies` in `apps/seller-web/package.json`.

2. **Frontend Architecture (`apps/seller-web`)**:
   - `apps/seller-web/package.json`: Lines 12-19 show dependencies: `"@ttc/branding": "workspace:^"`, `"@ttc/config": "workspace:*"`, `"@ttc/ui": "workspace:*"`, `"next": "14.2.15"`, `"react": "18.3.1"`, `"react-dom": "18.3.1"`.
   - Neither `@ttc/types` nor `@ttc/api-client` is currently installed in `apps/seller-web`.
   - `apps/seller-web/src/app/page.tsx`: Contains only static mock tenant state (`MOCK_CONFIG`) and basic `@ttc/ui` components (`Button`, `Card`, `Logo`). There is currently no API client instance, no data fetching, and no routing hierarchy beyond `/`.
   - `@ttc/api-client` already exists in `packages/api-client/src/client.ts`, featuring an `ApiClient` class wrapping `fetch` with typed requests, headers, and error handling.

3. **Tooling & Build Execution**:
   - `pnpm typecheck` (`turbo run typecheck`): Successfully checked 10 packages in 7.251s with 0 errors.
   - `pnpm lint` (`turbo run lint`): Executed across `@ttc/seller-web`, `@ttc/admin-web`, and `@ttc/marketplace-web` in 11.797s with "No ESLint warnings or errors".
   - `pnpm build` (`turbo run build`): Successfully built production bundles for Next.js applications in 735ms (cached) / clean build.
   - `pnpm test` (`turbo run test`): Returned code 0 with "No tasks were executed as part of this run" because monorepo packages do not have `test` scripts in `package.json`.

4. **Backend Test Discrepancy**:
   - Running `pytest` in `/workspaces/TheTextileCare/backend` produced 35 errors and 2 failures out of 53 tests.
   - Root cause in `backend/app/core/permissions/constants.py`: In `DEFAULT_ROLE_PERMISSIONS`, catalog permissions (`PermissionName.CATALOG_*`) are duplicated twice:
     - `RoleName.TENANT_ADMIN.value`: lines 184–195 and lines 200–211.
     - `RoleName.SELLER_OWNER.value`: lines 237–248 and lines 253–264.
     - `RoleName.SELLER_ADMIN.value`: lines 280–291 and lines 296–307.
   - Verbatim Postgres error during `reset_database` fixture:
     `sqlalchemy.exc.IntegrityError: (psycopg.errors.UniqueViolation) duplicate key value violates unique constraint "uq_role_permission"`
     `DETAIL: Key (role_id, permission_id)=(..., ...) already exists.`

5. **Documentation & Git Status**:
   - `docs/` structure is organized into architectural domains (`architecture/`, `database/`, `decisions/`, `deployment/`, `project-status/`, `security/`, etc.).
   - `git status`: Working branch `main` is up to date with `origin/main`. Working directory has `deleted: docs/project_stats/phase_4_verification_report.md` and untracked `docs/project-status/phase_4_verification_report.md` and `ORIGINAL_REQUEST.md`.

---

## 2. Logic Chain

1. **Type Integration**:
   - Because `packages/types` exports directly from source via `src/index.ts` (Observation 1), any new interfaces in `packages/types/src/pricing.ts` re-exported in `src/index.ts` will immediately be accessible to all TypeScript consumers across the monorepo.
   - Because `apps/seller-web` currently lacks `@ttc/types` in its `package.json` dependencies (Observation 1 & 2), adding `"@ttc/types": "workspace:*"` to `apps/seller-web/package.json` is necessary for type-safe pricing development.

2. **Frontend UI Foundation without Logic Duplication**:
   - Requirement R5 specifies building a minimal pricing management foundation in `apps/seller-web` without duplicating calculation logic.
   - Because `apps/seller-web` has no existing API client wiring (Observation 2), installing `"@ttc/api-client": "workspace:*"` and instantiating `apiClient` in `apps/seller-web/src/lib/api.ts` provides the exact mechanism to call backend pricing endpoints.
   - Implementing a dedicated `/pricing` route with:
     a. Price Books table / list
     b. Price Rules inspector
     c. Interactive Deterministic Calculation Sandbox that issues `POST /api/v1/pricing/calculate` and renders the exact backend breakdown
     ensures a complete functional UI foundation while strictly delegating 100% of the pricing mathematics and rule resolution to the backend.

3. **Monorepo Verification**:
   - Because `pnpm lint`, `pnpm typecheck`, and `pnpm build` pass cleanly (Observation 3), any changes introduced in Phase 5 can be validated against an already stable baseline.
   - Because the backend `uq_role_permission` error (Observation 4) blocks pytest test runs, deduplicating the catalog permissions in `backend/app/core/permissions/constants.py` is a prerequisite for backend test verification.

---

## 3. Caveats

1. **Mobile Applications Scope**:
   - The three mobile applications (`driver-mobile`, `marketplace-mobile`, `seller-mobile`) do not have `typecheck` scripts configured in `package.json`. While they consume workspace types, full verification is anchored on the 10 TypeScript packages and the 3 Next.js applications.
2. **Backend Permission Seed Assumption**:
   - The permission duplicates in `DEFAULT_ROLE_PERMISSIONS` were introduced in Phase 4. Fixing them requires removing the redundant list items in `backend/app/core/permissions/constants.py`. No database schema changes are required for this fix.

---

## 4. Conclusion

1. **Shared Types Foundation**:
   - Create `packages/types/src/pricing.ts` defining `PriceBook`, `PriceRule`, `PriceRuleType`, `ComponentType`, `PriceBookScope`, `PriceBookStatus`, `PricingCalculationRequest`, `PricingCalculationResult`, and CRUD inputs.
   - Export from `packages/types/src/index.ts` and add `pricing.read` and `pricing.manage` to `PermissionName` in `packages/types/src/tenant.ts`.
2. **Seller Web UI Foundation**:
   - Add `"@ttc/types": "workspace:*"` and `"@ttc/api-client": "workspace:*"` to `apps/seller-web/package.json`.
   - Implement `apps/seller-web/src/lib/api.ts` and `apps/seller-web/src/app/pricing/page.tsx`.
   - Include an interactive pricing sandbox that delegates calculation requests to `POST /api/v1/pricing/calculate` to avoid duplicating business logic.
3. **Backend & Test Readiness**:
   - Deduplicate `PermissionName.CATALOG_*` entries in `backend/app/core/permissions/constants.py` to restore 100% pass rate in pytest.
4. **Documentation & Git Hygiene**:
   - Produce the 4 required Phase 5 documentation files in `docs/architecture/pricing-engine.md`, `docs/database/phase-5-pricing-schema.md`, `docs/security/pricing-security-isolation.md`, and `docs/project-status/phase_5_verification_report.md`.
   - Stage untracked files and commit cleanly as `feat(phase-5): implement pricing engine foundation`.

---

## 5. Verification Method

To independently verify the findings and recommendations:

1. **Verify Shared Types & Monorepo Tooling**:
   ```bash
   pnpm typecheck
   pnpm lint
   pnpm build
   ```
   *Expected Result*: All 10 typechecked packages and 3 Next.js applications succeed with zero errors.

2. **Verify Backend Role Permission Duplication**:
   Inspect `backend/app/core/permissions/constants.py` lines 184–211, 237–264, and 280–307. Run:
   ```bash
   python3 -c "import tests.conftest as c; from app.services.roles import RoleService; db = c.SessionLocal(); RoleService(db).seed_defaults()"
   ```
   *Expected Observation*: Fails with `UniqueViolation: duplicate key value violates unique constraint "uq_role_permission"`.

3. **Verify Documentation Structure and Git Status**:
   ```bash
   git status
   ```
   Inspect `docs/` and verify layout compliance.
