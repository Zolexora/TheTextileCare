# Project: TTC Phase 7 — Commercial Billing, Payment Timing, Settlement & Seller Restrictions

## Architecture
- **Layered Modular Monolith**: FastAPI, SQLAlchemy 2, Alembic, PostgreSQL (psycopg3).
- **Separation of Operational & Commercial Concerns (R5)**:
  - `OrderStatus` (`backend/app/models/order.py`): Strictly operational (`DRAFT`, `PENDING`, `CONFIRMED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`). Zero payment states on OrderStatus.
  - `PaymentStatus` (`backend/app/models/payment.py`): Tracks financial transaction lifecycle (`PENDING`, `SUCCEEDED`, `FAILED`, `OUTSTANDING`, `REFUNDED`, `PARTIALLY_REFUNDED`).
  - `InvoiceStatus` (`backend/app/models/billing.py`): Tracks monthly billing invoices (`PENDING`, `PAID`, `OVERDUE`, `CANCELLED`).
  - `SettlementStatus` (`backend/app/models/billing.py`): Tracks weekly Monday payout disbursements (`SCHEDULED`, `PROCESSING`, `SETTLED`, `FAILED`).
  - `SellerRestrictionLevel` (`backend/app/models/commercial.py`): Tracks operational compliance (`NONE`, `WARNING`, `MARKETPLACE_RESTRICTED`, `WHITE_LABEL_RESTRICTED`, `FULL_SUSPENSION`).
- **Payment Abstraction & Timing (R1)**:
  - Order placement (`POST /api/v1/orders`) validates pricing and creates snapshots in `PENDING` without charging.
  - Dedicated `OrderPickup` (`order_pickups`) tracks physical garment collection: `SCHEDULED` -> `DETAILS_SUBMITTED` -> `APPROVED` / `REJECTED` -> `COMPLETED`.
  - Customer approval of pickup details (`APPROVED`) is the sole trigger for payment requests.
  - Dual failure modes via `SellerCommercialConfiguration`:
    - Hard gate (`payment_required_before_pickup = True`): Payment failure blocks pickup completion and transition to `IN_PROGRESS`.
    - Permissive (`outstanding_receivable_allowed = True`): Pickup completes, order moves to `IN_PROGRESS`, payment set to `OUTSTANDING` with payment deadline.
  - Financial ledger separates third-party processor costs (`gateway_fee`, `gateway_tax`) from platform revenue (`ttc_commission`, `ttc_commission_tax`). Commission recalculates dynamically on retained amount (`amount - refunded_amount`).
- **Commercial Models & Monthly Billing (R2)**:
  - Mutually exclusive commercial models:
    - Model 1: Commission Percentage (`commission_rate_percent > 0`, `subscription_fee = 0`).
    - Model 2: Fixed Monthly Subscription (`subscription_fee > 0`, `commission_rate_percent = 0`).
  - Monthly billing statements (`SellerBillingInvoice`) generated per calendar month with unique constraint `(seller_id, invoice_month)`.
  - Daily late-payment penalty calculation: $(\text{subtotal} + \text{tax\_total}) \times \text{daily\_penalty\_rate} \times \text{days\_overdue}$ (idempotent).
- **Settlement Logic (R3)**:
  - `TTC_GATEWAY`: Customer funds held in platform custody; subject to a 15-day cooling hold from `Payment.paid_at`; eligible batches disbursed on Mondays via `SellerSettlement`.
  - `SELLER_GATEWAY`: Direct merchant settlement; TTC holds zero funds, enforces 0 cooling hold, and generates 0 settlement payouts.
- **Seller Restrictions & Marketplace Re-selection (R4)**:
  - Configurable overdue enforcement triggers `MARKETPLACE_RESTRICTED`.
  - Restricted sellers hidden from marketplace discovery.
  - Any `PENDING` marketplace order automatically transitions to `CANCELLED` with `cancellation_reason = "SELLER_RESTRICTED"`.
  - Existing operational orders (`CONFIRMED`, `IN_PROGRESS`) remain completely unaffected.
  - Customer seller re-selection (`POST /api/v1/orders/{order_id}/reselect`): Generates a new order linked via `new_order.reselected_from_order_id = original_order.id`. Zero refund needed (no payment occurred at `PENDING`). Idempotent single-reselection check.
