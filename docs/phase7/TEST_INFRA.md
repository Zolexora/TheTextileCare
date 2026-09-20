# TTC Phase 7: Commercial Billing, Payment Timing, Settlement & Seller Restrictions — Test Infrastructure Specification (TEST_INFRA.md)

**Document Version**: 1.0.0  
**Target Milestone**: Phase 7 — Commercial Billing, Payment Timing, Settlement & Seller Restrictions  
**Authoritative Locations**:  
- `/workspaces/TheTextileCare/TEST_INFRA.md`  
- `/workspaces/TheTextileCare/.agents/TEST_INFRA.md`  
**Test Suite Directory**: `/workspaces/TheTextileCare/backend/tests/e2e/`  

---

## 1. Test Philosophy & Core Invariants

The testing infrastructure for Phase 7 of TheTextileCare (TTC) platform is engineered to validate commercial, financial, and operational integrity across real-world laundry and dry cleaning workflows. It adheres to six foundational principles:

### 1.1 Strict Opaque-Box Verification
Tests interact with the platform primarily through HTTP endpoints using FastAPI's `TestClient` and through domain service contracts when executing isolated business logic. Tests treat internal repositories and ORM plumbing as black boxes, validating observable HTTP response codes, response envelopes, database side-effects, audit events, and ledger records.

### 1.2 Non-Overloaded OrderStatus Separation (R5)
A non-negotiable architectural invariant: `OrderStatus` MUST NOT be overloaded with financial states.
- `OrderStatus` tracks the physical garment lifecycle: `DRAFT` $\to$ `PENDING` $\to$ `CONFIRMED` $\to$ `IN_PROGRESS` $\to$ `COMPLETED` (or `CANCELLED`).
- `PaymentStatus` tracks the financial ledger lifecycle: `PENDING` $\to$ `SUCCEEDED` / `FAILED` $\to$ `OUTSTANDING` $\to$ `REFUNDED` / `PARTIALLY_REFUNDED`.
- `InvoiceStatus` tracks monthly platform receivables: `PENDING` $\to$ `PAID` / `OVERDUE` / `CANCELLED`.
- `SettlementStatus` tracks weekly payout disbursements: `SCHEDULED` $\to$ `PROCESSING` $\to$ `SETTLED` / `FAILED`.
- `SellerRestrictionLevel` tracks marketplace compliance: `NONE` $\to$ `WARNING` $\to$ `MARKETPLACE_RESTRICTED` $\to$ `WHITE_LABEL_RESTRICTED` $\to$ `FULL_SUSPENSION`.

### 1.3 Post-Pickup Payment Timing (R1)
Garment quantities, stains, and weights (e.g. wash & fold kilograms) cannot be finalized until physical pickup. Therefore:
1. Placing an order (`POST /api/v1/orders`) creates the order in `OrderStatus.PENDING` with **zero initial payment charge** and zero payment records.
2. Sellers/drivers inspect and submit verified pickup counts/weights (`details_submitted`).
3. Customer approves actual pickup details (`approved`).
4. **Payment request is initiated ONLY upon customer approval of pickup details.**

### 1.4 Absolute Mathematical Determinism & Decimal Precision
Monetary calculations never use floating-point types. All amounts, fees, commissions, taxes, penalties, and retained amounts use Python `Decimal` with `ROUND_HALF_UP` quantized to 2 decimal places (`Decimal('0.01')`):
- `retained_amount = amount - refunded_amount`
- `ttc_commission = round_half_up(retained_amount * commission_rate_percent / 100, 2)`
- `daily_penalty = round_half_up((subtotal + tax_total) * (daily_late_penalty_rate_percent / 100) * days_overdue, 2)`

### 1.5 Zero-Refund Re-selection Invariant (R4)
When a seller is restricted due to overdue billing invoices:
- `PENDING` marketplace orders are automatically cancelled with `cancellation_reason = "SELLER_RESTRICTED"`.
- Because payment is only triggered after pickup approval, `PENDING` orders have zero collected funds.
- Re-selecting an alternative seller (`POST /api/v1/orders/{order_id}/reselect`) issues **zero payment refunds**, links `new_order.reselected_from_order_id = original_order.id`, and creates a new order in `PENDING`.
- Existing operational orders (`CONFIRMED`, `IN_PROGRESS`) are preserved to prevent customer laundry stranding.

### 1.6 Strict Multi-Tenant Isolation (R5)
All payment records, commercial configs, billing invoices, and settlement batches are strictly isolated by `tenant_id` and `seller_id`. Cross-tenant mutations or queries return `404 Not Found` or `403 Forbidden`.

---

## 2. Test Architecture & Tier Layering

The test suite is structured into 4 hierarchical tiers in `backend/tests/e2e/`:

