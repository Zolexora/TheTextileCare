# Milestone 1 Explorer 2 Handoff Report: Domain Models & Schemas

**Author:** `explorer_m1_2`  
**Milestone:** Milestone 1 — Database Migration, Domain Models & RBAC Foundation  
**Date:** 2026-09-19  
**Recipient:** Project Orchestrator / Worker M1.1 (`parent`)  

---

## 1. Observation

Direct code and environment observations:
1. **Existing Models State**:
   - `backend/app/models/commercial.py`: Lines 25–46 define `SellerCommercialConfiguration`. It maps `seller_id`, `marketplace_gateway`, `white_label_gateway`, `commercial_model`, `commission_rate_percent`, `subscription_fee`, `payment_required_before_pickup`, `outstanding_receivable_allowed`, `payment_deadline_days`, and `restriction_level`. However, `tenant_id` foreign key is **missing** (violating multi-tenant isolation R5). Furthermore, configurable late penalty and overdue threshold parameters (`overdue_warning_days`, `overdue_restriction_days`, `overdue_suspension_days`, `overdue_grace_days`, `daily_penalty_rate`, `billing_cycle_day`, `invoice_due_days`) were not present.
   - `backend/app/models/payment.py`: Lines 18–51 define `Payment`. It includes `order_id`, `tenant_id`, `customer_id`, fee and tax columns, `refunded_amount`, `retained_amount`. However, it lacks `seller_id` (crucial for seller queries without joining orders), `settled: bool` (required by `PROJECT.md` line 95), `settlement_id: UUID | None` (FK to `seller_settlements.id`), `paid_at: datetime | None` (mandatory for the 15-day settlement cooling hold filter), and `due_date: datetime | None` (mandatory for `OUTSTANDING` receivable deadlines). Lines 52–68 define `Refund`, which lacks `tenant_id` and `commission_deduction` (specified in `PROJECT.md` line 97).
   - `backend/app/models/billing.py`: Lines 16–40 define `SellerBillingInvoice`, but lack the database constraint `UniqueConstraint("seller_id", "invoice_month")` required by `PROJECT.md` line 23. Lines 41–46 define `SettlementStatus(str, Enum)` with states `PENDING`, `PROCESSING`, `SETTLED`, `FAILED`, whereas `PROJECT.md` line 9 and 101 strictly mandate `SCHEDULED`, `PROCESSING`, `SETTLED`, `FAILED`.
   - `backend/app/models/order.py`: Lines 154–156 define `reselected_from_order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)`. However, the self-referential relationship `reselected_from_order`, and explicit one-to-one relationships to `OrderPickup` (`order.pickup`) and `Payment` (`order.payment`) are absent from lines 171–185.
   - `backend/app/models/pickup.py`: Does not exist in the working directory or repository.
   - `backend/app/models/__init__.py`: Lines 33–35 import commercial, payment, and billing models, but do not import `OrderPickup` or `PickupStatus` from `app.models.pickup`. Consequently, `Base.metadata.create_all()` in `tests/conftest.py` line 21 does not create the `order_pickups` table.
2. **Existing Schemas State**:
   - `backend/app/schemas/` contains `order.py`, `pricing.py`, `seller.py`, `customer.py`, etc., but contains **no schema files** for `commercial.py`, `pickup.py`, `payment.py`, `billing.py`, or `settlement.py`.
   - Schema conventions across `backend/app/schemas/` adhere strictly to Pydantic v2: `model_config = ConfigDict(from_attributes=True)`, `Field(...)`, `Decimal` for all currency amounts, and `@model_validator(mode="after")`.
3. **Alembic Migrations State**:
   - `backend/migrations/versions/a1b2c3d4e5f6_phase7_order_foundation.py` is the current migration head (`revision = 'a1b2c3d4e5f6'`). It does not contain `order_pickups`, `seller_commercial_configs`, `payments`, `refunds`, `seller_billing_invoices`, `seller_settlements`, or `orders.reselected_from_order_id`. All of these must be created in the Phase 7 Alembic migration with `down_revision = 'a1b2c3d4e5f6'`.

---

## 2. Logic Chain

1. **Multi-Tenancy & Integrity (Step 1 -> Conclusion 1)**:
   - Observation: Multi-tenant isolation is the architectural foundation of TTC (`TenantContext.tenant_id`).
   - Deduction: `SellerCommercialConfiguration` and `Refund` must possess `tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)` so queries and cascading deletes are scoped without multi-hop joins.
2. **Post-Pickup Payment Timing (Step 2 -> Conclusion 2)**:
   - Observation: Physical laundry counts and weights vary between customer placement and driver collection. Charging at order creation would produce constant auth voids and transaction fee overhead.
   - Deduction: Physical pickup must be encapsulated in an independent entity `OrderPickup` with status transitions (`SCHEDULED` -> `DETAILS_SUBMITTED` -> `APPROVED` / `REJECTED` -> `COMPLETED`). Customer approval (`APPROVED`) is the sole trigger for initiating `Payment`.
3. **Dual Payment Failure Modes (Step 3 -> Conclusion 3)**:
   - Observation: Sellers configure either a hard payment gate (`payment_required_before_pickup = True`) or outstanding receivables (`outstanding_receivable_allowed = True`).
   - Deduction: `Payment` must store `due_date: datetime | None` to record repayment deadlines when `status == OUTSTANDING`, while `SellerCommercialConfiguration` stores `payment_deadline_days`.
