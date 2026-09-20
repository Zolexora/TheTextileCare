# Comprehensive Strategy Report: Alembic Migration & Schema Foundation (Phase 7)

**Author**: `explorer_m1_1`  
**Date**: 2026-09-19  
**Target Milestone**: Milestone 1 (M1 — Database Migration, Domain Models & RBAC Foundation)  
**Task Scope**: Alembic Migration Chain Investigation & Migration Design for Phase 7 Commercial, Billing, Payment, and Reselection Foundation  
**Output Target**: `/workspaces/TheTextileCare/.agents/explorer_m1_1/report.md`  

---

## 1. Executive Summary

This report establishes the authoritative architectural blueprint and migration specification for **Phase 7 (Commercial Billing, Payment Timing, Settlement & Seller Restrictions)** of the **TheTextileCare (TTC)** platform.

Phase 7 builds directly on top of the Order Foundation established in revision `a1b2c3d4e5f6` (`phase7_order_foundation`). The database schema must be extended to support:
1. **Physical Order Pickup Lifecycle Tracking** (`order_pickups`) decoupled from order creation.
2. **Seller Commercial Models & Restriction Configurations** (`seller_commercial_configs`) supporting mutually exclusive Commission (%) vs Monthly Subscription models, dual gateway routing (`TTC_GATEWAY` vs `SELLER_GATEWAY`), and overdue restriction levels.
3. **Financial Transaction & Escrow Ledger** (`payments`) with distinct fields for gateway processing costs, taxes, platform commission, 15-day cooling period tracking, and settlement linking.
4. **Refund Ledger & Commission Rebalancing** (`refunds`) recording partial and full refunds with proportional commission clawbacks.
5. **Monthly Seller Billing Engine** (`seller_billing_invoices`) with calendar-month uniqueness `(seller_id, invoice_month)`, due date enforcement, and daily late-payment penalty accumulators.
6. **Platform Payout Disbursement Engine** (`seller_settlements`) tracking batch Monday transfers to sellers for cooling-cleared `TTC_GATEWAY` customer funds.
7. **Order Reselection Linkage** (altering `orders` to add `reselected_from_order_id` referencing `orders.id` ondelete `SET NULL`), enabling zero-refund reselection when restricted sellers cause cancellation of pending orders.

This document details the migration dependency graph, PostgreSQL data types, check constraints, foreign keys, cascade semantics, performance indexes, and provides the complete drop-in migration script (`b2c3d4e5f6a7_phase7_commercial_billing_payment.py`).

---

## 2. Alembic Migration Chain Topology

### 2.1 Historical Lineage
The Alembic migration history in `backend/migrations/versions/` constitutes a single strictly-linear sequence:

```
[<base>]
   │
   ▼
0001_phase1 (Phase 1: identity, tenancy, membership, rbac, audit schema)
   │
   ▼
2010fc7ee67f (Phase 2: sellers, seller_branches, seller_settings, seller_staff_profiles)
   │
   ▼
debba6592524 (Phase 2 hardening: business_hours)
   │
   ▼
275f700c133f (Phase 3: applications, modules, configuration definitions & values)
   │
   ▼
ddf173e6fc96 (Phase 4: catalogs, categories, services, items, addons, branch availability)
   │
   ▼
e7f1a2b3c4d5 (Phase 5: price_books, price_rules)
   │
   ▼
112e2205a754 (Phase 6: customers, customer_addresses, customer_sellers)
   │
   ▼
a1b2c3d4e5f6 (Phase 7 Part 1: order_number_seq, orders, order_items, order_item_addons, order_status_history) [CURRENT HEAD]
   │
   ▼
b2c3d4e5f6a7 (Phase 7 Part 2: commercial configs, pickups, payments, refunds, invoices, settlements, order reselection) [NEW TARGET]
```

### 2.2 Current Head Verification
- **Current Alembic Head**: `a1b2c3d4e5f6` (`backend/migrations/versions/a1b2c3d4e5f6_phase7_order_foundation.py`).
- **Database `alembic_version` state**: Previously at `112e2205a754`; upgrades linearly to `a1b2c3d4e5f6`, then to `b2c3d4e5f6a7`.
- **Target New Revision ID**: `b2c3d4e5f6a7`
- **Target Down Revision**: `a1b2c3d4e5f6`
- **Target Filename**: `backend/migrations/versions/b2c3d4e5f6a7_phase7_commercial_billing_payment.py`

---

## 3. Schema & Model Architectural Principles

### 3.1 Separation of Operational & Financial State Machines (R5)
- `OrderStatus` (`orders.status`): Exclusively operational (`DRAFT`, `PENDING`, `CONFIRMED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`). Zero payment states on the order.
- `PaymentStatus` (`payments.status`): Financial transaction lifecycle (`PENDING`, `SUCCEEDED`, `FAILED`, `OUTSTANDING`, `REFUNDED`, `PARTIALLY_REFUNDED`).
- `PickupStatus` (`order_pickups.status`): Physical garment collection lifecycle (`SCHEDULED`, `DETAILS_SUBMITTED`, `APPROVED`, `REJECTED`, `COMPLETED`).
- `InvoiceStatus` (`seller_billing_invoices.status`): Monthly seller statement status (`PENDING`, `PAID`, `OVERDUE`, `CANCELLED`).
- `SettlementStatus` (`seller_settlements.status`): Batch disbursement status (`SCHEDULED`, `PROCESSING`, `SETTLED`, `FAILED`, `PENDING`).
- `SellerRestrictionLevel` (`seller_commercial_configs.restriction_level`): Compliance standing (`NONE`, `WARNING`, `MARKETPLACE_RESTRICTED`, `WHITE_LABEL_RESTRICTED`, `FULL_SUSPENSION`).

### 3.2 Post-Pickup Payment Decoupling (R1)
- Order placement creates the order in `PENDING` with no initial payment charge.
- Garment pickup details must be reviewed and approved by the customer (`order_pickups.status == 'APPROVED'`), which acts as the authoritative trigger for creating and requesting a `Payment`.
- Payment failure modes:
  - Hard gate (`payment_required_before_pickup = True`): Payment failure blocks pickup completion and blocks order transition to `IN_PROGRESS`.
  - Permissive (`outstanding_receivable_allowed = True`): Pickup completes, order transitions to `IN_PROGRESS`, and payment enters `OUTSTANDING` status with a deadline (`due_date`).

