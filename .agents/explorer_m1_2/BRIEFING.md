# BRIEFING — 2026-09-19T18:00:50Z

## Mission
Investigate and design SQLAlchemy 2.0 domain models (including OrderPickup in pickup.py, Payment, Refund, SellerBillingInvoice, SellerSettlement, SellerCommercialConfiguration) and Pydantic v2 schemas for Commercial, Pickup, Payment, and Billing domains for TTC Phase 7.

## 🔒 My Identity
- Archetype: explorer
- Roles: investigator, architect, blueprint designer
- Working directory: /workspaces/TheTextileCare/.agents/explorer_m1_2
- Original parent: 6f64afd2-1d3a-42aa-aecd-e2488f1779ca
- Milestone: Milestone 1 - Models, Enums & Alembic Migration Strategy
- Phase 7 Parent: 6b62fa2d-b0e1-4cea-9ad2-9f2593e98762
- Phase 7 Milestone: Milestone 1 - Domain Models & Pydantic Schemas

## 🔒 Key Constraints
- Read-only investigation — do NOT implement or modify source code files
- Down_revision must strictly be 'ddf173e6fc96'
- Models must adhere to SQLAlchemy 2.0 style (Mapped, mapped_column, Base from app.models.base)
- Deliver report to /workspaces/TheTextileCare/.agents/explorer_m1_2/strategy_models_migration.md
- Deliver handoff to /workspaces/TheTextileCare/.agents/explorer_m1_2/handoff.md
- Phase 7: Read-only investigation — do NOT modify backend source code directly
- Phase 7: Deliver strategy report to /workspaces/TheTextileCare/.agents/explorer_m1_2/report.md
- Phase 7: Deliver handoff to /workspaces/TheTextileCare/.agents/explorer_m1_2/handoff.md
- Phase 7: Keep progress.md updated

## Current Parent
- Conversation ID: 6b62fa2d-b0e1-4cea-9ad2-9f2593e98762
- Updated: 2026-09-19T18:00:50Z

## Investigation State
- **Explored paths**:
  - `backend/app/models/commercial.py`
  - `backend/app/models/payment.py`
  - `backend/app/models/billing.py`
  - `backend/app/models/order.py`
  - `backend/app/models/__init__.py`
  - `backend/app/schemas/`
  - `.agents/PROJECT.md`, `.agents/ORIGINAL_REQUEST.md`
  - `.agents/explorer_survey_phase7_2/report.md`
  - `.agents/explorer_survey_phase7_3/report.md`
- **Key findings**:
  - `commercial.py`, `payment.py`, and `billing.py` have initial draft models in working tree, but have structural omissions (`seller_id`, `paid_at`, `due_date`, `seller_settlement_id` on Payment; missing `OrderPickup` in `pickup.py`).
  - `OrderPickup` entity does not exist yet. Needs to be designed in `backend/app/models/pickup.py` with `PickupStatus` enum (`SCHEDULED`, `DETAILS_SUBMITTED`, `APPROVED`, `REJECTED`, `COMPLETED`).
  - `Order.reselected_from_order_id` column is already mapped on `Order`, but needs relationship/foreign key review.
  - Pydantic v2 schemas are missing for `commercial.py`, `pickup.py`, `payment.py`, `billing.py`, and `settlement.py`.
- **Unexplored areas**:
  - Deep-dive into existing Pydantic schemas in `backend/app/schemas/` to ensure 100% stylistic consistency (BaseModel, ConfigDict, Field, uuid, Decimal, datetime).
  - Exact column types, lengths, constraints, and relationship references.

## Key Decisions Made
- Use Pydantic v2 `ConfigDict(from_attributes=True)` and strict type hints.
- Separate schemas into Base, Create, Update, Response models per domain.
- Verify exact foreign keys and indexes to prevent migration conflicts.

## Artifact Index
- `/workspaces/TheTextileCare/.agents/explorer_m1_2/report.md` — Authoritative Phase 7 Domain Models & Schemas Strategy Report
- `/workspaces/TheTextileCare/.agents/explorer_m1_2/handoff.md` — 5-component handoff report
- `/workspaces/TheTextileCare/.agents/explorer_m1_2/progress.md` — Heartbeat progress tracker
