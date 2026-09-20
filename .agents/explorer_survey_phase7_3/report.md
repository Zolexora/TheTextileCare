# Technical Survey Report: R2 (Commercial Models & Billing) and R4 (Seller Restrictions & Marketplace Re-selection)

**Workspace**: `/workspaces/TheTextileCare`  
**Author**: `explorer_survey_phase7_3`  
**Date**: 2026-09-19  
**Milestone**: Phase 7 — Commercial Billing, Payment Timing, Settlement & Seller Restrictions  

---

## 1. Executive Summary

This report delivers a deep architectural and codebase investigation of **R2 (Commercial Models & Billing)** and **R4 (Seller Restrictions & Marketplace Re-selection)**, evaluating existing components and outlining concrete design patterns and migration strategies aligned with **R5 (Tenant Isolation, Idempotency, Separation of States, and Snapshot Reuse)**.

### Key Discoveries:
1. **Foundation Models Drafted**: Draft models have been added in `backend/app/models/commercial.py`, `backend/app/models/billing.py`, and `backend/app/models/payment.py`, alongside a `reselected_from_order_id` column added to `backend/app/models/order.py`. However, these entities are currently unmigrated in Alembic and lack repository, service, schema, and API route implementations.
2. **Commercial Models Mutual Exclusivity**:
   - **Model 1 (`COMMISSION`)**: Assesses platform commission strictly against the **retained transaction amount** (`order_amount - refunded_amount`), ensuring commission is reversed or reduced proportionally upon full/partial refund. Subscription fee is zero.
   - **Model 2 (`SUBSCRIPTION`)**: Assesses a recurring fixed monthly subscription fee. Order commission is 0.00%.
   - Both models are mutually exclusive per seller and must be strictly validated at the entity and service layers.
3. **Monthly TTC Billing Engine**:
   - Invoices (`seller_billing_invoices`) run on configurable monthly cycles (e.g., 1st of each calendar month) with configurable due date offsets (e.g., 15-day payment grace period).
   - Daily late penalties must be computed idempotently as `overdue_balance * daily_rate * days_overdue`, preventing compounding or duplicate charges on re-runs.
4. **Overdue Enforcement & Seller Restrictions**:
   - Hierarchical enforcement levels: `NONE` $\to$ `WARNING` $\to$ `MARKETPLACE_RESTRICTED` $\to$ `FULL_SUSPENSION`.
   - Reaching `MARKETPLACE_RESTRICTED` or `FULL_SUSPENSION` immediately suppresses marketplace discovery and triggers **automatic cancellation of all `PENDING` orders** with `cancellation_reason = "SELLER_RESTRICTED"`.
   - **Operational Orders Invariant**: `CONFIRMED` and `IN_PROGRESS` orders remain strictly unaffected to avoid disrupting physical laundry processing.
5. **Customer Re-selection & Zero-Refund Invariant**:
   - Under R1, payment is only captured after customer pickup details approval. At `PENDING` status, no customer payment has occurred.
   - Consequently, auto-cancellation of `PENDING` orders requires **zero refunds or gateway adjustments**.
   - Customers can re-select an alternative seller via `POST /api/v1/orders/{order_id}/reselect`. The backend validates that the original order was cancelled with `SELLER_RESTRICTED`, links the new order via `new_order.reselected_from_order_id = original_order.id`, recalculates deterministic pricing using the new seller's catalog, and enforces single-reselection idempotency.

---

## 2. R2: Commercial Models & Billing

### 2.1 Two Mutually Exclusive Commercial Models

In `backend/app/models/commercial.py`, `SellerCommercialConfiguration` defines the commercial settings associated with each seller:

```python
class SellerCommercialModel(str, Enum):
    COMMISSION = "COMMISSION"
    SUBSCRIPTION = "SUBSCRIPTION"

class SellerCommercialConfiguration(Base):
    __tablename__ = "seller_commercial_configs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sellers.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    commercial_model: Mapped[str] = mapped_column(String(50), default=SellerCommercialModel.COMMISSION.value, nullable=False)
    commission_rate_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("10.00"), nullable=False)
    subscription_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    
    # Billing cycle parameters
    billing_cycle_day: Mapped[int] = mapped_column(default=1, nullable=False) # 1st of the month
    invoice_due_days: Mapped[int] = mapped_column(default=15, nullable=False) # 15-day grace period
    daily_late_penalty_rate_percent: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.1000"), nullable=False)
    
    # Overdue enforcement thresholds (days past due)
    overdue_warning_days: Mapped[int] = mapped_column(default=1, nullable=False)
    overdue_restriction_days: Mapped[int] = mapped_column(default=7, nullable=False)
    overdue_suspension_days: Mapped[int] = mapped_column(default=30, nullable=False)
    
    restriction_level: Mapped[str] = mapped_column(String(50), default=SellerRestrictionLevel.NONE.value, nullable=False)
    ...
```