### 3.3 Fee & Commission Ledger Isolation (R1, R2)
- Monolithic platforms often conflate third-party gateway deductions with marketplace commission. Phase 7 isolates:
  - `gateway_fee` + `gateway_tax`: Costs assessed by the processor (Stripe, Adyen, etc.).
  - `ttc_commission` + `ttc_commission_tax`: Revenue retained by TTC.
  - `retained_amount`: Dynamically computed as `amount - refunded_amount`, ensuring that partial refunds proportionally adjust platform commission deductions.

### 3.4 15-Day Cooling Hold & Monday Batch Payouts (R3)
- `TTC_GATEWAY`: Customer payments are held by TTC for a 15-calendar-day cooling window starting from `Payment.paid_at`. Every Monday, eligible transactions (`settled = FALSE` and `paid_at <= target_date - 15 days`) are aggregated into a `SellerSettlement` payout record.
- `SELLER_GATEWAY`: Direct merchant account processing. TTC imposes zero hold and creates zero `SellerSettlement` disbursements.

### 3.5 Reselection Linkage & Zero-Refund Invariant (R4)
- When a seller becomes `MARKETPLACE_RESTRICTED` or `FULL_SUSPENSION`, all `PENDING` orders for that seller are automatically cancelled with `cancellation_reason = 'SELLER_RESTRICTED'`.
- The customer can re-select an alternative seller via `POST /api/v1/orders/{order_id}/reselect`.
- The new order links to the old order via `orders.reselected_from_order_id = original_order.id`.
- **Zero-Refund Invariant**: Because `PENDING` orders have not yet approved pickup or requested payment, cancellation requires zero payment gateway refund.

---

## 4. PostgreSQL ENUM vs VARCHAR + Check Constraints

### 4.1 Comparative Evaluation

| Dimension | Native PostgreSQL ENUM (`CREATE TYPE ... AS ENUM`) | VARCHAR(50) + CHECK Constraints (`sa.CheckConstraint`) |
|---|---|---|
| **Codebase Consistency** | ❌ None used in Phases 1–7.1 | ✅ 100% consistent across all existing migrations (`orders`, `sellers`, `catalogs`, `pricing`) |
| **Pytest Conftest Safety** | ❌ Known `pg_type` collision bug on rapid `drop_all`/`create_all` cycles (`duplicate key value violates unique constraint "pg_type_typname_nsp_index"`) | ✅ Perfectly safe; dropped and recreated cleanly with tables without type catalog pollution |
| **Schema Evolution** | ❌ `ALTER TYPE ... ADD VALUE` cannot run in transactional migration blocks in older PostgreSQL and cannot drop values | ✅ Simple `DROP CONSTRAINT` / `ADD CONSTRAINT` within transactional DDL |
| **Data Integrity** | ✅ Strict DB-level enforcement | ✅ Strict DB-level enforcement (exact same semantic guarantee) |
| **SQLAlchemy Driver Overhead** | ❌ Requires custom type mappings or string coercion with psycopg | ✅ Direct string mapping; zero driver coercion friction |

### 4.2 Architectural Decision
**We adopt `sa.String(length=50)` with explicit database-level `sa.CheckConstraint` definitions.**  
This satisfies the requirement for bullet-proof database-level enum integrity while maintaining strict compatibility with the existing test infrastructure (`tests/conftest.py:reset_database`) and architectural conventions.

For completeness, Section 6 also provides the optional native ENUM DDL statements if native PostgreSQL types are explicitly chosen.

---

## 5. Detailed Database Entity Specifications

```
  ┌─────────────────────────┐
  │         orders          │◀──────────────────────────────┐
  │  reselected_from_order_id│───────────────────────────────┘ (self-referential FK, SET NULL)
  └────────────┬────────────┘
               │ 1:1
               ├───────────────────────────────────────────┐
               ▼ 1:1                                       ▼ 1:1
  ┌─────────────────────────┐                 ┌─────────────────────────┐
  │      order_pickups      │                 │        payments         │
  └─────────────────────────┘                 └────────────┬────────────┘
                                                           │ 1:N
                                                           ├──────────────────────────┐
                                                           ▼ 1:N                      ▼ N:1 (SET NULL)
  ┌──────────────────────────────┐            ┌─────────────────────────┐┌─────────────────────────┐
  │  seller_commercial_configs   │            │         refunds         ││   seller_settlements    │
  └──────────────────────────────┘            └─────────────────────────┘└─────────────────────────┘
               │                                                                       ▲
               │ 1:N                                                                   │ 1:N
               ▼                                                                       │
  ┌──────────────────────────────┐                                                     │
  │   seller_billing_invoices    │                                                     │
  │   (seller_id, invoice_month) │─────────────────────────────────────────────────────┘
  └──────────────────────────────┘
```

### 5.1 Column Alteration: `orders.reselected_from_order_id`
- **Target Table**: `orders`
- **Column Name**: `reselected_from_order_id`
- **Type**: `sa.Uuid()` (nullable)
- **Foreign Key**: `ForeignKeyConstraint(['reselected_from_order_id'], ['orders.id'], ondelete='SET NULL')`
- **Index**: `ix_orders_reselected_from_order_id` on `orders(reselected_from_order_id)`
- **Purpose**: Tracks provenance when an order is reselected following cancellation of a restricted seller's pending order. Prevents duplicate reselections and allows customer journey audit trails.

