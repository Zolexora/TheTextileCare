# Dispatch — Explorer M1.3 (RBAC Permissions, Test Fixtures & Repositories)

## Task Assignment
Read:
- `/workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md` (specifically `## 2026-09-19T17:49:20Z`)
- `/workspaces/TheTextileCare/.agents/PROJECT.md` (specifically Milestone 1, Security, and Interface Contracts)
- Codebase files:
  - `backend/app/core/permissions/constants.py`
  - `backend/app/services/roles.py`
  - `backend/tests/conftest.py`

Investigate and design:
1. Permissions:
   - Define Phase 7 permissions in `PermissionName` (`backend/app/core/permissions/constants.py`):
     - `COMMERCIAL_READ = "commercial.read"`, `COMMERCIAL_MANAGE = "commercial.manage"`
     - `PAYMENT_READ = "payment.read"`, `PAYMENT_PROCESS = "payment.process"`
     - `BILLING_READ = "billing.read"`, `BILLING_MANAGE = "billing.manage"`
     - `SETTLEMENT_READ = "settlement.read"`, `SETTLEMENT_PROCESS = "settlement.process"`
   - Map permissions to `DEFAULT_ROLE_PERMISSIONS` for `PLATFORM_ADMIN`, `TENANT_ADMIN`, `SELLER_OWNER`, `SELLER_ADMIN`, `CUSTOMER`.
   - Update `ROLE_DESCRIPTIONS` in `backend/app/services/roles.py`.
2. Test Fixtures & Database Reset:
   - Verify `backend/tests/conftest.py`: ensure `import app.models` registers all Phase 7 models with `Base.metadata` so `reset_database` creates all tables seamlessly in test runs.
3. Multi-Tenant Repositories:
   - Design repository interfaces for `CommercialRepository`, `PickupRepository`, `PaymentRepository`, `BillingRepository`, `SettlementRepository` ensuring strict `tenant_id` query scoping.
4. Write your strategy report to `/workspaces/TheTextileCare/.agents/explorer_m1_3/report.md` and your handoff to `/workspaces/TheTextileCare/.agents/explorer_m1_3/handoff.md`.
