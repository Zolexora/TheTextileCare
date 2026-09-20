# Task Assignment: Survey Requirements & Specifications

## Working Directory
`/workspaces/TheTextileCare/.agents/spec_miner_survey_1`

## Authoritative Request
Read `/workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md` (specifically header `## 2026-09-19T04:33:52Z`).

## Objective
As `teamwork_preview_spec_miner`, conduct a thorough specification extraction of TTC Phase 5: Pricing Engine Foundation.
Inspect:
1. `/workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md`
2. Any existing specification, architecture, or design documents in `/workspaces/TheTextileCare/docs/` or throughout the repository relating to Phase 1-4 and Phase 5.
3. Identify all functional and non-functional requirements for Phase 5:
   - R1: Architectural Integrity (FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, modular monolith, tenant isolation, RBAC).
   - R2: Core Pricing Model & Components (`price_books`, `price_rules`, Decimal calculations, rule types FIXED, PER_ITEM, PER_UNIT, PER_WEIGHT, breakdown components Base Price, Surcharge, Discount, Tax).
   - R3: Deterministic Calculation Service (precedence Platform Default -> Seller -> Branch -> Rule, effective dates `effective_from`/`effective_to`, active/draft states, validation of tenant/seller/branch, no order persistence).
   - R4: Security & Permissions (Strict tenant isolation, prevent ID injection, granular permissions `pricing.read`, `pricing.manage`, AuditService integration).
   - R5: Integration & APIs (REST endpoints under `/api/v1/pricing/`, TypeScript types in `packages/types`, seller-web UI foundation).
   - Acceptance criteria and verification conditions.

## Deliverable
Write a comprehensive specification mining report at:
`/workspaces/TheTextileCare/.agents/spec_miner_survey_1/survey_requirements.md`
and complete handoff at `/workspaces/TheTextileCare/.agents/spec_miner_survey_1/handoff.md`.
Update `progress.md` with your progress and timestamps.


## 2026-09-19T04:35:57Z
You are assigned as the Pricing Specification Miner for TTC Phase 5: Pricing Engine Foundation.
Your working directory is: /workspaces/TheTextileCare/.agents/spec_miner_survey_1
Read /workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md (specifically header ## 2026-09-19T04:33:52Z) and /workspaces/TheTextileCare/.agents/spec_miner_survey_1/DISPATCH.md.
Extract all precise specifications, requirements (R1-R5), acceptance criteria, entity models, precedence logic, rule types, breakdown structure, security constraints, and integration requirements.
Produce your full report at /workspaces/TheTextileCare/.agents/spec_miner_survey_1/survey_requirements.md and deliver a comprehensive handoff at /workspaces/TheTextileCare/.agents/spec_miner_survey_1/handoff.md.
Keep your progress.md updated. When complete, send a message to orchestrator with your report path.