### 5.2 Table: `order_pickups`
- **Table Name**: `order_pickups`
- **Columns**:
  - `id`: `sa.Uuid()`, primary key, default `uuid.uuid4`.
  - `tenant_id`: `sa.Uuid()`, nullable=False, FK to `tenants.id` ondelete `RESTRICT`.
  - `seller_id`: `sa.Uuid()`, nullable=False, FK to `sellers.id` ondelete `RESTRICT`.
  - `order_id`: `sa.Uuid()`, nullable=False, unique=True, FK to `orders.id` ondelete `CASCADE`.
  - `status`: `sa.String(50)`, default `'SCHEDULED'`, nullable=False.
  - `actual_pickup_at`: `sa.DateTime(timezone=True)`, nullable=True.
  - `details_submitted_at`: `sa.DateTime(timezone=True)`, nullable=True.
  - `approved_at`: `sa.DateTime(timezone=True)`, nullable=True.
  - `rejection_reason`: `sa.String(1000)`, nullable=True.
  - `actual_details`: `sa.JSON()`, nullable=True (stores verified item counts, piece breakdown, operator notes).
  - `created_at`: `sa.DateTime(timezone=True)`, server_default=`now()`, nullable=False.
  - `updated_at`: `sa.DateTime(timezone=True)`, server_default=`now()`, nullable=False.
- **Constraints**:
  - `uq_order_pickups_order_id`: Unique on `['order_id']`.
  - `ck_order_pickups_status`: `status IN ('SCHEDULED', 'DETAILS_SUBMITTED', 'APPROVED', 'REJECTED', 'COMPLETED')`.
- **Indexes**:
  - `ix_order_pickups_order_id` (unique)
  - `ix_order_pickups_tenant_id`
  - `ix_order_pickups_seller_id`
  - `ix_order_pickups_status`
  - `ix_order_pickups_seller_status` composite on `['seller_id', 'status']`.

### 5.3 Table: `seller_commercial_configs`
- **Table Name**: `seller_commercial_configs`
- **Columns**:
  - `id`: `sa.Uuid()`, primary key.
  - `tenant_id`: `sa.Uuid()`, nullable=False, FK to `tenants.id` ondelete `CASCADE`.
  - `seller_id`: `sa.Uuid()`, nullable=False, unique=True, FK to `sellers.id` ondelete `CASCADE`.
  - `commercial_model`: `sa.String(50)`, default `'COMMISSION'`, nullable=False (`'COMMISSION'`, `'SUBSCRIPTION'`).
  - `commission_rate_percent`: `sa.Numeric(5, 2)`, default `10.00`, nullable=False.
  - `subscription_fee`: `sa.Numeric(12, 2)`, default `0.00`, nullable=False.
  - `marketplace_gateway`: `sa.String(50)`, default `'TTC_GATEWAY'`, nullable=False (`'TTC_GATEWAY'`, `'SELLER_GATEWAY'`).
  - `white_label_gateway`: `sa.String(50)`, default `'SELLER_GATEWAY'`, nullable=False (`'TTC_GATEWAY'`, `'SELLER_GATEWAY'`).
  - `payment_required_before_pickup`: `sa.Boolean()`, default `True`, nullable=False.
  - `outstanding_receivable_allowed`: `sa.Boolean()`, default `False`, nullable=False.
  - `payment_deadline_days`: `sa.Integer()`, default `1`, nullable=False.
  - `restriction_level`: `sa.String(50)`, default `'NONE'`, nullable=False (`'NONE'`, `'WARNING'`, `'MARKETPLACE_RESTRICTED'`, `'WHITE_LABEL_RESTRICTED'`, `'FULL_SUSPENSION'`).
  - `overdue_grace_days`: `sa.Integer()`, default `7`, nullable=False.
  - `daily_penalty_rate`: `sa.Numeric(6, 4)`, default `0.0010`, nullable=False (0.1% daily penalty).
  - `created_at`: `sa.DateTime(timezone=True)`, server_default=`now()`, nullable=False.
  - `updated_at`: `sa.DateTime(timezone=True)`, server_default=`now()`, nullable=False.
- **Constraints**:
  - `uq_seller_commercial_configs_seller_id`: Unique on `['seller_id']`.
  - `ck_seller_commercial_model`: `commercial_model IN ('COMMISSION', 'SUBSCRIPTION')`.
  - `ck_seller_marketplace_gateway`: `marketplace_gateway IN ('TTC_GATEWAY', 'SELLER_GATEWAY')`.
  - `ck_seller_whitelabel_gateway`: `white_label_gateway IN ('TTC_GATEWAY', 'SELLER_GATEWAY')`.
  - `ck_seller_restriction_level`: `restriction_level IN ('NONE', 'WARNING', 'MARKETPLACE_RESTRICTED', 'WHITE_LABEL_RESTRICTED', 'FULL_SUSPENSION')`.
  - `ck_seller_commission_rate`: `commission_rate_percent >= 0 AND commission_rate_percent <= 100`.
  - `ck_seller_subscription_fee`: `subscription_fee >= 0`.
  - `ck_seller_penalty_rate`: `daily_penalty_rate >= 0`.
  - `ck_seller_grace_days`: `overdue_grace_days >= 0`.
  - `ck_seller_deadline_days`: `payment_deadline_days >= 0`.
- **Indexes**:
  - `ix_seller_commercial_configs_seller_id` (unique)
  - `ix_seller_commercial_configs_tenant_id`
  - `ix_seller_commercial_configs_restriction_level`

### 5.4 Table: `seller_billing_invoices`
- **Table Name**: `seller_billing_invoices`
- **Columns**:
  - `id`: `sa.Uuid()`, primary key.
  - `tenant_id`: `sa.Uuid()`, nullable=False, FK to `tenants.id` ondelete `CASCADE`.
  - `seller_id`: `sa.Uuid()`, nullable=False, FK to `sellers.id` ondelete `CASCADE`.
  - `invoice_month`: `sa.String(7)`, nullable=False (format: `"YYYY-MM"`, e.g. `"2026-09"`).
  - `due_date`: `sa.Date()`, nullable=False.
  - `status`: `sa.String(50)`, default `'PENDING'`, nullable=False (`'PENDING'`, `'PAID'`, `'OVERDUE'`, `'CANCELLED'`).
  - `currency`: `sa.String(3)`, default `'USD'`, nullable=False.
  - `subtotal`: `sa.Numeric(12, 2)`, default `0.00`, nullable=False.
  - `tax_total`: `sa.Numeric(12, 2)`, default `0.00`, nullable=False.
  - `penalty_total`: `sa.Numeric(12, 2)`, default `0.00`, nullable=False.
  - `total_amount`: `sa.Numeric(12, 2)`, default `0.00`, nullable=False.
  - `paid_at`: `sa.DateTime(timezone=True)`, nullable=True.
  - `created_at`: `sa.DateTime(timezone=True)`, server_default=`now()`, nullable=False.
  - `updated_at`: `sa.DateTime(timezone=True)`, server_default=`now()`, nullable=False.
