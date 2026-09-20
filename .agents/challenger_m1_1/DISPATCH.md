# Task Assignment: Milestone 1 Challenger 1 — Schema Invariants & Stress Testing

## Working Directory
`/workspaces/TheTextileCare/.agents/challenger_m1_1`

## Authoritative Context
Read:
- `/workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md` (specifically header ## 2026-09-19T04:33:52Z)
- `/workspaces/TheTextileCare/.agents/PROJECT.md`
- `/workspaces/TheTextileCare/.agents/worker_m1_1/handoff.md`

## Challenge Scope
Adversarially challenge the Milestone 1 schemas and models:
1. Try to break Pydantic V2 schemas in `backend/app/schemas/pricing.py`:
   - Test invalid/lowercase currency codes (`usd`, `US`, `USDD`).
   - Test negative rates (`-0.01`, `-100.00`).
   - Test inverted date ranges (`effective_from > effective_to`).
   - Test scope misalignments (`PLATFORM_DEFAULT` with seller_id, `SELLER` without seller_id).
   - Test breakdown mathematical invariant with float vs Decimal drift (`grand_total != subtotal + surcharges - discounts + tax`).
2. Run test harnesses to verify that all boundary conditions and invariants hold under stress.
3. Conclude with verdict: APPROVE or REQUEST_CHANGES.

## Deliverable
Deliver your handoff report at `/workspaces/TheTextileCare/.agents/challenger_m1_1/handoff.md`.
Send message with verdict when done.

## 2026-09-19T05:02:55Z
You are Milestone 1 Challenger 1: Schema Invariants & Stress Testing.
Your working directory is: /workspaces/TheTextileCare/.agents/challenger_m1_1
Read /workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md (specifically header ## 2026-09-19T04:33:52Z), /workspaces/TheTextileCare/.agents/PROJECT.md, /workspaces/TheTextileCare/.agents/worker_m1_1/handoff.md, and /workspaces/TheTextileCare/.agents/challenger_m1_1/DISPATCH.md.
Adversarially stress-test Pydantic V2 schemas, decimal rounding, scope alignment, and breakdown invariants.
Deliver your handoff report at /workspaces/TheTextileCare/.agents/challenger_m1_1/handoff.md with your verdict (APPROVE or REQUEST_CHANGES).
Notify orchestrator via send_message.