4. **15-Day Cooling Hold & Monday Settlement (Step 4 -> Conclusion 4)**:
   - Observation: TTC holds marketplace funds for 15 days before Monday payouts; seller-owned gateways bypass platform custody.
   - Deduction: `Payment` requires `paid_at: datetime | None` to compute `paid_at <= target_date - 15 days`, `settled: bool` for fast un-settled filtering, and `settlement_id: UUID | None` to link disbursed payments to their `SellerSettlement`. `SettlementStatus` must initialize at `SCHEDULED`.
5. **Monthly Billing Invariant & Late Penalties (Step 5 -> Conclusion 5)**:
   - Observation: Sellers receive one platform invoice per calendar month, subject to idempotent daily late fees.
   - Deduction: `SellerBillingInvoice` requires `UniqueConstraint("seller_id", "invoice_month")` to prevent duplicate billing runs. Daily penalties must be calculated deterministically based on `(as_of_date - due_date) * daily_penalty_rate * overdue_balance`.
6. **Marketplace Seller Restriction & Zero-Refund Reselection (Step 6 -> Conclusion 6)**:
   - Observation: Restricted sellers have `PENDING` orders cancelled with `cancellation_reason = "SELLER_RESTRICTED"`. Customers re-select via `new_order.reselected_from_order_id = original_order.id`.
   - Deduction: Because payment occurs only post-pickup approval, `PENDING` orders have zero collected funds; cancellation requires zero gateway refunds. `Order` needs a self-referential relationship `reselected_from_order` to easily traverse re-selection chains.

---

## 3. Caveats

1. **Alembic Down Revision**:
   - The Alembic migration must strictly specify `down_revision = 'a1b2c3d4e5f6'`.
2. **Enum Database Storage**:
   - In SQLite test environments and PostgreSQL, using Python `(str, enum.Enum)` with SQLAlchemy `String(50)` (storing the string value, e.g. `default=PickupStatus.SCHEDULED.value`) avoids native PostgreSQL enum drop/recreate transaction issues in test fixtures while retaining full typing and Pydantic validation.
3. **Database Sequence for Invoices**:
   - Unlike `orders` which uses `order_number_seq`, `seller_billing_invoices` uses the business key `(seller_id, invoice_month)`. If human-readable invoice numbers are desired, a format like `INV-{year}{month:02d}-{seller_short_id}` can be derived deterministically.

---

## 4. Conclusion

1. **SQLAlchemy Models Ready for Implementation**:
   - Complete code blueprints have been produced and published to `/workspaces/TheTextileCare/.agents/explorer_m1_2/report.md` for:
     - `backend/app/models/pickup.py` (`OrderPickup`, `PickupStatus`)
     - `backend/app/models/commercial.py` (`SellerCommercialConfiguration`, enums)
     - `backend/app/models/payment.py` (`Payment`, `Refund`, enums)
     - `backend/app/models/billing.py` (`SellerBillingInvoice`, `SellerSettlement`, enums)
     - `backend/app/models/order.py` (relationships: `reselected_from_order`, `pickup`, `payment`)
     - `backend/app/models/__init__.py` (re-exports)
2. **Pydantic v2 Schemas Ready for Implementation**:
   - Complete schema specifications have been created for:
     - `backend/app/schemas/commercial.py` (with mutual exclusivity validator)
     - `backend/app/schemas/pickup.py` (with inspection details DTOs)
     - `backend/app/schemas/payment.py` (with fee/tax ledger breakdown)
     - `backend/app/schemas/billing.py` (with month regex and penalty DTOs)
     - `backend/app/schemas/settlement.py` (with Monday batch preview DTOs)
     - `backend/app/schemas/order.py` (`OrderReselectRequest`)

---

## 5. Verification Method

To verify these models and schemas once implemented by the worker:

1. **Syntax and Import Verification**:
   ```bash
   python -c "import app.models; import app.schemas; print('Imports successful')"
   ```
2. **Metadata Table Registration**:
   ```bash
   python -c "from app.db import Base; import app.models; tables = set(Base.metadata.tables.keys()); required = {'order_pickups', 'seller_commercial_configs', 'payments', 'refunds', 'seller_billing_invoices', 'seller_settlements', 'orders'}; assert required.issubset(tables), f'Missing tables: {required - tables}'; print('All tables registered successfully!')"
   ```
3. **Schema Validation Test**:
   ```bash
   python -c "
   from decimal import Decimal
   import uuid
   from app.schemas.commercial import CommercialConfigCreate, SellerCommercialModel
   # Test mutual exclusivity validator
   try:
       CommercialConfigCreate(seller_id=uuid.uuid4(), commercial_model=SellerCommercialModel.COMMISSION, commission_rate_percent=Decimal('10.00'), subscription_fee=Decimal('50.00'))
       assert False, 'Failed to reject invalid mutual exclusivity'
   except ValueError:
       print('Mutual exclusivity validator verified!')
   "
   ```
4. **Pytest Database Schema Creation**:
   ```bash
   pytest backend/tests/unit/ -v -k "not test_rate_limit"
   ```