- **Constraints**:
  - `uq_seller_billing_invoices_seller_month`: Unique on `['seller_id', 'invoice_month']`.
  - `ck_billing_invoices_status`: `status IN ('PENDING', 'PAID', 'OVERDUE', 'CANCELLED')`.
  - `ck_billing_invoices_subtotal_nonneg`: `subtotal >= 0`.
  - `ck_billing_invoices_tax_nonneg`: `tax_total >= 0`.
  - `ck_billing_invoices_penalty_nonneg`: `penalty_total >= 0`.
  - `ck_billing_invoices_total_nonneg`: `total_amount >= 0`.
- **Indexes**:
  - `ix_seller_billing_invoices_seller_id`
  - `ix_seller_billing_invoices_tenant_id`
  - `ix_seller_billing_invoices_status`
  - `ix_seller_billing_invoices_due_date`
  - `ix_seller_billing_invoices_seller_status` composite on `['seller_id', 'status']`.

### 5.5 Table: `seller_settlements`
- **Table Name**: `seller_settlements`
- **Columns**:
  - `id`: `sa.Uuid()`, primary key.
  - `tenant_id`: `sa.Uuid()`, nullable=False, FK to `tenants.id` ondelete `CASCADE`.
  - `seller_id`: `sa.Uuid()`, nullable=False, FK to `sellers.id` ondelete `CASCADE`.
  - `gateway_type`: `sa.String(50)`, default `'TTC_GATEWAY'`, nullable=False (`'TTC_GATEWAY'`, `'SELLER_GATEWAY'`).
  - `status`: `sa.String(50)`, default `'SCHEDULED'`, nullable=False (`'SCHEDULED'`, `'PROCESSING'`, `'SETTLED'`, `'FAILED'`, `'PENDING'`).
  - `currency`: `sa.String(3)`, default `'USD'`, nullable=False.
  - `amount`: `sa.Numeric(12, 2)`, nullable=False.
  - `scheduled_for`: `sa.Date()`, nullable=False (the Monday disbursement date).
  - `processed_at`: `sa.DateTime(timezone=True)`, nullable=True.
  - `reference_id`: `sa.String(255)`, nullable=True (bank transfer / stripe payout transaction reference).
  - `created_at`: `sa.DateTime(timezone=True)`, server_default=`now()`, nullable=False.
  - `updated_at`: `sa.DateTime(timezone=True)`, server_default=`now()`, nullable=False.
- **Constraints**:
  - `uq_seller_settlements_reference_id`: Unique on `['reference_id']` (partial index or unique constraint allowing multiple nulls).
  - `ck_settlements_gateway_type`: `gateway_type IN ('TTC_GATEWAY', 'SELLER_GATEWAY')`.
  - `ck_settlements_status`: `status IN ('SCHEDULED', 'PROCESSING', 'SETTLED', 'FAILED', 'PENDING')`.
  - `ck_settlements_amount_nonneg`: `amount >= 0`.
- **Indexes**:
  - `ix_seller_settlements_seller_id`
  - `ix_seller_settlements_tenant_id`
  - `ix_seller_settlements_status`
  - `ix_seller_settlements_scheduled_for`
  - `ix_seller_settlements_seller_scheduled` composite on `['seller_id', 'scheduled_for']`.
  - `ix_seller_settlements_status_scheduled` composite on `['status', 'scheduled_for']`.

### 5.6 Table: `payments`
- **Table Name**: `payments`
- **Columns**:
  - `id`: `sa.Uuid()`, primary key.
  - `order_id`: `sa.Uuid()`, nullable=False, unique=True, FK to `orders.id` ondelete `CASCADE`.
  - `tenant_id`: `sa.Uuid()`, nullable=False, FK to `tenants.id` ondelete `CASCADE`.
  - `seller_id`: `sa.Uuid()`, nullable=False, FK to `sellers.id` ondelete `CASCADE`.
  - `customer_id`: `sa.Uuid()`, nullable=False, FK to `customers.id` ondelete `CASCADE`.
  - `gateway_type`: `sa.String(50)`, nullable=False (`'TTC_GATEWAY'`, `'SELLER_GATEWAY'`).
  - `status`: `sa.String(50)`, default `'PENDING'`, nullable=False (`'PENDING'`, `'SUCCEEDED'`, `'FAILED'`, `'OUTSTANDING'`, `'REFUNDED'`, `'PARTIALLY_REFUNDED'`).
  - `currency`: `sa.String(3)`, nullable=False.
  - `amount`: `sa.Numeric(12, 2)`, nullable=False.
  - `gateway_fee`: `sa.Numeric(12, 2)`, default `0.00`, nullable=False.
  - `gateway_tax`: `sa.Numeric(12, 2)`, default `0.00`, nullable=False.
  - `ttc_commission`: `sa.Numeric(12, 2)`, default `0.00`, nullable=False.
  - `ttc_commission_tax`: `sa.Numeric(12, 2)`, default `0.00`, nullable=False.
  - `refunded_amount`: `sa.Numeric(12, 2)`, default `0.00`, nullable=False.
  - `retained_amount`: `sa.Numeric(12, 2)`, default `0.00`, nullable=False.
  - `settled`: `sa.Boolean()`, default `False`, nullable=False.
  - `settlement_id`: `sa.Uuid()`, nullable=True, FK to `seller_settlements.id` ondelete `SET NULL`.
  - `paid_at`: `sa.DateTime(timezone=True)`, nullable=True (starts 15-day hold countdown).
  - `due_date`: `sa.DateTime(timezone=True)`, nullable=True (for outstanding receivable deadline).
  - `gateway_transaction_id`: `sa.String(255)`, nullable=True.
  - `created_at`: `sa.DateTime(timezone=True)`, server_default=`now()`, nullable=False.
  - `updated_at`: `sa.DateTime(timezone=True)`, server_default=`now()`, nullable=False.