```
backend/tests/e2e/
├── __init__.py
├── conftest.py                             # Common fixtures, database reset, authentication & world factories
├── test_phase7_tier1_features.py          # Tier 1: Primary Happy Paths per Feature (>=5 tests per feature, 20 features)
├── test_phase7_tier2_boundaries.py        # Tier 2: Boundary & Corner Cases (>=5 tests per boundary domain)
├── test_phase7_tier3_combinations.py      # Tier 3: Multi-Dimensional Pairwise Combinations
└── test_phase7_tier4_workloads.py         # Tier 4: Realistic End-to-End User Journeys
```

### 2.1 Tier Definitions & Objectives

| Tier | File | Primary Scope | Min. Tests |
| :--- | :--- | :--- | :--- |
| **Tier 1** | `test_phase7_tier1_features.py` | Isolated feature verification across R1–R5 (happy paths, state changes, exact mathematical calculations). | ≥100 tests (≥5 per feature across 20 features) |
| **Tier 2** | `test_phase7_tier2_boundaries.py` | Boundary and edge condition stress: exact 15-day cooling limits, calendar Monday payouts, 0-day overdue penalties, 100% and 1-cent refunds, boundary commission rates (0.01%, 99.99%), invalid re-selections, and cross-tenant rejections. | ≥40 tests (≥5 per boundary domain) |
| **Tier 3** | `test_phase7_tier3_combinations.py` | Pairwise combination testing: Gateway Type (`TTC_GATEWAY` vs `SELLER_GATEWAY`) $\times$ Commercial Model (`COMMISSION` vs `SUBSCRIPTION`) $\times$ Failure Mode (Hard Gate vs Permissive) $\times$ Restriction Level (`NONE` vs `MARKETPLACE_RESTRICTED`). | ≥16 combination matrices |
| **Tier 4** | `test_phase7_tier4_workloads.py` | Realistic multi-actor business workloads: full customer lifecycle, seller gateway subscription lifecycle, payment failure & retry, restriction discovery suppression & re-selection, and damaged garment refund settlement reconciliation. | ≥5 comprehensive workflows |

---

## 3. Phase 7 Feature Inventory (Features 1 – 20)

| ID | Domain | Feature Name | Description | Authoritative Rule |
| :--- | :--- | :--- | :--- | :--- |
| **F-01** | R1 | Zero Payment at Order Creation | Order placed via `POST /api/v1/orders` enters `PENDING` with no charge or payment transaction. | `OrderStatus.PENDING`, zero payment transactions created. |
| **F-02** | R1 | Post-Pickup Approval Payment Trigger | Submitting pickup details and customer approval triggers payment request creation. | `PickupStatus.APPROVED` creates `Payment` in `PENDING`. |
| **F-03** | R1 | Payment Failure Mode 1: Hard Gate | `payment_required_before_pickup = True` blocks pickup completion and transition to `IN_PROGRESS` if payment fails. | HTTP 409 / Domain block; order remains `CONFIRMED`. |
| **F-04** | R1 | Payment Failure Mode 2: Permissive | `outstanding_receivable_allowed = True` allows pickup completion and transitions payment to `OUTSTANDING`. | Order enters `IN_PROGRESS`; `PaymentStatus.OUTSTANDING` set with `due_date`. |
| **F-05** | R1 | Dual Gateway Accounting | Separate ledger columns for processor costs (`gateway_fee`, `gateway_tax`) vs platform revenue (`ttc_commission`, `ttc_commission_tax`). | Numeric(10, 2) exact separate columns on `Payment`. |
| **F-06** | R1 | Proportional Commission on Refunds | Platform commission recalculated on `retained_amount = amount - refunded_amount`. | Full refund $\implies$ commission 0.00; partial refund $\implies$ reduced commission. |
| **F-07** | R2 | Mutually Exclusive Commercial Models | Model 1 (`COMMISSION` with `rate > 0`, `sub = 0`) vs Model 2 (`SUBSCRIPTION` with `sub > 0`, `rate = 0`). | Mutual exclusivity enforced at entity and service layer. |
| **F-08** | R2 | Monthly Billing Statements | Monthly invoice generation (`SellerBillingInvoice`) with unique constraint `(seller_id, invoice_month)`. | Generated per calendar month; duplicate generation prevented. |
| **F-09** | R2 | Idempotent Daily Late Penalties | Daily penalty formula: $(P) \times r \times D$ where $P = \text{subtotal} + \text{tax}$, $r = \text{daily\_rate}$, $D = \text{days\_overdue}$. | Recalculating on same day yields exact same penalty. |
| **F-10** | R3 | 15-Day Cooling Hold Engine | Funds from `TTC_GATEWAY` held for 15 days from `paid_at` before settlement eligibility. | Eligible on `target_date` if `paid_at <= target_date - 15 days`. |
| **F-11** | R3 | Weekly Monday Settlement Payouts | Batching eligible cooling-cleared funds into weekly Monday `SellerSettlement` records. | Payout scheduled on Mondays (`target_date.weekday() == 0`). |
| **F-12** | R3 | Seller Gateway Direct Bypass | `SELLER_GATEWAY` transactions bypass platform custody; zero cooling hold, zero settlement transfers. | `SellerSettlement` is NOT created for seller gateway payments. |
| **F-13** | R4 | Overdue Seller Restriction Levels | Transition to `WARNING`, `MARKETPLACE_RESTRICTED`, `FULL_SUSPENSION` based on overdue invoice days. | Overdue days $\ge$ threshold updates `restriction_level`. |
| **F-14** | R4 | Auto-Cancellation of PENDING Orders | Entering `MARKETPLACE_RESTRICTED` automatically cancels `PENDING` marketplace orders with reason `SELLER_RESTRICTED`. | `status = CANCELLED`, `cancellation_reason = "SELLER_RESTRICTED"`. |
| **F-15** | R4 | Preservation of Operational Orders | Ongoing orders (`CONFIRMED`, `IN_PROGRESS`) are preserved and unaffected by seller restriction. | Operational orders continue to completion. |
| **F-16** | R4 | Customer Seller Re-Selection API | `POST /api/v1/orders/{order_id}/reselect` creates new order linked via `reselected_from_order_id`. | Links to original cancelled order; fresh pricing recalculated. |
| **F-17** | R4 | Zero-Refund Re-selection Invariant | Re-selection of cancelled `PENDING` orders triggers no payment refunds. | Zero refund emitted since customer was not charged at `PENDING`. |
| **F-18** | R5 | Orthogonal Status Separation | Complete separation of `OrderStatus`, `PaymentStatus`, `InvoiceStatus`, `SettlementStatus`, and `SellerRestrictionLevel`. | No cross-pollution of enum domains. |
| **F-19** | R5 | Strict Multi-Tenant Data Isolation | Reject cross-tenant and cross-seller access attempts across all endpoints and queries. | Returns 404/403 on cross-tenant operations. |
| **F-20** | R5 | Financial Idempotency | Repeated payment captures, penalty updates, or settlement batch runs remain strictly idempotent. | Prevents double billing, duplicate payout, or duplicate penalties. |