#### Detailed Model Specifications:

| Feature | Model 1: Commission (`COMMISSION`) | Model 2: Subscription (`SUBSCRIPTION`) |
| :--- | :--- | :--- |
| **Primary Revenue** | Percentage of retained order value | Fixed recurring monthly subscription fee |
| **Commission Rate** | $X\%$ (e.g. 10.00%, `commission_rate_percent > 0`) | $0.00\%$ (`commission_rate_percent = 0`) |
| **Subscription Fee**| $0.00$ (`subscription_fee = 0`) | $\$Y$ (e.g. $199.00 / month, `subscription_fee > 0`) |
| **Calculation Base**| **Retained Transaction Amount**: $\text{Amount} - \text{Refunds}$ | Fixed monthly fee regardless of order volume |
| **Refund Handling** | Refund reduces commission proportionally; full refund reduces commission to $0.00$ | Subscription fee unchanged by order refunds |
| **Gateway Offset**  | In TTC Gateway: deducted from weekly seller payouts. In Seller Gateway: billed on monthly TTC invoice. | Billed on monthly TTC invoice (or deducted from settlement). |

#### Mutual Exclusivity Enforcement:
The domain layer (`SellerCommercialService`) and validation schemas must enforce:
1. When `commercial_model == "COMMISSION"`:
   - `commission_rate_percent` must be $> 0.00$ and $\le 100.00$.
   - `subscription_fee` must be exactly $0.00$.
2. When `commercial_model == "SUBSCRIPTION"`:
   - `subscription_fee` must be $> 0.00$.
   - `commission_rate_percent` must be exactly $0.00$.
3. Any transition between models should record an audit entry (`COMMERCIAL_MODEL_CHANGED`) and apply to future orders / future billing periods.

### 2.2 Monthly TTC Billing System & Invoicing Lifecycle

In `backend/app/models/billing.py`, `SellerBillingInvoice` models the monthly billing statement:

```python
class InvoiceStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"

class SellerBillingInvoice(Base):
    __tablename__ = "seller_billing_invoices"
    __table_args__ = (
        UniqueConstraint("seller_id", "invoice_month", name="uq_seller_billing_invoice_month"),
        Index("ix_seller_billing_invoices_seller_status", "seller_id", "status"),
        Index("ix_seller_billing_invoices_due_date", "due_date"),
    )
    
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False, index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    invoice_month: Mapped[date] = mapped_column(Date, nullable=False) # e.g. 2026-09-01
    billing_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    billing_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=InvoiceStatus.PENDING.value, nullable=False)
    
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    tax_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    penalty_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
```

#### Line Itemization (`SellerBillingInvoiceItem`):
An invoice should contain line items for clear auditability:
1. `SUBSCRIPTION_FEE`: Flat monthly charge for the billing period.
2. `COMMISSION_CHARGES`: Aggregate or order-level commission for retained orders processed via Seller Gateway during the cycle.
3. `TAX`: Sales tax or VAT applied to TTC platform service fees.
4. `LATE_PENALTY`: Accumulated late-payment penalty charges.

#### Monthly Billing Generation Workflow:
1. **Trigger**: Scheduled cron job on the `billing_cycle_day` of each month (e.g., 1st of month 00:00 UTC) or admin batch run.
2. **Period Resolution**:
   - `billing_period_start`: Start of prior calendar month (e.g. `2026-08-01 00:00:00 UTC`).
   - `billing_period_end`: End of prior calendar month (e.g. `2026-08-31 23:59:59 UTC`).
   - `invoice_month`: First date of the prior month (`2026-08-01`).
3. **Idempotency Guard**:
   - Query existing invoice by `(seller_id, invoice_month)`. If exists, skip or refresh; never duplicate.
4. **Due Date Assignment**:
   - `due_date = invoice_generation_date + timedelta(days=seller_config.invoice_due_days)`.
   - Default is 15 calendar days from issuance.

### 2.3 Daily Late-Payment Penalties