- **Constraints**:
  - `uq_payments_order_id`: Unique on `['order_id']`.
  - `ck_payments_gateway_type`: `gateway_type IN ('TTC_GATEWAY', 'SELLER_GATEWAY')`.
  - `ck_payments_status`: `status IN ('PENDING', 'SUCCEEDED', 'FAILED', 'OUTSTANDING', 'REFUNDED', 'PARTIALLY_REFUNDED')`.
  - `ck_payments_amount_nonneg`: `amount >= 0`.
  - `ck_payments_gateway_fee_nonneg`: `gateway_fee >= 0`.
  - `ck_payments_gateway_tax_nonneg`: `gateway_tax >= 0`.
  - `ck_payments_ttc_commission_nonneg`: `ttc_commission >= 0`.
  - `ck_payments_ttc_commission_tax_nonneg`: `ttc_commission_tax >= 0`.
  - `ck_payments_refunded_range`: `refunded_amount >= 0 AND refunded_amount <= amount`.
  - `ck_payments_retained_range`: `retained_amount >= 0 AND retained_amount <= amount`.
- **Indexes**:
  - `ix_payments_order_id` (unique)
  - `ix_payments_tenant_id`
  - `ix_payments_seller_id`
  - `ix_payments_customer_id`
  - `ix_payments_status`
  - `ix_payments_settlement_id`
  - `ix_payments_settled_paid_at` composite on `['settled', 'paid_at']` (critical for 15-day cooling hold batch queries).
  - `ix_payments_seller_settled` composite on `['seller_id', 'settled']`.
  - `ix_payments_due_date` on `['due_date']`.

### 5.7 Table: `refunds`
- **Table Name**: `refunds`
- **Columns**:
  - `id`: `sa.Uuid()`, primary key.
  - `tenant_id`: `sa.Uuid()`, nullable=False, FK to `tenants.id` ondelete `CASCADE`.
  - `payment_id`: `sa.Uuid()`, nullable=False, FK to `payments.id` ondelete `CASCADE`.
  - `amount`: `sa.Numeric(12, 2)`, nullable=False.
  - `reason`: `sa.String(500)`, nullable=True.
  - `commission_deduction`: `sa.Numeric(12, 2)`, default `0.00`, nullable=False.
  - `gateway_fee_reversed`: `sa.Numeric(12, 2)`, default `0.00`, nullable=False.
  - `gateway_tax_reversed`: `sa.Numeric(12, 2)`, default `0.00`, nullable=False.
  - `gateway_refund_id`: `sa.String(255)`, nullable=True.
  - `created_at`: `sa.DateTime(timezone=True)`, server_default=`now()`, nullable=False.
- **Constraints**:
  - `ck_refunds_amount_positive`: `amount > 0`.
  - `ck_refunds_commission_deduction_nonneg`: `commission_deduction >= 0`.
  - `ck_refunds_gateway_fee_reversed_nonneg`: `gateway_fee_reversed >= 0`.
  - `ck_refunds_gateway_tax_reversed_nonneg`: `gateway_tax_reversed >= 0`.
- **Indexes**:
  - `ix_refunds_payment_id`
  - `ix_refunds_tenant_id`
  - `ix_refunds_created_at`

---

## 6. Complete Drop-In Alembic Migration Script

Below is the complete implementation for `backend/migrations/versions/b2c3d4e5f6a7_phase7_commercial_billing_payment.py`.