- **Security & Idempotency (R5)**:
  - Strict tenant isolation via `TenantContext`. All queries scoped to `tenant_id`.
  - Idempotent financial operations via idempotency keys and unique constraints.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Phase 7 Alembic Migration | Migration `down_revision = 'a1b2c3d4e5f6'` creating `order_pickups`, `seller_commercial_configs`, `payments`, `refunds`, `seller_billing_invoices`, `seller_settlements`, and `orders.reselected_from_order_id` | M1 | Survey |
| 2 | Core Domain Models & Schemas | SQLAlchemy 2.0 models and Pydantic v2 schemas for Commercial, Pickup, Payment, and Billing domains | M1 | Survey |
| 3 | RBAC & Permission Registration | Define and seed Phase 7 permissions (`commercial.read`, `commercial.manage`, `payment.read`, `payment.process`, `billing.read`, `settlement.process`) | M1 | Survey |
| 4 | Order Pickup Decoupling | `OrderPickup` entity and lifecycle transitions (`SCHEDULED` -> `DETAILS_SUBMITTED` -> `APPROVED` / `REJECTED` -> `COMPLETED`) | M2 | Survey / R1 |
| 5 | Post-Pickup Payment Timing | Order creation does not charge; customer pickup approval triggers payment request | M2 | Survey / R1 |
| 6 | Dual Payment Failure Modes | Configurable hard gate (`payment_required_before_pickup`) vs permissive outstanding receivable (`outstanding_receivable_allowed`) | M2 | Survey / R1 |
| 7 | Payment Gateway Abstraction | Support `TTC_GATEWAY` and `SELLER_GATEWAY` transaction processing | M2 | Survey / R1 |
| 8 | Financial Ledger Fee/Tax Separation | Separate columns for `gateway_fee`, `gateway_tax`, `ttc_commission`, `ttc_commission_tax` | M2 | Survey / R1 |
| 9 | Refund & Retained Amount Commission Recalculation | Retained amount tracking with proportional commission deduction on partial/full refunds | M2 | Survey / R1 |
| 10 | Payment REST Endpoints | Pickup submission/approval and payment execution/status REST endpoints | M2 | Survey / R1 |
| 11 | Mutually Exclusive Commercial Models | Model 1 (Commission %) vs Model 2 (Monthly Subscription) validation and persistence | M3 | Survey / R2 |
| 12 | Monthly Billing Invoice Engine | Calendar month invoice generation with unique `(seller_id, invoice_month)` and configurable due dates | M3 | Survey / R2 |
| 13 | Idempotent Daily Late Penalties | Daily penalty formula: $(\text{subtotal} + \text{tax\_total}) \times \text{daily\_penalty\_rate} \times \text{days\_overdue}$ | M3 | Survey / R2 |
| 14 | Commercial & Billing REST APIs | Admin endpoints for commercial configs and seller endpoints for billing invoices | M3 | Survey / R2 |
| 15 | TTC 15-Day Cooling Hold Engine | Filter `Payment.paid_at <= now - 15 days` for platform gateway funds | M4 | Survey / R3 |
| 16 | Monday Settlement Payout Batching | Batch eligible cooling-cleared funds into weekly Monday `SellerSettlement` payouts | M4 | Survey / R3 |
| 17 | Seller Gateway Direct Bypass | Verify `SELLER_GATEWAY` transactions bypass platform hold and settlement creation | M4 | Survey / R3 |
| 18 | Settlement REST & Execution APIs | Settlement preview, manual trigger, and listing endpoints | M4 | Survey / R3 |
| 19 | Overdue Seller Restriction Levels | Transition to `WARNING`, `MARKETPLACE_RESTRICTED`, `FULL_SUSPENSION` based on overdue invoices | M5 | Survey / R4 |
| 20 | Marketplace Discovery Suppression | Filter restricted sellers out of marketplace discovery queries | M5 | Survey / R4 |
| 21 | Automated PENDING Order Cancellation | Automatically cancel all `PENDING` marketplace orders with `cancellation_reason = "SELLER_RESTRICTED"` | M5 | Survey / R4 |
| 22 | Preservation of Operational Orders | Verify `CONFIRMED` and `IN_PROGRESS` orders remain unaffected when seller is restricted | M5 | Survey / R4 |
| 23 | Customer Seller Re-selection API | `POST /api/v1/orders/{order_id}/reselect` creating new order linked via `reselected_from_order_id` | M5 | Survey / R4 |
| 24 | Zero-Refund Re-selection Invariant | Confirm no gateway refund is issued on re-selection since cancelled `PENDING` orders were uncharged | M5 | Survey / R4 |
| 25 | Full Verification & E2E Acceptance | Pass 100% E2E tests (Tiers 1-4), adversarial hardening (Tier 5), full pytest suite, alembic migrations, lint & typecheck | M6 | Survey / R5 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Database Migration, Domain Models & RBAC Foundation | Alembic migration, SQLAlchemy models (`order_pickups`, `seller_commercial_configs`, `payments`, `refunds`, `seller_billing_invoices`, `seller_settlements`, `orders.reselected_from_order_id`), Pydantic schemas, RBAC permissions | none | PLANNED |
| M2 | Payment Abstraction, Pickup Decoupling & Timing Engine | `OrderPickup` workflow, post-pickup approval payment trigger, dual failure modes, fee/tax ledger separation, refunds & retained amount commissions, Payment APIs | M1 | PLANNED |
| M3 | Commercial Models & Monthly Billing System | Mutually exclusive models (Commission % vs Subscription), monthly billing invoice generation, idempotent daily late penalties, Commercial & Billing APIs | M1 | PLANNED |
| M4 | Settlement Logic & Monday Payout Engine | 15-day cooling hold, weekly Monday batch payouts for `TTC_GATEWAY`, seller gateway bypass, Settlement APIs | M2, M3 | PLANNED |
| M5 | Seller Overdue Restrictions & Marketplace Re-selection | Configurable overdue enforcement, discovery suppression, auto-cancel `PENDING` orders (`SELLER_RESTRICTED`), preserve operational orders, customer re-selection endpoint (`reselected_from_order_id`) | M2, M3 | PLANNED |
| M6 | Final Milestone: E2E Verification & Adversarial Hardening | Pass 100% E2E test suite (Tiers 1-4), adversarial test hardening (Tier 5), pytest suite, alembic upgrade, linting, typechecking | M4, M5, E2E Test Suite | PLANNED |

