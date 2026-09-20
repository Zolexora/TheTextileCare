# Task Assignment: Milestone 1 — Backend Pricing Core & Schema Foundation

## Working Directory
`/workspaces/TheTextileCare/.agents/sub_orch_m1`

## Role & Mission
You are the Sub-Orchestrator for Milestone 1 of TTC Phase 5: Pricing Engine Foundation.
Your parent is Project Orchestrator (`6f64afd2-1d3a-42aa-aecd-e2488f1779ca`).

## Authoritative Context & Scope
Read:
- `/workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md` (specifically header `## 2026-09-19T04:33:52Z`)
- `/workspaces/TheTextileCare/.agents/PROJECT.md` (specifically Milestone 1 and Interface Contracts)
- Survey reports:
  - `/workspaces/TheTextileCare/.agents/explorer_survey_2/survey_backend.md`
  - `/workspaces/TheTextileCare/.agents/spec_miner_survey_1/survey_requirements.md`

## Milestone 1 Objectives
1. **Fix RBAC Permission Seed & Test Fixture**:
   - In `backend/app/core/permissions/constants.py`, remove duplicate `PermissionName.CATALOG_*` entries in `DEFAULT_ROLE_PERMISSIONS` under `TENANT_ADMIN`, `SELLER_OWNER`, and `SELLER_ADMIN`.
   - In `backend/tests/conftest.py`, ensure `import app.models` is present before `Base.metadata.create_all()` so all tables are registered.
2. **Add Phase 5 Pricing Permissions**:
   - Add `PRICING_READ = "pricing.read"` and `PRICING_MANAGE = "pricing.manage"` to `PermissionName` in `backend/app/core/permissions/constants.py`.
   - Map `PRICING_READ` and `PRICING_MANAGE` to `DEFAULT_ROLE_PERMISSIONS`:
     - `PLATFORM_ADMIN`: `PRICING_READ`, `PRICING_MANAGE`
     - `TENANT_OWNER`, `TENANT_ADMIN`: `PRICING_READ`, `PRICING_MANAGE`
     - `SELLER_OWNER`, `SELLER_ADMIN`: `PRICING_READ`, `PRICING_MANAGE`
     - `TENANT_VIEWER`, `SELLER_STAFF`: `PRICING_READ` only (strictly no `PRICING_MANAGE`)
   - Add descriptions to `PERMISSION_DESCRIPTIONS` in `backend/app/services/roles.py`.
3. **Implement Pricing Models (`backend/app/models/pricing.py`)**:
   - `PriceBookScope`: `PLATFORM_DEFAULT`, `SELLER`, `BRANCH`
   - `PriceBookStatus`: `DRAFT`, `ACTIVE`, `ARCHIVED`
   - `PriceRuleType`: `FIXED`, `PER_ITEM`, `PER_UNIT`, `PER_WEIGHT`
   - `ComponentType`: `BASE_PRICE`, `SURCHARGE`, `DISCOUNT`, `TAX`
   - `PriceBook` model: `id`, `tenant_id` (nullable for platform defaults), `name`, `scope`, `seller_id` (nullable), `branch_id` (nullable), `currency` (default "USD"), `priority` (default 0), `is_active` (default True), `created_at`, `updated_at`.
   - `PriceRule` model: `id`, `tenant_id` (nullable), `price_book_id` (FK to `price_books.id`), `service_id` (nullable FK to `services.id`), `service_item_id` (nullable FK to `service_items.id`), `service_addon_id` (nullable FK to `service_addons.id`), `rule_type`, `component_type`, `rate` (`Numeric(10, 2)` / Decimal), `effective_from` (nullable datetime), `effective_to` (nullable datetime), `is_active` (default True), `priority` (default 0), `created_at`, `updated_at`.
   - Register models in `backend/app/models/__init__.py`.
4. **Create Alembic Migration**:
   - Create new migration in `backend/migrations/versions/` with `down_revision = 'ddf173e6fc96'`.
   - Create `price_books` and `price_rules` tables with proper indexes (`idx_price_books_tenant_scope`, `idx_price_rules_book_service`, etc.) and constraints.
5. **Implement Schemas & Repository**:
   - `backend/app/schemas/pricing.py`: Pydantic request/response models.
   - `backend/app/repositories/pricing.py`: Multi-tenant repository enforcing `tenant_id` isolation.
6. **Verification**:
   - Verify `alembic upgrade head` succeeds.
   - Verify unit tests for models, repository, and RBAC seed pass.

## Execution Rules
- Follow Sub-Orchestrator procedure: Assess -> Decompose or Iteration Loop (Explorer -> Worker -> Reviewer -> Challenger -> Auditor -> Gate).
- As Sub-Orchestrator, dispatch your subagents (do not write code yourself).
- Ensure workers include the MANDATORY INTEGRITY WARNING.
- Maintain your own `SCOPE.md`, `BRIEFING.md`, `progress.md`, and `GATE_STATUS.md`.
- When Milestone 1 gate passes, deliver `handoff.md` and notify Project Orchestrator via `send_message`.
