# BRIEFING — 2026-09-19T18:10:00Z

## Mission
Implement Phase 7 Milestone 1: Database Migration, Domain Models & RBAC Foundation for TTC Commercial Billing, Post-Pickup Payment Timing, Settlement & Seller Restrictions.

## 🔒 My Identity
- Archetype: worker
- Roles: implementer, qa, specialist
- Working directory: /workspaces/TheTextileCare/.agents/worker_m1_1
- Original parent: 6f64afd2-1d3a-42aa-aecd-e2488f1779ca
- Milestone: Milestone 1 - Pricing Engine Foundation
- Milestone Phase 7: Milestone 1 — Database Migration, Domain Models & RBAC Foundation
- Phase 7 Parent: 6b62fa2d-b0e1-4cea-9ad2-9f2593e98762

## 🔒 Key Constraints
- Exclusively owned files:
  - backend/app/core/permissions/constants.py
  - backend/app/services/roles.py
  - backend/tests/conftest.py
  - backend/app/models/pricing.py
  - backend/app/models/__init__.py
  - backend/migrations/versions/e7f1a2b3c4d5_phase5_pricing_engine.py
  - backend/app/schemas/pricing.py
  - backend/app/repositories/pricing.py
  - backend/tests/unit/test_pricing_models.py
- Minimal change principle. No unrelated refactoring.
- Zero regressions on existing tests.
- Down revision for Alembic migration must be 'ddf173e6fc96'.
- No hardcoded test results, facade implementations, or circumventing.
- Strict multi-tenant isolation on PriceBook and PriceRule.
- Phase 7 Scope & Ownership:
  - backend/migrations/versions/b2c3d4e5f6a7_phase7_commercial_billing_payment.py (down_revision = 'a1b2c3d4e5f6')
  - backend/app/models/pickup.py, commercial.py, payment.py, billing.py, order.py, __init__.py
  - backend/app/schemas/pickup.py, commercial.py, payment.py, billing.py, settlement.py, order.py
  - backend/app/core/permissions/constants.py & backend/app/services/roles.py
  - backend/app/repositories/pickup.py, commercial.py, payment.py, billing.py, settlement.py, __init__.py
  - backend/tests/conftest.py, tests/unit/test_phase7_models_schemas.py, tests/unit/test_phase7_repositories.py

## Current Parent
- Conversation ID: 6b62fa2d-b0e1-4cea-9ad2-9f2593e98762
- Updated: 2026-09-19T18:10:00Z

## Task Summary
- **What to build**: Phase 7 foundation:
  1. Alembic migration `b2c3d4e5f6a7` adding `reselected_from_order_id` to `orders`, tables `order_pickups`, `seller_commercial_configs`, `seller_billing_invoices`, `seller_settlements`, `payments`, `refunds`.
  2. SQLAlchemy 2.0 models for Pickup, Commercial, Payment, Billing, Order relationships, and exports.
  3. Pydantic v2 schemas for Pickup, Commercial, Payment, Billing, Settlement, and OrderReselectRequest.
  4. RBAC: 8 Phase 7 permissions, `RoleName.CUSTOMER`, `DEFAULT_ROLE_PERMISSIONS` matrix, role/permission descriptions.
  5. Multi-tenant Repositories with tenant scoping, `flush()`, no `commit()`.
  6. Unit tests verifying models, schemas, and repository multi-tenant isolation.
- **Success criteria**:
  - `alembic upgrade head` succeeds.
  - `alembic downgrade a1b2c3d4e5f6 && alembic upgrade head` succeeds.
  - `pytest tests/unit/test_phase7_*.py` passes 100%.
  - Existing test suite passes with 0 regressions.
- **Interface contracts**: PROJECT.md, Explorer M1 reports (explorer_m1_1, explorer_m1_2, explorer_m1_3).

## Key Decisions Made
- Use `sa.String(length=50)` with database-level `sa.CheckConstraint` for enums to ensure clean testing and schema evolution.
- Enforce unique constraint `(seller_id, invoice_month)` on `seller_billing_invoices`.
- Foreign key `orders.reselected_from_order_id` references `orders.id` with `ondelete='SET NULL'`.
- All repositories inherit `BaseRepository`, use `flush()`, never `commit()`.

## Artifact Index
- DISPATCH.md — Assignment instructions
- progress.md — Liveness heartbeat and step tracking
- handoff.md — Final handoff report

## Change Tracker
- **Files modified**: TBD
- **Build status**: In progress
- **Pending issues**: None

## Quality Status
- **Build/test result**: Pending verification
- **Lint status**: Pending
- **Tests added/modified**: Pending

## Loaded Skills
- None
