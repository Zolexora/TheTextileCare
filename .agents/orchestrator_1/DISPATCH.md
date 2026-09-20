## 2026-09-19T04:35:03Z

You are the Project Orchestrator for TTC Phase 5: Pricing Engine Foundation.

Your working directory is: /workspaces/TheTextileCare/.agents/orchestrator_1
Workspace root is: /workspaces/TheTextileCare
Authoritative request is at: /workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md (see request under header ## 2026-09-19T04:33:52Z)

Task overview:
Implement the Pricing Engine Foundation for TTC as a reusable, deterministic, tenant-isolated pricing domain, establishing "How much does it cost?" structurally isolated from the catalog ("What is being offered?").
Please strictly satisfy all requirements (R1 to R5) and acceptance criteria detailed in ORIGINAL_REQUEST.md:
- R1: Architectural Integrity (FastAPI, SQLAlchemy 2, Alembic migration for Phase 5, PostgreSQL, tenant isolation, RBAC).
- R2: Core Pricing Model & Components (`price_books`, `price_rules`, Decimal calculations, rule types FIXED, PER_ITEM, PER_UNIT, PER_WEIGHT, normalized breakdown).
- R3: Deterministic Calculation Service (Precedence: Platform Default -> Seller -> Branch -> Rule, effective dates, surcharges/discounts/taxes).
- R4: Security & Permissions (Strict tenant isolation, prevent ID injection, granular permissions `pricing.read`, `pricing.manage`, AuditService events).
- R5: Integration & APIs (REST endpoints under `/api/v1/pricing/`, TypeScript types in `packages/types`, seller-web UI foundation).
- Full testing (`pytest` for Phase 1-5, Alembic migration upgrade, `pnpm lint`, `pnpm typecheck`, `pnpm build`, docs, clean git commit `feat(phase-5): implement pricing engine foundation`).

Maintain your BRIEFING.md and progress.md in your working directory (.agents/orchestrator_1/).
When all acceptance criteria are met, report completion to the Sentinel.