#### Penalty Formula & Idempotent Calculation:
If an invoice is past its `due_date` and unpaid (`status != PAID`):
1. **Overdue Status Transition**:
   - When `current_date > invoice.due_date` and `invoice.status == InvoiceStatus.PENDING`:
     - Transition `invoice.status` to `InvoiceStatus.OVERDUE`.
2. **Days Overdue**:
   $$D = \max(0, (\text{current\_date} - \text{invoice.due\_date}).\text{days})$$
3. **Daily Penalty Calculation**:
   - Unpaid principal: $P = \text{invoice.subtotal} + \text{invoice.tax\_total}$.
   - Daily penalty rate: $r = \frac{\text{daily\_late\_penalty\_rate\_percent}}{100}$ (e.g. $0.001$ for $0.1\%$).
   - Total accumulated penalty:
     $$\text{penalty\_total} = \text{round\_half\_up}(P \times r \times D, 2)$$
   - Total invoice amount:
     $$\text{total\_amount} = P + \text{penalty\_total}$$
4. **Deterministic Idempotency**:
   - Because $P$, $r$, and $D$ are derived deterministically from the current date and immutable invoice base amounts, recalculating this job multiple times on the same date produces the exact same result without duplicate accumulation.

---

## 3. R4: Seller Restrictions & Marketplace Re-selection

### 3.1 Overdue Enforcement Levels

The platform enforces four progressive restriction levels based on overdue invoice duration:

```
[Level 0: NONE] ────────────> [Level 1: WARNING] ────────────> [Level 2: MARKETPLACE_RESTRICTED] ────────────> [Level 3: FULL_SUSPENSION]
(Current / Paid)               (1-6 days overdue)              (7-29 days overdue)                              (30+ days overdue)
- Normal operations            - Dashboard warning banner      - Hidden from Marketplace discovery              - White-label disabled
- Marketplace active           - No operational blocks         - PENDING orders AUTO-CANCELLED                  - Portal login blocked
- White-label active           - Settlement continues          - Cannot receive new marketplace orders          - All operations frozen
                                                               - CONFIRMED & IN_PROGRESS orders continue!
```

#### Enforcement Rules:
1. **Level 0 (`NONE`)**:
   - Seller has 0 overdue invoices.
   - Marketplace status is `PUBLISHED` (if active), white-label active, full platform access.
2. **Level 1 (`WARNING`)**:
   - $1 \le D < \text{overdue\_restriction\_days}$ (e.g. 1 to 6 days overdue).
   - In-app notification / alert banner in seller dashboard.
   - Marketplace listings, ordering, and fulfillment remain active.
3. **Level 2 (`MARKETPLACE_RESTRICTED`)**:
   - $\text{overdue\_restriction\_days} \le D < \text{overdue\_suspension\_days}$ (e.g. 7 to 29 days overdue).
   - **Marketplace Discovery Suppression**:
     - `MarketplaceRepository.list_published_sellers` automatically excludes sellers with `restriction_level in ('MARKETPLACE_RESTRICTED', 'FULL_SUSPENSION')`.
     - Direct profile access `MarketplaceRepository.get_published_seller` returns `None` (404).
   - **Order Creation Rejection**:
     - `OrderService.create_order` checks seller restriction level; rejects with 403 `SELLER_RESTRICTED` if restricted.
   - **Automatic Cancellation of PENDING Orders**:
     - All orders for this seller with `status == OrderStatus.PENDING.value` are transitioned to `OrderStatus.CANCELLED.value`.
     - `cancellation_reason = "SELLER_RESTRICTED"`.
   - **Operational Orders Invariant**:
     - Orders already in `CONFIRMED` or `IN_PROGRESS` are **unaffected**.
     - Sellers remain contractually and physically obligated to finish and complete ongoing customer garments.
4. **Level 3 (`FULL_SUSPENSION`)**:
   - $D \ge \text{overdue\_suspension\_days}$ (e.g. 30+ days overdue).
   - Both Marketplace and White-Label stores are disabled.
   - Seller staff cannot access seller portal endpoints (middleware/dependencies raise 403 `ACCOUNT_SUSPENDED`).
5. **Cure / Restoration**:
   - Once all overdue invoices are paid (`status = PAID`), the restriction evaluation service evaluates outstanding balance.
   - If no overdue invoices remain, `restriction_level` returns to `NONE`.
   - Seller marketplace visibility is restored.

### 3.2 Automatic Cancellation of PENDING Orders

