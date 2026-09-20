# Dispatch — Survey Explorer 2 (R1: Payment Abstraction & Timing, R3: Settlement Logic)

## Task Assignment
Read `/workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md` (specifically the section `## 2026-09-19T17:49:20Z`).
Investigate R1 (Payment Abstraction & Timing) and R3 (Settlement Logic) against the existing codebase at `/workspaces/TheTextileCare`:
1. R1: Payment requested only after customer approves actual pickup details (not at order creation).
   - How are pickup details submitted and approved?
   - How to support two modes for payment failure: required before pickup completion, or allowed as an outstanding receivable.
   - How to support two payment gateway scenarios: TTC Payment Gateway and Seller's own gateway.
   - Gateway fees and taxes recorded separately from TTC commissions.
   - Ensure OrderStatus is NOT overloaded with payment states (keep operational and payment states separate).
2. R3: Settlement Logic:
   - For TTC Payment Gateway: settlement model holding funds for 15-day cooling period and settling eligible amounts on Mondays.
   - For Seller-owned gateways: TTC does not impose holds or create settlement transfers.
3. Identify existing payment/transaction modules or lack thereof. Design proposed entities, state machines, interfaces, and migration strategies.
4. Output your analysis to `/workspaces/TheTextileCare/.agents/explorer_survey_phase7_2/report.md`.

## 2026-09-19T17:51:10Z
You are explorer_survey_phase7_2.
Your working directory is: /workspaces/TheTextileCare/.agents/explorer_survey_phase7_2
Read /workspaces/TheTextileCare/.agents/explorer_survey_phase7_2/DISPATCH.md and /workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md.
Investigate R1 (Payment Abstraction & Timing) and R3 (Settlement Logic) against the codebase at /workspaces/TheTextileCare.
Analyze how payment timing (post-pickup approval, failure modes), payment gateways (TTC vs Seller gateway, fee/tax separation), and settlement (15-day hold, Monday payout for TTC) should be structured and integrated without overloading OrderStatus.
Write your findings report to /workspaces/TheTextileCare/.agents/explorer_survey_phase7_2/report.md and your handoff to /workspaces/TheTextileCare/.agents/explorer_survey_phase7_2/handoff.md.
Keep progress.md updated. When finished, send a message to your caller.

