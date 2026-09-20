# BRIEFING — 2026-09-19T17:51:10Z

## Mission
Investigate R1 (Payment Abstraction & Timing) and R3 (Settlement Logic) against TheTextileCare codebase to design payment architecture, gateway abstraction, post-pickup approval payment flow, failure modes, and 15-day/Monday settlement logic without overloading OrderStatus.

## 🔒 My Identity
- Archetype: explorer
- Roles: explorer, survey
- Working directory: /workspaces/TheTextileCare/.agents/explorer_survey_phase7_2
- Original parent: 6b62fa2d-b0e1-4cea-9ad2-9f2593e98762
- Milestone: phase-7-survey

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Analyze R1 and R3 specifically
- Maintain strict tenant/seller isolation
- Do not overload OrderStatus with payment states
- Produce report.md and handoff.md in working directory
- Keep progress.md updated with timestamps
- Communicate via send_message to parent

## Current Parent
- Conversation ID: 6b62fa2d-b0e1-4cea-9ad2-9f2593e98762
- Updated: 2026-09-19T17:56:30Z

## Investigation State
- **Explored paths**:
  - `backend/app/models/order.py`, `commercial.py`, `payment.py`, `billing.py`
  - `backend/app/services/order.py`, `pricing.py`
  - `backend/app/api/v1/orders.py`, `router.py`
  - `docs/architecture/order-domain.md`, `phase-7-business-resolution.md`, `phase-7-customer-cancellation.md`
  - `backend/migrations/versions/a1b2c3d4e5f6_phase7_order_foundation.py`
  - `packages/types/src/order.ts`
- **Key findings**:
  - Pickup details are not yet modeled; need `OrderPickup` entity (`order_pickups`) to handle the post-confirmation inspection, submission, and customer approval flow.
  - Payment request is triggered explicitly upon customer pickup approval (`approved_at`).
  - Two payment failure modes mapped to `SellerCommercialConfiguration`: `payment_required_before_pickup` (blocks pickup completion / order progress on failure) vs `outstanding_receivable_allowed` (allows order to proceed to IN_PROGRESS while marking payment OUTSTANDING).
  - Two gateway scenarios: `TTC_GATEWAY` (funds held by platform, 15-day cooling period, Monday payout) vs `SELLER_GATEWAY` (direct seller funds, no platform hold, no settlement transfers, commission billed monthly via invoice).
  - Financial separation: Gateway fee/tax tracked distinctly from TTC commission/commission tax; partial and full refund logic properly recalculates retained amount and commission.
  - OrderStatus cleanliness: OrderStatus remains strictly operational (`DRAFT`, `PENDING`, `CONFIRMED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`); PaymentStatus (`PENDING`, `SUCCEEDED`, `FAILED`, `OUTSTANDING`, `REFUNDED`, `PARTIALLY_REFUNDED`) is tracked independently.
- **Unexplored areas**: None. Full evidence chain gathered for R1 and R3.

## Key Decisions Made
- Formalized 5-state Pickup lifecycle (`SCHEDULED`, `DETAILS_SUBMITTED`, `APPROVED`, `REJECTED`, `COMPLETED`).
- Formalized Payment lifecycle and gateway abstraction interface.
- Formalized 15-day cooling hold and Monday settlement algorithm.

## Artifact Index
- /workspaces/TheTextileCare/.agents/explorer_survey_phase7_2/DISPATCH.md — Task assignment
- /workspaces/TheTextileCare/.agents/explorer_survey_phase7_2/BRIEFING.md — Working memory
- /workspaces/TheTextileCare/.agents/explorer_survey_phase7_2/progress.md — Progress tracker and heartbeat
- /workspaces/TheTextileCare/.agents/explorer_survey_phase7_2/report.md — Detailed findings report
- /workspaces/TheTextileCare/.agents/explorer_survey_phase7_2/handoff.md — Handoff report