When a seller transitions into `MARKETPLACE_RESTRICTED` or `FULL_SUSPENSION`:

```python
def apply_seller_restriction(seller_id: uuid.UUID, new_level: SellerRestrictionLevel):
    # 1. Update commercial configuration
    config = db.query(SellerCommercialConfiguration).filter_by(seller_id=seller_id).one()
    old_level = config.restriction_level
    config.restriction_level = new_level.value

    # 2. If entering restricted state, cancel all PENDING orders
    if new_level in (SellerRestrictionLevel.MARKETPLACE_RESTRICTED, SellerRestrictionLevel.FULL_SUSPENSION):
        pending_orders = db.query(Order).filter(
            Order.seller_id == seller_id,
            Order.status == OrderStatus.PENDING.value
        ).all()
        
        for order in pending_orders:
            order.status = OrderStatus.CANCELLED.value
            order.cancelled_at = datetime.now(timezone.utc)
            order.cancellation_reason = "SELLER_RESTRICTED"
            
            # Record status history
            order_status_history = OrderStatusHistory(
                order_id=order.id,
                from_status=OrderStatus.PENDING.value,
                to_status=OrderStatus.CANCELLED.value,
                reason="SELLER_RESTRICTED",
                actor_user_id=None # System action
            )
            db.add(order_status_history)
            
            # Audit log
            audit_svc.log_event(
                event_type="ORDER_CANCELLED",
                tenant_id=order.tenant_id,
                entity_type="Order",
                entity_id=str(order.id),
                payload={
                    "order_number": order.order_number,
                    "reason": "SELLER_RESTRICTED",
                    "automated": True
                }
            )
```

#### Why `CONFIRMED` and `IN_PROGRESS` Orders Must Not Be Cancelled:
- In textile cleaning and garment care, `CONFIRMED` means pickup has been scheduled or clothes have been received, and `IN_PROGRESS` means physical items are already tagged, washed, dry-cleaned, or ironed.
- Cancelling an in-progress order midway creates extreme consumer harm (garments stranded inside a restricted facility).
- The platform therefore strictly scopes the automated cancellation to `PENDING` orders (unacknowledged/unconfirmed orders where fulfillment has not begun).

### 3.3 Customer Seller Re-selection Architecture

#### Zero-Refund Invariant:
Under Phase 7 R1 ("Payment requested only after customer approves actual pickup details, not at order creation"):
- When an order is in `PENDING`, the customer has **not yet paid**.
- The payment record is either non-existent or in `PENDING` status with $0.00$ captured.
- Therefore, auto-cancelling a `PENDING` order with `SELLER_RESTRICTED` does **NOT** require any payment gateway refund, chargeback, or fee clawback.

#### Re-selection Flow & Data Contract:

```
+───────────────────────────+
| Original Order            |
| - ID: order-aaa           |
| - Status: CANCELLED       |
| - Reason: SELLER_RESTRICTED
+─────────────┬─────────────+
              │
              │ Customer calls:
              │ POST /api/v1/orders/order-aaa/reselect
              │ { new_seller_id: seller-bbb, new_branch_id: branch-bbb, items: [...] }
              ▼
+───────────────────────────────────────────────────────────+
| New Order                                                 |
| - ID: order-ccc                                           |
| - reselected_from_order_id: order-aaa                     |
| - Status: PENDING                                         |
| - Snapshots: fresh pricing & catalog from seller-bbb      |
| - New unique order_number (e.g. TTC-202609-00042)         |
+───────────────────────────────────────────────────────────+
```

#### API Specification: `POST /api/v1/orders/{order_id}/reselect`
- **Authentication**: Customer context (`require_authenticated_user`).
- **Request Body (`OrderReselectRequest`)**:
  ```json
  {
    "new_seller_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "new_branch_id": "7ca85f64-5717-4562-b3fc-2c963f66afa7",
    "items": [
      {
        "service_id": "...",
        "service_item_id": "...",
        "quantity": "2.000",
        "unit_type": "ITEM",
        "addons": []
      }
    ],
    "customer_address_id": "optional-uuid"
  }
  ```
