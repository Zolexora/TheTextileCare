# BRIEFING — 2026-09-19T17:56:00Z

## Mission
Investigate R2 (Commercial Models & Billing) and R4 (Seller Restrictions & Marketplace Re-selection) against TTC codebase.

## 🔒 My Identity
- Archetype: explorer
- Roles: survey, analysis, investigation
- Working directory: /workspaces/TheTextileCare/.agents/explorer_survey_phase7_3
- Original parent: 6b62fa2d-b0e1-4cea-9ad2-9f2593e98762
- Milestone: Phase 7 Survey & Analysis

## 🔒 Key Constraints
- Read-only investigation — do NOT implement
- Analyze commercial models (Model 1: % Commission vs Model 2: Fixed Subscription)
- Monthly billing cycles, payment deadlines, daily late-payment penalties
- Overdue enforcement levels (WARNING, MARKETPLACE_RESTRICTED, FULL_SUSPENSION)
- Automatic cancellation of PENDING orders on restriction with reason SELLER_RESTRICTED
- Customer seller re-selection logic (link new order to original, no refund needed as no payment yet)
- R5: Tenant isolation, idempotency, reuse existing pricing and snapshot architectures

## Current Parent
- Conversation ID: 6b62fa2d-b0e1-4cea-9ad2-9f2593e98762
- Updated: 2026-09-19T17:56:00Z

## Investigation State
- **Explored paths**:
  - `backend/app/models/commercial.py`
  - `backend/app/models/billing.py`
  - `backend/app/models/payment.py`
  - `backend/app/models/order.py`
  - `backend/app/models/seller.py`
  - `backend/app/services/marketplace.py`
  - `backend/app/repositories/marketplace.py`
  - `backend/app/services/order.py`
  - `backend/app/api/v1/orders.py`
  - `backend/migrations/versions/`
- **Key findings**:
  - Models for `SellerCommercialConfiguration`, `SellerBillingInvoice`, `Payment`, `Refund` are drafted but not migrated.
  - Model 1 (Commission on retained amount) and Model 2 (Subscription fee, 0% commission) are mutually exclusive.
  - Invoices run monthly with configurable due dates (15 days grace). Late penalties are deterministically and idempotently calculated daily as `balance * daily_rate * days_overdue`.
  - Restriction levels `WARNING`, `MARKETPLACE_RESTRICTED`, `FULL_SUSPENSION` cleanly suppress discovery and trigger auto-cancellation of `PENDING` orders with reason `SELLER_RESTRICTED`. Operational orders (`CONFIRMED`, `IN_PROGRESS`) remain unaffected.
  - Since customer payment is captured only post-pickup approval, `PENDING` orders have zero collected funds; re-selection requires zero refunds.
  - Re-selection links `new_order.reselected_from_order_id = original_order.id`, enforces single-reselection idempotency, and runs new items through deterministic `PricingService`.
- **Unexplored areas**: None within R2/R4 scope.

## Key Decisions Made
- Confirmed mathematical formulas and domain rules for Models 1 & 2.
- Established zero-refund invariant and idempotency guarantees for re-selection.
- Designed complete database migration and API specifications in report.md.

## Artifact Index
- `/workspaces/TheTextileCare/.agents/explorer_survey_phase7_3/DISPATCH.md` — Dispatch instructions
- `/workspaces/TheTextileCare/.agents/explorer_survey_phase7_3/BRIEFING.md` — Situational awareness
- `/workspaces/TheTextileCare/.agents/explorer_survey_phase7_3/progress.md` — Liveness & progress tracker
- `/workspaces/TheTextileCare/.agents/explorer_survey_phase7_3/report.md` — Comprehensive findings report
- `/workspaces/TheTextileCare/.agents/explorer_survey_phase7_3/handoff.md` — 5-component handoff report