```python
"""phase7_commercial_billing_payment

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-19 18:00:00.000000

Phase 7 — Commercial Billing, Payment Timing, Settlement & Seller Restrictions Foundation.

Creates:
  - orders.reselected_from_order_id (column alteration with FK to orders.id ondelete SET NULL)
  - order_pickups
  - seller_commercial_configs
  - seller_billing_invoices
  - seller_settlements
  - payments
  - refunds
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # 1. Alter orders: add reselected_from_order_id
    # -----------------------------------------------------------------------
    op.add_column(
        'orders',
        sa.Column('reselected_from_order_id', sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        'fk_orders_reselected_from_order_id_orders',
        'orders',
        'orders',
        ['reselected_from_order_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.create_index(
        'ix_orders_reselected_from_order_id',
        'orders',
        ['reselected_from_order_id'],
        unique=False,
    )

    # -----------------------------------------------------------------------
    # 2. Table: order_pickups
    # -----------------------------------------------------------------------
    op.create_table(
        'order_pickups',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('seller_id', sa.Uuid(), nullable=False),
        sa.Column('order_id', sa.Uuid(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='SCHEDULED', nullable=False),
        sa.Column('actual_pickup_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('details_submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.String(length=1000), nullable=True),
        sa.Column('actual_details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint(
            "status IN ('SCHEDULED', 'DETAILS_SUBMITTED', 'APPROVED', 'REJECTED', 'COMPLETED')",
            name='ck_order_pickups_status',
        ),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['seller_id'], ['sellers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id', name='uq_order_pickups_order_id'),
    )
    op.create_index('ix_order_pickups_order_id', 'order_pickups', ['order_id'], unique=True)
    op.create_index('ix_order_pickups_tenant_id', 'order_pickups', ['tenant_id'], unique=False)
    op.create_index('ix_order_pickups_seller_id', 'order_pickups', ['seller_id'], unique=False)
    op.create_index('ix_order_pickups_status', 'order_pickups', ['status'], unique=False)
    op.create_index('ix_order_pickups_seller_status', 'order_pickups', ['seller_id', 'status'], unique=False)

    # -----------------------------------------------------------------------
    # 3. Table: seller_commercial_configs
    # -----------------------------------------------------------------------
    op.create_table(
        'seller_commercial_configs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('seller_id', sa.Uuid(), nullable=False),
        sa.Column('commercial_model', sa.String(length=50), server_default='COMMISSION', nullable=False),
        sa.Column('commission_rate_percent', sa.Numeric(precision=5, scale=2), server_default='10.00', nullable=False),
        sa.Column('subscription_fee', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('marketplace_gateway', sa.String(length=50), server_default='TTC_GATEWAY', nullable=False),
        sa.Column('white_label_gateway', sa.String(length=50), server_default='SELLER_GATEWAY', nullable=False),
        sa.Column('payment_required_before_pickup', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('outstanding_receivable_allowed', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('payment_deadline_days', sa.Integer(), server_default='1', nullable=False),
        sa.Column('restriction_level', sa.String(length=50), server_default='NONE', nullable=False),
        sa.Column('overdue_grace_days', sa.Integer(), server_default='7', nullable=False),
        sa.Column('daily_penalty_rate', sa.Numeric(precision=6, scale=4), server_default='0.0010', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("commercial_model IN ('COMMISSION', 'SUBSCRIPTION')", name='ck_seller_commercial_model'),
        sa.CheckConstraint("marketplace_gateway IN ('TTC_GATEWAY', 'SELLER_GATEWAY')", name='ck_seller_marketplace_gateway'),
        sa.CheckConstraint("white_label_gateway IN ('TTC_GATEWAY', 'SELLER_GATEWAY')", name='ck_seller_whitelabel_gateway'),
        sa.CheckConstraint(
            "restriction_level IN ('NONE', 'WARNING', 'MARKETPLACE_RESTRICTED', 'WHITE_LABEL_RESTRICTED', 'FULL_SUSPENSION')",
            name='ck_seller_restriction_level',
        ),
        sa.CheckConstraint("commission_rate_percent >= 0 AND commission_rate_percent <= 100", name='ck_seller_commission_rate'),
        sa.CheckConstraint("subscription_fee >= 0", name='ck_seller_subscription_fee'),
        sa.CheckConstraint("daily_penalty_rate >= 0", name='ck_seller_penalty_rate'),
        sa.CheckConstraint("overdue_grace_days >= 0", name='ck_seller_grace_days'),
        sa.CheckConstraint("payment_deadline_days >= 0", name='ck_seller_deadline_days'),
        sa.ForeignKeyConstraint(['seller_id'], ['sellers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('seller_id', name='uq_seller_commercial_configs_seller_id'),
    )
    op.create_index('ix_seller_commercial_configs_seller_id', 'seller_commercial_configs', ['seller_id'], unique=True)
    op.create_index('ix_seller_commercial_configs_tenant_id', 'seller_commercial_configs', ['tenant_id'], unique=False)
    op.create_index('ix_seller_commercial_configs_restriction_level', 'seller_commercial_configs', ['restriction_level'], unique=False)

    # -----------------------------------------------------------------------
    # 4. Table: seller_billing_invoices
    # -----------------------------------------------------------------------
    op.create_table(
        'seller_billing_invoices',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('seller_id', sa.Uuid(), nullable=False),
        sa.Column('invoice_month', sa.String(length=7), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='PENDING', nullable=False),
        sa.Column('currency', sa.String(length=3), server_default='USD', nullable=False),
        sa.Column('subtotal', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('tax_total', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('penalty_total', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("status IN ('PENDING', 'PAID', 'OVERDUE', 'CANCELLED')", name='ck_billing_invoices_status'),
        sa.CheckConstraint("subtotal >= 0", name='ck_billing_invoices_subtotal_nonneg'),
        sa.CheckConstraint("tax_total >= 0", name='ck_billing_invoices_tax_nonneg'),
        sa.CheckConstraint("penalty_total >= 0", name='ck_billing_invoices_penalty_nonneg'),
        sa.CheckConstraint("total_amount >= 0", name='ck_billing_invoices_total_nonneg'),
        sa.ForeignKeyConstraint(['seller_id'], ['sellers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('seller_id', 'invoice_month', name='uq_seller_billing_invoices_seller_month'),
    )
    op.create_index('ix_seller_billing_invoices_seller_id', 'seller_billing_invoices', ['seller_id'], unique=False)
    op.create_index('ix_seller_billing_invoices_tenant_id', 'seller_billing_invoices', ['tenant_id'], unique=False)
    op.create_index('ix_seller_billing_invoices_status', 'seller_billing_invoices', ['status'], unique=False)
    op.create_index('ix_seller_billing_invoices_due_date', 'seller_billing_invoices', ['due_date'], unique=False)
    op.create_index('ix_seller_billing_invoices_seller_status', 'seller_billing_invoices', ['seller_id', 'status'], unique=False)

    # -----------------------------------------------------------------------
    # 5. Table: seller_settlements
    # -----------------------------------------------------------------------
    op.create_table(
        'seller_settlements',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('seller_id', sa.Uuid(), nullable=False),
        sa.Column('gateway_type', sa.String(length=50), server_default='TTC_GATEWAY', nullable=False),
        sa.Column('status', sa.String(length=50), server_default='SCHEDULED', nullable=False),
        sa.Column('currency', sa.String(length=3), server_default='USD', nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('scheduled_for', sa.Date(), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reference_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("gateway_type IN ('TTC_GATEWAY', 'SELLER_GATEWAY')", name='ck_settlements_gateway_type'),
        sa.CheckConstraint("status IN ('SCHEDULED', 'PROCESSING', 'SETTLED', 'FAILED', 'PENDING')", name='ck_settlements_status'),
        sa.CheckConstraint("amount >= 0", name='ck_settlements_amount_nonneg'),
        sa.ForeignKeyConstraint(['seller_id'], ['sellers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('reference_id', name='uq_seller_settlements_reference_id'),
    )
    op.create_index('ix_seller_settlements_seller_id', 'seller_settlements', ['seller_id'], unique=False)
    op.create_index('ix_seller_settlements_tenant_id', 'seller_settlements', ['tenant_id'], unique=False)
    op.create_index('ix_seller_settlements_status', 'seller_settlements', ['status'], unique=False)
    op.create_index('ix_seller_settlements_scheduled_for', 'seller_settlements', ['scheduled_for'], unique=False)
    op.create_index('ix_seller_settlements_seller_scheduled', 'seller_settlements', ['seller_id', 'scheduled_for'], unique=False)
    op.create_index('ix_seller_settlements_status_scheduled', 'seller_settlements', ['status', 'scheduled_for'], unique=False)

    # -----------------------------------------------------------------------
    # 6. Table: payments
    # -----------------------------------------------------------------------
    op.create_table(
        'payments',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('order_id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('seller_id', sa.Uuid(), nullable=False),
        sa.Column('customer_id', sa.Uuid(), nullable=False),
        sa.Column('gateway_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), server_default='PENDING', nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('gateway_fee', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('gateway_tax', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('ttc_commission', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('ttc_commission_tax', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('refunded_amount', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('retained_amount', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('settled', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('settlement_id', sa.Uuid(), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('gateway_transaction_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("gateway_type IN ('TTC_GATEWAY', 'SELLER_GATEWAY')", name='ck_payments_gateway_type'),
        sa.CheckConstraint(
            "status IN ('PENDING', 'SUCCEEDED', 'FAILED', 'OUTSTANDING', 'REFUNDED', 'PARTIALLY_REFUNDED')",
            name='ck_payments_status',
        ),
        sa.CheckConstraint("amount >= 0", name='ck_payments_amount_nonneg'),
        sa.CheckConstraint("gateway_fee >= 0", name='ck_payments_gateway_fee_nonneg'),
        sa.CheckConstraint("gateway_tax >= 0", name='ck_payments_gateway_tax_nonneg'),
        sa.CheckConstraint("ttc_commission >= 0", name='ck_payments_ttc_commission_nonneg'),
        sa.CheckConstraint("ttc_commission_tax >= 0", name='ck_payments_ttc_commission_tax_nonneg'),
        sa.CheckConstraint("refunded_amount >= 0 AND refunded_amount <= amount", name='ck_payments_refunded_range'),
        sa.CheckConstraint("retained_amount >= 0 AND retained_amount <= amount", name='ck_payments_retained_range'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['seller_id'], ['sellers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['settlement_id'], ['seller_settlements.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('order_id', name='uq_payments_order_id'),
    )
    op.create_index('ix_payments_order_id', 'payments', ['order_id'], unique=True)
    op.create_index('ix_payments_tenant_id', 'payments', ['tenant_id'], unique=False)
    op.create_index('ix_payments_seller_id', 'payments', ['seller_id'], unique=False)
    op.create_index('ix_payments_customer_id', 'payments', ['customer_id'], unique=False)
    op.create_index('ix_payments_status', 'payments', ['status'], unique=False)
    op.create_index('ix_payments_settlement_id', 'payments', ['settlement_id'], unique=False)
    op.create_index('ix_payments_settled_paid_at', 'payments', ['settled', 'paid_at'], unique=False)
    op.create_index('ix_payments_seller_settled', 'payments', ['seller_id', 'settled'], unique=False)
    op.create_index('ix_payments_due_date', 'payments', ['due_date'], unique=False)

    # -----------------------------------------------------------------------
    # 7. Table: refunds
    # -----------------------------------------------------------------------
    op.create_table(
        'refunds',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('tenant_id', sa.Uuid(), nullable=False),
        sa.Column('payment_id', sa.Uuid(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('reason', sa.String(length=500), nullable=True),
        sa.Column('commission_deduction', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('gateway_fee_reversed', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('gateway_tax_reversed', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('gateway_refund_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('amount > 0', name='ck_refunds_amount_positive'),
        sa.CheckConstraint('commission_deduction >= 0', name='ck_refunds_commission_deduction_nonneg'),
        sa.CheckConstraint('gateway_fee_reversed >= 0', name='ck_refunds_gateway_fee_reversed_nonneg'),
        sa.CheckConstraint('gateway_tax_reversed >= 0', name='ck_refunds_gateway_tax_reversed_nonneg'),
        sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_refunds_payment_id', 'refunds', ['payment_id'], unique=False)
    op.create_index('ix_refunds_tenant_id', 'refunds', ['tenant_id'], unique=False)
    op.create_index('ix_refunds_created_at', 'refunds', ['created_at'], unique=False)


def downgrade() -> None:
    # 7. Drop refunds
    op.drop_index('ix_refunds_created_at', table_name='refunds')
    op.drop_index('ix_refunds_tenant_id', table_name='refunds')
    op.drop_index('ix_refunds_payment_id', table_name='refunds')
    op.drop_table('refunds')

    # 6. Drop payments
    op.drop_index('ix_payments_due_date', table_name='payments')
    op.drop_index('ix_payments_seller_settled', table_name='payments')
    op.drop_index('ix_payments_settled_paid_at', table_name='payments')
    op.drop_index('ix_payments_settlement_id', table_name='payments')
    op.drop_index('ix_payments_status', table_name='payments')
    op.drop_index('ix_payments_customer_id', table_name='payments')
    op.drop_index('ix_payments_seller_id', table_name='payments')
    op.drop_index('ix_payments_tenant_id', table_name='payments')
    op.drop_index('ix_payments_order_id', table_name='payments')
    op.drop_table('payments')

    # 5. Drop seller_settlements
    op.drop_index('ix_seller_settlements_status_scheduled', table_name='seller_settlements')
    op.drop_index('ix_seller_settlements_seller_scheduled', table_name='seller_settlements')
    op.drop_index('ix_seller_settlements_scheduled_for', table_name='seller_settlements')
    op.drop_index('ix_seller_settlements_status', table_name='seller_settlements')
    op.drop_index('ix_seller_settlements_tenant_id', table_name='seller_settlements')
    op.drop_index('ix_seller_settlements_seller_id', table_name='seller_settlements')
    op.drop_table('seller_settlements')

    # 4. Drop seller_billing_invoices
    op.drop_index('ix_seller_billing_invoices_seller_status', table_name='seller_billing_invoices')
    op.drop_index('ix_seller_billing_invoices_due_date', table_name='seller_billing_invoices')
    op.drop_index('ix_seller_billing_invoices_status', table_name='seller_billing_invoices')
    op.drop_index('ix_seller_billing_invoices_tenant_id', table_name='seller_billing_invoices')
    op.drop_index('ix_seller_billing_invoices_seller_id', table_name='seller_billing_invoices')
    op.drop_table('seller_billing_invoices')

    # 3. Drop seller_commercial_configs
    op.drop_index('ix_seller_commercial_configs_restriction_level', table_name='seller_commercial_configs')
    op.drop_index('ix_seller_commercial_configs_tenant_id', table_name='seller_commercial_configs')
    op.drop_index('ix_seller_commercial_configs_seller_id', table_name='seller_commercial_configs')
    op.drop_table('seller_commercial_configs')

    # 2. Drop order_pickups
    op.drop_index('ix_order_pickups_seller_status', table_name='order_pickups')
    op.drop_index('ix_order_pickups_status', table_name='order_pickups')
    op.drop_index('ix_order_pickups_seller_id', table_name='order_pickups')
    op.drop_index('ix_order_pickups_tenant_id', table_name='order_pickups')
    op.drop_index('ix_order_pickups_order_id', table_name='order_pickups')
    op.drop_table('order_pickups')

    # 1. Revert orders alteration
    op.drop_index('ix_orders_reselected_from_order_id', table_name='orders')
    op.drop_constraint('fk_orders_reselected_from_order_id_orders', 'orders', type_='foreignkey')
    op.drop_column('orders', 'reselected_from_order_id')
```