## Dual Track: E2E Testing Track
- **E2E Testing Track Orchestrator**:
  - Scope: Test infrastructure and comprehensive opaque-box test cases derived directly from requirements in `ORIGINAL_REQUEST.md`.
  - Tiers:
    - Tier 1: Feature coverage (≥5 test cases per feature across R1-R5).
    - Tier 2: Boundary & Corner cases (≥5 test cases per feature).
    - Tier 3: Cross-feature pairwise interactions (Payment timing × Gateway type × Commercial model × Restriction state).
    - Tier 4: Real-world application scenarios (Full customer journey: order -> pickup approval -> payment -> settlement / restriction -> re-selection).
  - Deliverables: `TEST_INFRA.md`, test runner and test cases, `TEST_READY.md`.

## Interface Contracts

### M1 ↔ M2, M3, M4, M5: Schema & Model Contracts
- `OrderPickup`:
  - `id: UUID`, `tenant_id: UUID`, `order_id: UUID`, `seller_id: UUID`, `status: PickupStatus` (`SCHEDULED`, `DETAILS_SUBMITTED`, `APPROVED`, `REJECTED`, `COMPLETED`), `actual_pickup_at: datetime | None`, `details_submitted_at: datetime | None`, `approved_at: datetime | None`, `rejection_reason: str | None`, `actual_details: dict | None`.
