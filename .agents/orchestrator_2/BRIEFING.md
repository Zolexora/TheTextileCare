# BRIEFING — 2026-09-19T17:50:50Z

## Mission
Orchestrate Phase 7 of TTC (TheTextileCare): Commercial billing, payment abstraction & timing, settlement logic, and seller restriction foundation.

## 🔒 My Identity
- Archetype: orchestrator
- Roles: orchestrator, user_liaison, human_reporter, successor
- Working directory: /workspaces/TheTextileCare/.agents/orchestrator_2
- Original parent: parent
- Original parent conversation ID: c4d32e1e-eaf2-4297-8f8a-a8dde1fc0a5e

## 🔒 My Workflow
- **Pattern**: Project
- **Scope document**: /workspaces/TheTextileCare/.agents/PROJECT.md
1. **Decompose**: Survey codebase & specs, produce Feature Inventory, Milestones, and Interface Contracts.
2. **Dispatch & Execute** (pick ONE):
   - **Direct (iteration loop)**: Assess scope. Delegate milestones to sub-orchestrators or execute Explorer -> Worker -> Reviewer -> Challenger -> Auditor gate cycle.
   - **Delegate (sub-orchestrator)**: When an item is too large, spawn a sub-orchestrator for it.
3. **On failure** (in this order):
   - Retry: nudge stuck agent or re-send task
   - Replace: spawn fresh agent with partial progress
   - Skip: proceed without (only if non-critical)
   - Redistribute: split stuck agent's remaining work
   - Redesign: re-partition decomposition
   - Escalate: report to parent (sub-orchestrators only, last resort)
4. **Succession**: Self-succeed at 16 spawns, write handoff.md, spawn successor.
- **Work items**:
  1. Survey & Architecture Mapping [in-progress]
  2. E2E Testing Track [pending]
  3. Milestone 1: Payment Domain & Timing Abstraction [pending]
  4. Milestone 2: Commercial Models & Monthly Billing [pending]
  5. Milestone 3: Settlement Logic & Payout Engine [pending]
  6. Milestone 4: Seller Overdue Restrictions & Marketplace Re-selection [pending]
  7. Final Milestone 5: E2E Test Suite Pass (100%) & Adversarial Hardening [pending]
- **Current phase**: 0 (Survey)
- **Current focus**: Surveying existing Phase 1-6 architecture, schema, and contracts

## 🔒 Key Constraints
- NEVER write, modify, or create source code files directly.
- NEVER run build/test commands yourself — require workers to do so.
- NEVER investigate or explore the problem at the code level — dispatch Explorers for technical investigation.
- You MAY use file-editing tools ONLY for metadata/state files (.md) in your .agents/ folder.
- Never reuse a subagent after it has delivered its handoff — always spawn fresh.
- Do not overload OrderStatus enum with payment states; keep operational and payment states separate.
- Financial mutations must be idempotent.
- Strict tenant/seller data isolation.
- Binary veto on Forensic Auditor failures.

## Current Parent
- Conversation ID: c4d32e1e-eaf2-4297-8f8a-a8dde1fc0a5e
- Updated: 2026-09-19T17:50:50Z

## Key Decisions Made
- Starting Phase 7 fresh survey with 3 parallel Explorers per Project Pattern Step 0.

## Team Roster
| Agent | Type | Work Item | Status | Conv ID |
|-------|------|-----------|--------|---------|
| spec_miner_survey_phase7 | teamwork_preview_spec_miner | Survey Architecture & Grounding | completed | e0896ea7-a4eb-4100-99b9-1ed2f527f835 |
| explorer_survey_phase7_2 | teamwork_preview_explorer | Survey R1 Payment & R3 Settlement | completed | 0dcee61e-37f4-4d5f-b66b-eceea9a424f3 |
| explorer_survey_phase7_3 | teamwork_preview_explorer | Survey R2 Billing & R4 Restrictions | completed | 5a386cce-4370-44cd-8551-d0ff4dedbe32 |
| test_writer_phase7_e2e | teamwork_preview_test_writer | E2E Testing Track (Tiers 1-4) | in-progress | 75395fa9-b4c1-4d4c-8198-59c0b38be030 |
| explorer_m1_1 | teamwork_preview_explorer | M1 Migration & DDL Strategy | completed | 67083bde-8d53-4fba-a6f9-676486ada456 |
| explorer_m1_2 | teamwork_preview_explorer | M1 Domain Models & Schemas | completed | cf7bc8dd-a321-4756-ad16-69283fae719c |
| explorer_m1_3 | teamwork_preview_explorer | M1 RBAC & Repositories | completed | 4fba725f-bff6-45c7-a8a7-c75d59089a7f |
| worker_m1_1 | teamwork_preview_worker | M1 Implementation & Verification | in-progress | c1fa1b38-8e6b-432c-8abc-9f530674a554 |

## Succession Status
- Succession required: no
- Spawn count: 8 / 16
- Pending subagents: 75395fa9-b4c1-4d4c-8198-59c0b38be030, c1fa1b38-8e6b-432c-8abc-9f530674a554
- Predecessor: orchestrator_1
- Successor: not yet spawned

## Active Timers
- Heartbeat cron: 6b62fa2d-b0e1-4cea-9ad2-9f2593e98762/task-22
- Safety timer: none
- On succession: kill all timers before spawning successor
- On context truncation: run `manage_task(Action="list")` — re-create if missing

## Artifact Index
- /workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md — User requirements
- /workspaces/TheTextileCare/.agents/orchestrator_2/DISPATCH.md — Orchestrator dispatch record
- /workspaces/TheTextileCare/.agents/orchestrator_2/progress.md — Liveness & step tracking
- /workspaces/TheTextileCare/.agents/orchestrator_2/BRIEFING.md — Persistent context & state