- **Validation Pipeline**:
  1. `original_order = order_repo.get_by_id(order_id)`
  2. Verify customer ownership: `original_order.customer_id == customer.id`.
  3. Verify status: `original_order.status == OrderStatus.CANCELLED.value`.
  4. Verify reason: `original_order.cancellation_reason == "SELLER_RESTRICTED"`.
  5. Verify single-reselection constraint: Query if any order has `reselected_from_order_id == original_order.id`. If found, raise 409 `ALREADY_RESELECTED`.
  6. Verify `new_seller`: Must be active, published, and `restriction_level in ('NONE', 'WARNING')`.
  7. Deterministic Pricing: Call `PricingService.calculate` with `tenant_id=new_seller.tenant_id`.
  8. Create new order with:
     - `reselected_from_order_id = original_order.id`
     - Fresh snapshots (`pricing_snapshot`, `catalog_snapshot`, `customer_snapshot`)
     - Status: `PENDING`
     - Status history: `"Reselected from order {original_order.order_number}"`
     - Audit log: `ORDER_RESELECTED`.

---

## 4. R5: Cross-Cutting Architectural Constraints

### 4.1 Strict Tenant & Seller Isolation
1. **Multi-Tenancy Guard**:
   - Sellers in TTC have a 1:1 relationship with Tenants (`sellers.tenant_id == tenants.id`).
   - All commercial configurations (`seller_commercial_configs`) and billing invoices (`seller_billing_invoices`) include `tenant_id` foreign keys indexed alongside `seller_id`.
   - In seller-facing endpoints (`/api/v1/seller/invoices/*`, `/api/v1/seller/commercial/*`), queries strictly resolve tenant identity via `TenantContext` (`require_tenant_context`).
   - A seller in Tenant A can never view or modify invoices, settlements, or commercial configurations belonging to Tenant B (guaranteed by explicit tenant filtering and repository boundaries).

### 4.2 Financial & Operational Mutation Idempotency
1. **Billing Invoices**:
   - `UniqueConstraint("seller_id", "invoice_month", name="uq_seller_billing_invoice_month")` guarantees that only one invoice can ever be generated for a seller in a given calendar month.
2. **Order Re-selection**:
   - A customer submitting multiple simultaneous re-selection requests with the same `Idempotency-Key` receives the same new order instance without duplicate creations.
   - Even without an idempotency key, the database/service level constraint (`reselected_from_order_id` uniqueness or verification) ensures that an order cancelled with `SELLER_RESTRICTED` can only be re-selected once.
3. **Penalty Calculations**:
   - Late penalty calculations are pure mathematical functions of overdue days: $P \times r \times D$. Re-running penalty evaluations at any point during a day produces an identical total amount.

### 4.3 Clean Separation of Operational and Payment States
- **The Golden Rule of R5**: `OrderStatus` MUST NOT be overloaded with payment statuses!
- `OrderStatus` records only operational states: `DRAFT`, `PENDING`, `CONFIRMED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`.
- `PaymentStatus` records customer transaction states: `PENDING`, `SUCCEEDED`, `FAILED`, `OUTSTANDING`, `REFUNDED`, `PARTIALLY_REFUNDED`.
- `InvoiceStatus` records B2B billing states: `PENDING`, `PAID`, `OVERDUE`, `CANCELLED`.
- `SellerRestrictionLevel` records compliance/enforcement states: `NONE`, `WARNING`, `MARKETPLACE_RESTRICTED`, `WHITE_LABEL_RESTRICTED`, `FULL_SUSPENSION`.

### 4.4 Reuse of Pricing & Snapshot Architectures
- In Phase 5, TTC established an authoritative, deterministic `PricingService` structurally isolated from catalog data.
- During re-selection to an alternative seller:
  - Catalog entities (services, items, addons) and prices differ between sellers.
  - The new order does NOT copy stale prices or snapshots from the restricted seller.
  - It runs the new items through `PricingService.calculate` for the new seller, generating mathematically exact `Decimal` totals and fresh JSON snapshots.

---

## 5. Existing Codebase Mapping & Gap Analysis