- `SellerCommercialConfiguration`:
  - `id: UUID`, `tenant_id: UUID`, `seller_id: UUID`, `commercial_model: SellerCommercialModel` (`COMMISSION`, `SUBSCRIPTION`), `commission_rate_percent: Decimal`, `subscription_fee: Decimal`, `payment_gateway_type: PaymentGatewayType` (`TTC_GATEWAY`, `SELLER_GATEWAY`), `payment_required_before_pickup: bool`, `outstanding_receivable_allowed: bool`, `payment_deadline_days: int`, `restriction_level: SellerRestrictionLevel` (`NONE`, `WARNING`, `MARKETPLACE_RESTRICTED`, `WHITE_LABEL_RESTRICTED`, `FULL_SUSPENSION`), `overdue_grace_days: int`, `daily_penalty_rate: Decimal`.
- `Payment`:
  - `id: UUID`, `tenant_id: UUID`, `order_id: UUID`, `seller_id: UUID`, `gateway_type: PaymentGatewayType`, `status: PaymentStatus` (`PENDING`, `SUCCEEDED`, `FAILED`, `OUTSTANDING`, `REFUNDED`, `PARTIALLY_REFUNDED`), `currency: str`, `amount: Decimal`, `gateway_fee: Decimal`, `gateway_tax: Decimal`, `ttc_commission: Decimal`, `ttc_commission_tax: Decimal`, `refunded_amount: Decimal`, `retained_amount: Decimal`, `settled: bool`, `settlement_id: UUID | None`, `paid_at: datetime | None`, `due_date: datetime | None`.
- `Refund`:
  - `id: UUID`, `tenant_id: UUID`, `payment_id: UUID`, `amount: Decimal`, `reason: str`, `commission_deduction: Decimal`, `created_at: datetime`.
- `SellerBillingInvoice`:
  - `id: UUID`, `tenant_id: UUID`, `seller_id: UUID`, `invoice_month: str` ("YYYY-MM"), `status: InvoiceStatus` (`PENDING`, `PAID`, `OVERDUE`, `CANCELLED`), `subtotal: Decimal`, `tax_total: Decimal`, `penalty_total: Decimal`, `total_amount: Decimal`, `due_date: date`, `paid_at: datetime | None`.
- `SellerSettlement`:
  - `id: UUID`, `tenant_id: UUID`, `seller_id: UUID`, `gateway_type: PaymentGatewayType`, `status: SettlementStatus` (`SCHEDULED`, `PROCESSING`, `SETTLED`, `FAILED`), `currency: str`, `amount: Decimal`, `scheduled_for: date`, `processed_at: datetime | None`.
- `Order`:
  - Existing attributes + `reselected_from_order_id: UUID | None` (FK `orders.id`).

### M2 ↔ M3, M4, M5: Payment & Pickup Service Contracts
- `PaymentService`:
  - `create_payment_request(ctx, order_id) -> PaymentResponse` (invoked when pickup is approved)
  - `process_payment(ctx, payment_id, action: PaymentAction) -> PaymentResult`
  - `process_refund(ctx, payment_id, refund_amount, reason) -> RefundResponse`
  - `get_payment_by_order(ctx, order_id) -> PaymentResponse | None`
- `PickupService`:
  - `submit_pickup_details(ctx, order_id, actual_details) -> PickupResponse`
  - `approve_pickup_details(ctx, order_id) -> PickupResponse` (triggers payment creation)
  - `reject_pickup_details(ctx, order_id, reason) -> PickupResponse`
  - `complete_pickup(ctx, order_id) -> PickupResponse` (enforces failure mode checks)

### M3 ↔ M4, M5: Commercial & Billing Service Contracts
- `CommercialService`:
  - `get_or_create_config(ctx, seller_id) -> SellerCommercialConfiguration`
  - `update_config(ctx, seller_id, data: CommercialConfigUpdate) -> SellerCommercialConfiguration`
