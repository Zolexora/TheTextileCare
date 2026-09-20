# Task Assignment: Survey Backend Architecture & Existing Codebase

## Working Directory
`/workspaces/TheTextileCare/.agents/explorer_survey_2`

## Authoritative Request
Read `/workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md` (specifically header `## 2026-09-19T04:33:52Z`).

## Objective
As `teamwork_preview_explorer`, investigate the existing backend architecture and code in `/workspaces/TheTextileCare`.
Specifically investigate:
1. Backend project layout (FastAPI application entrypoint, routers, models, schemas, services, core, database session management).
2. Existing Phase 1-4 implementations:
   - Tenant isolation implementation (how is `tenant_id` handled, tenant context, middleware, dependencies).
   - Authentication & RBAC implementation (roles, permissions, security dependencies, current permission enum/constants).
   - Catalog domain models (Phase 4): where are services, products, categories, variants, items defined? How are they structured? Note: catalog must NOT have pricing fields.
   - AuditService implementation: how are lifecycle audit events emitted and recorded?
   - Database & Alembic: where are Alembic migrations stored? What is the current head migration? How are SQLAlchemy 2 models registered?
   - Testing setup: where are backend pytest tests located? How are fixtures configured (DB, client, auth tokens, mock tenants)?
3. Identify integration points for Phase 5 Pricing Engine:
   - Where new models (`PriceBook`, `PriceRule`, etc.) should live.
   - How price rules reference catalog entities without coupling or duplicating data.
   - Where the deterministic calculation service should reside.
   - Where router `/api/v1/pricing/` should be mounted.
   - New permissions needed (`pricing.read`, `pricing.manage`) and how they fit into existing RBAC.

## Deliverable
Write a comprehensive backend architecture survey report at:
`/workspaces/TheTextileCare/.agents/explorer_survey_2/survey_backend.md`
and complete handoff at `/workspaces/TheTextileCare/.agents/explorer_survey_2/handoff.md`.
Update `progress.md` with your progress and timestamps.


## 2026-09-19T04:35:57Z
You are assigned as the Backend Architecture Explorer for TTC Phase 5: Pricing Engine Foundation.
Your working directory is: /workspaces/TheTextileCare/.agents/explorer_survey_2
Read /workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md (specifically header ## 2026-09-19T04:33:52Z) and /workspaces/TheTextileCare/.agents/explorer_survey_2/DISPATCH.md.
Investigate the existing backend codebase (/workspaces/TheTextileCare/backend or apps/api), database models, Alembic migrations, tenant isolation mechanisms, auth/RBAC system, Phase 4 catalog models, AuditService, and pytest test suite.
Map out exactly how Phase 5 Pricing Engine fits into the existing architecture.
Produce your full report at /workspaces/TheTextileCare/.agents/explorer_survey_2/survey_backend.md and deliver a comprehensive handoff at /workspaces/TheTextileCare/.agents/explorer_survey_2/handoff.md.
Keep your progress.md updated. When complete, send a message to orchestrator with your report path.