---

## 7. Required SQLAlchemy Domain Model Adjustments

To ensure exact 1:1 synchronization between Alembic migrations and the declarative metadata in `backend/app/models/`, the following model additions and adjustments must be implemented by the M1 implementation agent:

### 7.1 New Model: `backend/app/models/pickup.py`
Create `pickup.py` defining:
```python
from enum import Enum
import uuid
from datetime import datetime
from typing import Any
from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

class PickupStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    DETAILS_SUBMITTED = "DETAILS_SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    COMPLETED = "COMPLETED"

class OrderPickup(Base):
    __tablename__ = "order_pickups"
    __table_args__ = (
        UniqueConstraint("order_id", name="uq_order_pickups_order_id"),
        Index("ix_order_pickups_seller_status", "seller_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False, index=True)
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sellers.id", ondelete="RESTRICT"), nullable=False, index=True)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)

    status: Mapped[str] = mapped_column(String(50), default=PickupStatus.SCHEDULED.value, nullable=False, index=True)

    actual_pickup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    details_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    actual_details: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
```

### 7.2 Model Update: `backend/app/models/commercial.py`
Add `tenant_id`, `overdue_grace_days`, and `daily_penalty_rate`:
```python
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    overdue_grace_days: Mapped[int] = mapped_column(default=7, nullable=False)
    daily_penalty_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("0.0010"), nullable=False)
```