- `BillingService`:
  - `generate_monthly_invoices(ctx, year: int, month: int) -> list[SellerBillingInvoice]`
  - `calculate_overdue_penalties(ctx, as_of_date: date) -> list[SellerBillingInvoice]`
  - `mark_invoice_paid(ctx, invoice_id) -> SellerBillingInvoice`

### M4: Settlement Service Contract
- `SettlementService`:
  - `generate_monday_settlements(ctx, target_date: date) -> list[SellerSettlement]`
    - Filters: `gateway_type == TTC_GATEWAY`, `status == SUCCEEDED`, `settled == False`, `paid_at <= target_date - 15 days`.
  - `process_settlements(ctx, settlement_ids) -> list[SellerSettlement]`

### M5: Restriction & Re-selection Service Contracts
- `SellerRestrictionService`:
  - `evaluate_and_apply_restrictions(ctx) -> dict`
    - Evaluates overdue days -> updates `SellerCommercialConfiguration.restriction_level`.
    - If `MARKETPLACE_RESTRICTED` or `FULL_SUSPENSION`: auto-cancels `PENDING` marketplace orders with `cancellation_reason = "SELLER_RESTRICTED"`.
- `OrderReselectionService`:
  - `reselect_seller(ctx, original_order_id: UUID, new_seller_id: UUID, new_branch_id: UUID) -> OrderResponse`
    - Precondition: `original_order.status == CANCELLED` and `original_order.cancellation_reason == "SELLER_RESTRICTED"`.
    - Prevents double reselection.
    - Zero refund (no payment collected).
    - Creates new order with `reselected_from_order_id = original_order_id`.

## Code Layout
- Backend Models & Schema:
  - `backend/app/models/commercial.py`: Commercial configs & restriction enums
  - `backend/app/models/pickup.py`: OrderPickup model & PickupStatus enum
  - `backend/app/models/payment.py`: Payment, Refund models & PaymentStatus enum
  - `backend/app/models/billing.py`: SellerBillingInvoice, SellerSettlement models & Invoice/Settlement status enums
  - `backend/app/models/order.py`: Order model with `reselected_from_order_id`
  - `backend/app/models/__init__.py`: Export all models
  - `backend/migrations/versions/<rev>_phase7_commercial_billing_payment.py`: Alembic migration
- Backend Schemas:
  - `backend/app/schemas/commercial.py`
  - `backend/app/schemas/pickup.py`
  - `backend/app/schemas/payment.py`
  - `backend/app/schemas/billing.py`
  - `backend/app/schemas/settlement.py`
- Backend Repositories & Services:
  - `backend/app/repositories/commercial.py`
  - `backend/app/repositories/pickup.py`
  - `backend/app/repositories/payment.py`
  - `backend/app/repositories/billing.py`
  - `backend/app/repositories/settlement.py`
  - `backend/app/services/commercial.py`
  - `backend/app/services/pickup.py`
  - `backend/app/services/payment.py`
  - `backend/app/services/billing.py`
  - `backend/app/services/settlement.py`
  - `backend/app/services/seller_restriction.py`
  - `backend/app/services/order.py`: Integration for re-selection and restriction checks
- Backend API Routers:
  - `backend/app/api/v1/commercial.py`: `/api/v1/commercial`
  - `backend/app/api/v1/pickups.py`: `/api/v1/orders/{order_id}/pickup`
  - `backend/app/api/v1/payments.py`: `/api/v1/payments`
  - `backend/app/api/v1/billing.py`: `/api/v1/billing`
  - `backend/app/api/v1/settlements.py`: `/api/v1/settlements`
  - `backend/app/api/v1/orders.py`: Add `POST /api/v1/orders/{order_id}/reselect`
  - `backend/app/api/router.py`: Router registrations
- Tests:
  - `backend/tests/unit/test_commercial.py`
  - `backend/tests/unit/test_pickup.py`
  - `backend/tests/unit/test_payment.py`
  - `backend/tests/unit/test_billing.py`
  - `backend/tests/unit/test_settlement.py`
  - `backend/tests/unit/test_restrictions.py`
  - `backend/tests/api/test_phase7_e2e.py`
  - `tests/e2e/test_phase7_full_lifecycle.py`
