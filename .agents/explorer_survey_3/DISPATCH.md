# Task Assignment: Survey Frontend, Types & Monorepo Tooling

## Working Directory
`/workspaces/TheTextileCare/.agents/explorer_survey_3`

## Authoritative Request
Read `/workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md` (specifically header `## 2026-09-19T04:33:52Z`).

## Objective
As `teamwork_preview_explorer`, investigate the frontend, shared types, monorepo tooling, and verification setup in `/workspaces/TheTextileCare`.
Specifically investigate:
1. Shared TypeScript types in `packages/types` (or equivalent):
   - Where are existing shared types located? How are they built, exported, and imported across apps?
   - What pricing types need to be added (e.g. `PriceBook`, `PriceRule`, `PricingCalculationRequest`, `PricingCalculationResult`, etc.)?
2. `apps/seller-web`:
   - Frontend architecture (Next.js, Vite, React, components, routes, API clients, state management).
   - How does seller-web currently interact with catalog and backend APIs?
   - What is the existing UI foundation for seller-web (navigation, layout, tables, forms)?
   - Where should the minimal pricing management foundation be added in `apps/seller-web` without duplicating calculation logic?
3. Tooling, build, lint, and typecheck scripts:
   - What monorepo tools are configured (`turbo`, `pnpm`, etc.)?
   - How do `pnpm lint`, `pnpm typecheck`, `pnpm build` work across all monorepo packages?
   - How are docs structured in `docs/`? What documentation already exists for Phase 1-4?
   - Git status and cleanliness check.

## Deliverable
Write a comprehensive frontend, types, and tooling survey report at:
`/workspaces/TheTextileCare/.agents/explorer_survey_3/survey_frontend_tooling.md`
and complete handoff at `/workspaces/TheTextileCare/.agents/explorer_survey_3/handoff.md`.
Update `progress.md` with your progress and timestamps.
## 2026-09-19T04:35:57Z
You are assigned as the Frontend Tooling Explorer for TTC Phase 5: Pricing Engine Foundation.
Your working directory is: /workspaces/TheTextileCare/.agents/explorer_survey_3
Read /workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md (specifically header ## 2026-09-19T04:33:52Z) and /workspaces/TheTextileCare/.agents/explorer_survey_3/DISPATCH.md.
Investigate the monorepo packages (packages/types, apps/seller-web, etc.), TypeScript type exports, seller-web application architecture and API clients, pnpm lint/typecheck/build setup, docs/ directory structure, and git status.
Identify what types need to be added, what UI foundation needs to be built in seller-web, and how monorepo verification is executed.
Produce your full report at /workspaces/TheTextileCare/.agents/explorer_survey_3/survey_frontend_tooling.md and deliver a comprehensive handoff at /workspaces/TheTextileCare/.agents/explorer_survey_3/handoff.md.
Keep your progress.md updated. When complete, send a message to orchestrator with your report path.