### 7.3 Model Update: `backend/app/models/payment.py`
Add missing fields on `Payment` and `Refund`:
```python
    # In Payment:
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False, index=True)
    settled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    settlement_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("seller_settlements.id", ondelete="SET NULL"), nullable=True, index=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # In Refund:
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    commission_deduction: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
```

### 7.4 Model Update: `backend/app/models/billing.py`
1. In `SettlementStatus`: add `SCHEDULED = "SCHEDULED"`.
2. In `SellerBillingInvoice`:
   Change `invoice_month` to `String(7)`:
   ```python
   invoice_month: Mapped[str] = mapped_column(String(7), nullable=False)  # format: "YYYY-MM"
   ```
   Add table args:
   ```python
   __table_args__ = (
       UniqueConstraint("seller_id", "invoice_month", name="uq_seller_billing_invoices_seller_month"),
       Index("ix_seller_billing_invoices_seller_status", "seller_id", "status"),
   )
   ```

### 7.5 Model Registration: `backend/app/models/__init__.py`
Export `OrderPickup` and `PickupStatus` in `__init__.py` and include in `__all__`:
```python
from app.models.pickup import OrderPickup, PickupStatus

__all__ = [
    ...,
    'OrderPickup',
    'PickupStatus',
]
```

---

## 8. Migration Reversibility & Rollback Safety

1. **Transactional Execution**: All DDL statements in PostgreSQL are fully transactional. If any step fails during upgrade or downgrade, the entire transaction rolls back cleanly without leaving orphan tables or partial schemas.
2. **Nullable Column Addition**: Adding `orders.reselected_from_order_id` as a nullable column (`nullable=True`) allows instant, lock-free schema alteration on existing production tables without rewriting existing rows.
3. **Foreign Key Integrity**:
   - `orders.reselected_from_order_id` uses `ondelete='SET NULL'`. If a parent order is deleted, the reselected order retains its row with a null parent pointer rather than being destroyed.
   - `order_pickups.order_id` uses `ondelete='CASCADE'`.
   - `payments.settlement_id` uses `ondelete='SET NULL'`, ensuring that payment transaction records survive even if an unfinalized settlement draft is purged.
4. **Clean Symmetrical Downgrade**: The `downgrade()` function strictly drops objects in the exact reverse order of creation: children before parents, foreign keys before referenced tables, indexes before tables.

---

## 9. Verification & Execution Playbook

### Step 1: Migration Generation
Save the complete migration script to:
`/workspaces/TheTextileCare/backend/migrations/versions/b2c3d4e5f6a7_phase7_commercial_billing_payment.py`

### Step 2: Alembic Upgrade Verification
Run the migration upgrade command:
```bash
cd /workspaces/TheTextileCare/backend
PYTHONPATH=. /workspaces/TheTextileCare/.venv/bin/alembic upgrade head
```
Verify terminal output confirms:
`Running upgrade a1b2c3d4e5f6 -> b2c3d4e5f6a7, phase7_commercial_billing_payment`

### Step 3: Alembic Downgrade Verification
Verify full rollback safety:
```bash
PYTHONPATH=. /workspaces/TheTextileCare/.venv/bin/alembic downgrade a1b2c3d4e5f6
```
Verify terminal output confirms:
`Running downgrade b2c3d4e5f6a7 -> a1b2c3d4e5f6, phase7_commercial_billing_payment`

### Step 4: Re-Upgrade to Head
```bash
PYTHONPATH=. /workspaces/TheTextileCare/.venv/bin/alembic upgrade head
```

### Step 5: Pytest Conftest & Regression Test Run
Run the full test suite to verify table creation and test isolation:
```bash
PYTHONPATH=. /workspaces/TheTextileCare/.venv/bin/pytest tests/api/test_health.py tests/api/test_orders.py tests/api/test_cancellation.py tests/api/test_rejection.py
```
Expected result: **All 35 tests pass.**