| Requirement | Existing Code / Model | Status | Gaps to Implement |
| :--- | :--- | :--- | :--- |
| **Model 1 & 2 Config** | `backend/app/models/commercial.py` | Drafted | Add Alembic migration, add billing cycle/penalty fields, implement `SellerCommercialService`, schemas, and API routes. |
| **Billing Invoices** | `backend/app/models/billing.py` | Drafted | Add Alembic migration, add invoice items table, unique constraint on `(seller_id, invoice_month)`, implement `BillingService` and overdue evaluation logic. |
| **Overdue Penalties** | `SellerBillingInvoice.penalty_total` | Drafted | Implement daily deterministic penalty calculator service. |
| **Enforcement Levels** | `SellerRestrictionLevel` in `commercial.py` | Drafted | Hook restriction check into `MarketplaceRepository` queries, implement auto-cancellation of `PENDING` orders upon restriction. |
| **Pending Cancellation** | `OrderService._transition` in `order.py` | Supported | Implement bulk cancellation method in `OrderService` for `SELLER_RESTRICTED` with audit logging. |
| **Order Re-selection** | `Order.reselected_from_order_id` in `order.py` | Drafted | Add column to Alembic migration, add `reselect_order` method in `OrderService`, add schema `OrderReselectRequest`, add endpoint `POST /api/v1/orders/{order_id}/reselect`. |
| **Database Migrations** | `migrations/versions/a1b2c3d4e5f6_phase7_order_foundation.py` | Phase 7 Head | Create new migration `b2c3d4e5f6a7_phase7_commercial_billing_restrictions.py` for commercial, payment, billing, and re-selection fields. |

---

## 6. Actionable Implementation & Verification Plan

### 6.1 Database Migration Plan
Create Alembic migration `b2c3d4e5f6a7_phase7_commercial_billing_restrictions.py`:
1. `ALTER TABLE orders ADD COLUMN reselected_from_order_id UUID REFERENCES orders(id) ON DELETE SET NULL;`
2. `CREATE TABLE seller_commercial_configs (...);`
3. `CREATE TABLE payments (...);`
4. `CREATE TABLE refunds (...);`
5. `CREATE TABLE seller_billing_invoices (...);`
6. `CREATE TABLE seller_settlements (...);`
7. Add indexes and unique constraints:
   - `uq_seller_billing_invoice_month` on `(seller_id, invoice_month)`
   - `ix_orders_reselected_from_order_id` on `reselected_from_order_id`

### 6.2 New Services & Endpoints to Introduce
1. **`app/services/commercial.py` (`CommercialService`)**:
   - `get_or_create_config(seller_id)`
   - `update_config(seller_id, request)`
   - `evaluate_seller_overdue_and_restrictions(current_date)`
   - `apply_restriction(seller_id, new_level)`
2. **`app/services/billing.py` (`BillingService`)**:
   - `generate_monthly_invoices(invoice_month)`
   - `calculate_daily_penalties(current_date)`
   - `record_invoice_payment(invoice_id, payment_details)`
3. **`app/services/order.py` (`OrderService`)**:
   - `cancel_pending_orders_for_restricted_seller(seller_id)`
   - `reselect_order(customer_user_id, original_order_id, request, idempotency_key)`
4. **API Endpoints**:
   - `POST /api/v1/orders/{order_id}/reselect` (Customer order re-selection)
   - `GET /api/v1/seller/commercial/config` (Seller views commercial settings)
   - `PATCH /api/v1/admin/sellers/{seller_id}/commercial` (Admin sets commercial model & rates)
   - `GET /api/v1/seller/invoices` (Seller views monthly invoices)
   - `GET /api/v1/seller/invoices/{invoice_id}` (Seller views invoice detail)
   - `POST /api/v1/admin/billing/generate` (Admin triggers monthly billing run)
   - `POST /api/v1/admin/billing/evaluate-overdue` (Admin triggers daily overdue & penalty evaluation)

### 6.3 Test Verification Matrix
1. **Commercial Model Validation**:
   - Verify Model 1 calculates commission on retained amount ($100 order refunded $20 $\to$ commission on $80).
   - Verify Model 2 calculates flat subscription fee ($199) and 0% commission on orders.
   - Verify mutual exclusivity validation rejects invalid combinations.
2. **Monthly Invoicing & Penalties**:
   - Verify invoice generation is idempotent per `(seller_id, invoice_month)`.
   - Verify daily late penalty calculation is mathematically exact and idempotent on re-runs.
3. **Seller Restriction & Auto-Cancellation**:
   - Verify reaching `MARKETPLACE_RESTRICTED` immediately cancels `PENDING` orders with reason `SELLER_RESTRICTED`.
   - Verify `CONFIRMED` and `IN_PROGRESS` orders remain active and unaffected.
   - Verify restricted seller is omitted from marketplace discovery.
4. **Customer Re-selection**:
   - Verify customer cannot re-select an order that is not `CANCELLED` with `SELLER_RESTRICTED`.
   - Verify customer cannot re-select the same order more than once (409 conflict).
   - Verify new order correctly sets `reselected_from_order_id`, executes `PricingService`, creates snapshots, and requires no refunds.
