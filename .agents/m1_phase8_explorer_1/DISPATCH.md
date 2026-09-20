# Dispatch Task: Milestone 1 Explorer 1 — Driver Schema, Models & RBAC Permissions

## Working Directory
`/workspaces/TheTextileCare/.agents/m1_phase8_explorer_1`

## Scope & Objective
Investigate the technical implementation strategy for Milestone 1:
- Driver database schema migration revising `b2c3d4e5f6a7`.
- SQLAlchemy 2.0 models in `backend/app/models/driver.py`.
- RBAC role (`RoleName.DRIVER`) and permissions registration in `backend/app/core/permissions/constants.py` and `backend/app/services/roles.py`.
- Pydantic v2 schemas in `backend/app/schemas/driver.py`.

## Inputs to Read
- `/workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md`
- `/workspaces/TheTextileCare/.agents/PROJECT.md`
- `/workspaces/TheTextileCare/.agents/survey_spec_miner_1/handoff.md`
- `/workspaces/TheTextileCare/.agents/survey_explorer_2/handoff.md`

## Specific Analysis Needed
1. Review proposed tables: `drivers`, `driver_vehicles`, `driver_seller_authorizations`, `driver_compliance_documents`.
2. Define exact column types, foreign keys, cascade rules, indexes, and unique constraints.
3. Review SQLAlchemy 2.0 mapping standards (`Mapped[...]`, `mapped_column(...)`, relationships).
4. Review RBAC permissions: define `DRIVER_MANAGE`, `DRIVER_VIEW`, `DUTY_MANAGE`, `DUTY_VIEW`, `DUTY_REASSIGN`, `OPERATIONS_ALERT_VIEW`. Specify role-permission mapping for `PLATFORM_ADMIN`, `TENANT_OWNER`, `TENANT_ADMIN`, `SELLER_OWNER`, `SELLER_ADMIN`, `STAFF`, `VIEWER`, and `DRIVER`.
5. Identify potential migration and schema pitfalls (e.g. Alembic down_revision, index naming, UUID generation).

## Output Requirements
Write a complete, structured analysis in `/workspaces/TheTextileCare/.agents/m1_phase8_explorer_1/handoff.md` with concrete code snippets, model definitions, and recommendations for the Worker.

## 2026-09-20T08:15:32Z
You are m1_phase8_explorer_1. Your working directory is /workspaces/TheTextileCare/.agents/m1_phase8_explorer_1.
Read your instructions in /workspaces/TheTextileCare/.agents/m1_phase8_explorer_1/DISPATCH.md, /workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md, and /workspaces/TheTextileCare/.agents/PROJECT.md.
Investigate Milestone 1 implementation strategy for Driver migration, models, schemas, and RBAC permissions.
Deliver your handoff report to /workspaces/TheTextileCare/.agents/m1_phase8_explorer_1/handoff.md and notify parent when complete.