---

## 4. Authoritative Mathematical Specifications

### 4.1 Commission and Retained Amount Math
$$\text{retained\_amount} = \text{amount} - \text{refunded\_amount}$$
$$\text{ttc\_commission} = \text{round\_half\_up}\left( \text{retained\_amount} \times \frac{\text{commission\_rate\_percent}}{100}, 2 \right)$$
$$\text{ttc\_commission\_tax} = \text{round\_half\_up}\left( \text{ttc\_commission} \times \frac{\text{tax\_rate\_percent}}{100}, 2 \right)$$

### 4.2 Daily Overdue Penalty Math
$$P = \text{invoice.subtotal} + \text{invoice.tax\_total}$$
$$D = \max(0, (\text{as\_of\_date} - \text{invoice.due\_date}).\text{days})$$
$$r = \frac{\text{daily\_late\_penalty\_rate\_percent}}{100}$$
$$\text{penalty\_total} = \text{round\_half\_up}(P \times r \times D, 2)$$
$$\text{total\_amount} = P + \text{penalty\_total}$$

### 4.3 15-Day Cooling Hold & Monday Settlement
$$\text{Eligible Date} = \text{Payment.paid\_at}.\text{date}() + 15\text{ days}$$
$$\text{Payment is Eligible on Date } T \iff \text{Payment.gateway\_type} == \text{TTC\_GATEWAY} \land \text{Payment.status} == \text{SUCCEEDED} \land \text{Payment.settled} == \text{False} \land \text{Eligible Date} \le T$$
$$\text{Settlement Valid Day } T \iff T.\text{weekday}() == 0 \quad (\text{Monday})$$

---

## 5. Test Execution & Verification Protocol

### 5.1 Test Execution Command
Tests are executed sequentially with the project virtual environment runner:

```bash
# Run all Phase 7 E2E tests
/workspaces/TheTextileCare/.venv/bin/pytest backend/tests/e2e/test_phase7_*.py -v

# Run individual tiers
/workspaces/TheTextileCare/.venv/bin/pytest backend/tests/e2e/test_phase7_tier1_features.py -v
/workspaces/TheTextileCare/.venv/bin/pytest backend/tests/e2e/test_phase7_tier2_boundaries.py -v
/workspaces/TheTextileCare/.venv/bin/pytest backend/tests/e2e/test_phase7_tier3_combinations.py -v
/workspaces/TheTextileCare/.venv/bin/pytest backend/tests/e2e/test_phase7_tier4_workloads.py -v
```

### 5.2 Quality Gates
- **100% Assertion Determinism**: All calculations matched to exact `0.01` precision.
- **Zero Flakiness**: Tests must run deterministically with clean database setup.
- **Coverage**: Every one of the 20 features covered by $\ge 5$ tests in Tier 1; all boundary domains covered by $\ge 5$ tests in Tier 2; pairwise matrix tested in Tier 3; $\ge 5$ realistic workflows in Tier 4.
