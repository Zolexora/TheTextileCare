# Phase 7 Investigation Report: Payment Abstraction, Timing & Settlement (R1 & R3)

**Author:** `explorer_survey_phase7_2`  
**Date:** 2026-09-19  
**Domain Scope:** R1 (Payment Abstraction & Timing) and R3 (Settlement Logic)  
**Target Codebase:** `/workspaces/TheTextileCare`  

---

## 1. Executive Summary

In Phase 7, TheTextileCare (TTC) extends its commerce foundation to include real-world commercial operations: post-pickup payment approvals, gateway routing (Platform TTC vs Seller direct), dual payment failure modes, and a 15-day cooling hold with Monday settlement cycles.

A fundamental requirement is that **`OrderStatus` must never be overloaded with payment states**. The physical laundry lifecycle (`OrderStatus`) and the financial lifecycle (`PaymentStatus`) are orthogonal concerns governed by separate state machines. Furthermore, textile care operations require that customers are **not charged at order creation**; instead, payment is requested only after the seller inspects the garments and the customer explicitly approves the actual pickup details.

This report establishes the architectural blueprint, mathematical models, state machines, database schemas, and API contracts necessary to implement R1 and R3 seamlessly on top of the existing Phase 7 Order Foundation.

---

## 2. Existing Codebase Analysis

### 2.1 Current Order Domain (`backend/app/models/order.py`, `services/order.py`)
- **OrderStatus Enum**: Currently consists of six operational states:
  ```python
  class OrderStatus(str, Enum):
      DRAFT = "DRAFT"
      PENDING = "PENDING"
      CONFIRMED = "CONFIRMED"
      IN_PROGRESS = "IN_PROGRESS"
      COMPLETED = "COMPLETED"
      CANCELLED = "CANCELLED"
  ```
- **State Transitions**:
  - `PENDING` -> `CONFIRMED` (Seller acceptance via `/api/v1/seller/orders/{id}/confirm`)
  - `PENDING` -> `CANCELLED` (Customer cancellation or seller rejection via `/api/v1/seller/orders/{id}/reject`)
  - `CONFIRMED` -> `IN_PROGRESS` (Seller start processing via `/api/v1/seller/orders/{id}/start`)
  - `CONFIRMED` -> `CANCELLED` (Customer cancellation or seller cancellation via `/api/v1/seller/orders/{id}/cancel`)
  - `IN_PROGRESS` -> `COMPLETED` (Seller completion via `/api/v1/seller/orders/{id}/complete`)
- **Commercial Snapshotting**: `Order` stores immutable snapshots (`pricing_snapshot`, `catalog_snapshot`, `customer_snapshot`). No payment records, payment gateway identifiers, or pickup inspection logs are currently persisted.
- **Order Creation Flow**: `OrderService.create_order()` validates seller/branch/catalog, invokes `PricingService.calculate()`, checks price deviation, creates the `Order` in `PENDING` status, and does **not** charge any card or interact with a payment gateway.

### 2.2 Survey of Working Tree Artifacts
In `backend/app/models/`, preliminary uncommitted models were found:
1. `payment.py`: Defines `Payment` and `Refund` tables with basic fee/tax breakdown (`gateway_fee`, `gateway_tax`, `ttc_commission`, `ttc_commission_tax`, `refunded_amount`, `retained_amount`).
   *Gaps identified:*
   - Missing `seller_id` column (critical for seller multi-tenancy and indexation).
   - Missing `paid_at` timestamp (mandatory for calculating the 15-day settlement cooling period).
   - Missing `due_date` timestamp (mandatory for tracking `OUTSTANDING` receivable deadlines).
   - Missing foreign key `seller_settlement_id` to link settled payments to their settlement payout.
2. `commercial.py`: Defines `SellerCommercialConfiguration` (`marketplace_gateway`, `white_label_gateway`, `commercial_model`, `commission_rate_percent`, `subscription_fee`, `payment_required_before_pickup`, `outstanding_receivable_allowed`, `payment_deadline_days`, `restriction_level`).
   *Alignment:* Perfectly models the seller-level flags required by R1 and R2.
3. `billing.py`: Defines `SellerBillingInvoice` and `SellerSettlement`.
   *Alignment:* `SellerSettlement` contains `seller_id`, `gateway_type`, `status`, `currency`, `amount`, `scheduled_for` (Date), `processed_at`, and `reference_id`.
4. **Pickup Domain**: Completely absent from the database and codebase. Only textual references exist in `CustomerAddress` ("Private customer delivery / pickup address").

---

## 3. R1: Payment Abstraction & Timing

### 3.1 Timing Rule: Post-Pickup Approval (Not at Order Creation)

#### The Business Rationale
In on-demand laundry and dry cleaning:
1. When a customer places an order on the marketplace or store, they provide an **estimate** (e.g. 5 shirts, 1 bedsheet, 1 bag of wash-and-fold).
2. When the seller or driver physically picks up the garments, actual physical realities are discovered:
   - Piece counts may differ (e.g. 4 cotton shirts + 1 silk blouse).
   - Wash-and-fold weight is measured on a calibrated scale (e.g. 6.4 kg instead of 5.0 kg).
   - Stains, tears, or delicate fabric requiring specialized surcharges or different services are identified.
3. If payment were charged at order creation:
   - Any quantity or weight adjustment would require messy pre-auth adjustments, void/re-issues, incremental card captures, or refund fees.
   - Pre-authorizations typically expire within 5 to 7 days, which is problematic if pickup is scheduled days out.
4. **Authoritative Timing Rule**:
   - Order creation creates an order in `PENDING` with estimated pricing snapshots. **Zero payment transactions occur.**
   - The seller accepts the order (`CONFIRMED`).
   - The pickup takes place, and the seller submits the **actual pickup details**.
   - The customer reviews and **approves the actual pickup details**.
   - **Payment is requested ONLY upon customer approval of actual pickup details.**

### 3.2 Pickup Details Lifecycle & Architecture

A dedicated entity `OrderPickup` (`order_pickups`) models the physical collection and customer verification process:

```
[Order Placed: PENDING]
        │
        ▼ (Seller Confirms Order)
[Order Status: CONFIRMED]
        │
        ▼ (Driver arrives, inspects & weighs laundry)
[Pickup Status: DETAILS_SUBMITTED]
   (Seller submits actual items, weights, condition notes)
        │
        ├── Customer Rejects ──► [Pickup Status: REJECTED] ──► Seller re-inspects/re-submits
        │
        ▼ Customer Approves
[Pickup Status: APPROVED]
        │
        ▼
   [PAYMENT INITIATED] (Payment requested from customer)
        │
        ├── Payment Succeeded ────────────────────────────────┐
        │                                                     ▼
        ├── Payment Failed + Mode B (Outstanding Allowed) ────┼──► [Pickup Status: COMPLETED]
        │                                                     │    [Order Status: IN_PROGRESS]
        └── Payment Failed + Mode A (Payment Required) ───────┘
                     │
                     ▼
          [BLOCKED from Completion]
          (Pickup held; Customer prompted to retry payment)
```

#### Pickup Lifecycle States (`PickupStatus`)
- `SCHEDULED`: Initial state upon order confirmation.
- `DETAILS_SUBMITTED`: Seller/driver has uploaded the verified item count, weights, condition notes, and pricing adjustments.
- `APPROVED`: Customer has verified and approved the submitted pickup details. Triggers payment request.
- `REJECTED`: Customer contested the counts/notes; seller must review.
- `COMPLETED`: Physical collection finalized; garments transported to processing plant.

### 3.3 Dual Payment Failure Modes

Sellers configure their failure mode via `SellerCommercialConfiguration`:

| Feature | Mode 1: Required Before Pickup Completion | Mode 2: Allowed as Outstanding Receivable |
|---|---|---|
| **Configuration** | `payment_required_before_pickup = True`<br>`outstanding_receivable_allowed = False` | `payment_required_before_pickup = False`<br>`outstanding_receivable_allowed = True` |
| **Payment Success** | Pickup completed -> Order moves to `IN_PROGRESS` | Pickup completed -> Order moves to `IN_PROGRESS` |
| **Payment Failure** | `Payment.status = FAILED`.<br>Seller is **blocked** from calling `/pickup/complete` or starting order.<br>Returns `409 Conflict: PAYMENT_REQUIRED_BEFORE_PICKUP`. | `Payment.status = OUTSTANDING`.<br>Seller is **allowed** to complete pickup.<br>Order moves to `IN_PROGRESS`. |
| **Financial Tracking** | No debt created; customer must retry payment to unblock order. | Outstanding receivable tracked on `Payment` and customer balance with `due_date = now + payment_deadline_days`. |
| **Customer Impact** | Laundry cannot be processed until payment clears. | Laundry processed immediately; customer billed with payment deadline. |

### 3.4 Dual Payment Gateway Scenarios

The platform supports two distinct gateway execution models:

```
                                  CUSTOMER PAYMENT
                                         │
                 ┌───────────────────────┴───────────────────────┐
                 ▼                                               ▼
         [TTC_GATEWAY]                                   [SELLER_GATEWAY]
   (Platform Master Account)                       (Seller Direct Merchant Account)
                 │                                               │
  ┌──────────────┴──────────────┐                 ┌──────────────┴──────────────┐
  │ • Funds collected by TTC    │                 │ • Funds direct to seller    │
  │ • Gateway fee/tax deducted  │                 │ • Gateway fee paid by seller│
  │ • TTC commission deducted   │                 │ • TTC holds ZERO funds      │
  │ • Net funds held by TTC     │                 │ • NO settlement transfers   │
  │ • 15-day cooling hold       │                 │ • TTC commission recorded   │
  │ • Monday payout transfer    │                 │   and billed monthly (R2)   │
  └─────────────────────────────┘                 └─────────────────────────────┘
```

#### Gateway Comparison Table
| Dimension | TTC Payment Gateway (`TTC_GATEWAY`) | Seller-Owned Gateway (`SELLER_GATEWAY`) |
|---|---|---|
| **Merchant of Record** | TheTextileCare (Platform) | Seller |
| **Customer Funds Destination** | TTC Master Bank/Gateway Account | Seller Bank/Gateway Account |
| **Gateway Fees & Gateway Taxes** | Borne by transaction; deducted by TTC before seller payout | Borne directly by seller via their own gateway contract |
| **TTC Commission Collection** | Retained automatically at source from transaction payout | Invoiced monthly via `SellerBillingInvoice` (R2) |
| **Cooling Period** | **15-day cooling hold** enforced on TTC net payable funds | **None** (TTC has no custody of funds) |
| **Settlement Transfers** | **Monday settlement batch** generates `SellerSettlement` | **None** (TTC creates no settlement records) |
| **Typical Usage** | Marketplace orders (`marketplace_gateway`) | White-label / private brand portals (`white_label_gateway`) |

### 3.5 Financial Ledger & Mathematical Breakdown

TTC enforces strict `Decimal(12, 2)` arithmetic using `ROUND_HALF_UP` for all monetary entries:

```
Gross Customer Payment: P
Gateway Fee:            GF  (e.g., 2.0% + fixed fee)
Gateway Tax:            GT  (e.g., 18% GST on Gateway Fee)
TTC Commission:         TC  (e.g., 10% of Retained Order Amount)
TTC Commission Tax:     TT  (e.g., 18% GST on TTC Commission)
Net Seller Share:       NS  = P - (GF + GT) - (TC + TT)
```

#### Recording Separation Rule
1. `gateway_fee` and `gateway_tax` belong to the **payment gateway provider** (third-party payment processor cost).
2. `ttc_commission` and `ttc_commission_tax` belong to **TheTextileCare** (platform revenue).
3. These four components are stored in distinct database columns on `Payment`:
   - `gateway_fee: Numeric(12, 2)`
   - `gateway_tax: Numeric(12, 2)`
   - `ttc_commission: Numeric(12, 2)`
   - `ttc_commission_tax: Numeric(12, 2)`

#### Refund Accounting & Commission Adjustment
When a customer refund occurs (full or partial):
```
Refund Amount: R
Retained Amount: Ret = P - sum(R)
```
- Gateway fee reversal: `gateway_fee_reversed` and `gateway_tax_reversed` (dependent on gateway refund policy).
- TTC commission adjustment: TTC platform commission is recalculated based on the **retained amount**:
  $$\text{Adjusted Commission} = \text{Ret} \times \text{Commission Rate}$$
  $$\text{Commission Reversed} = \text{Original Commission} - \text{Adjusted Commission}$$
- If `Ret == 0`: `Payment.status = PaymentStatus.REFUNDED`
- If `0 < Ret < P`: `Payment.status = PaymentStatus.PARTIALLY_REFUNDED`

### 3.6 Non-Overloaded OrderStatus Architectural Invariant

**Constraint**: `OrderStatus` MUST NOT contain payment states (`PAID`, `UNPAID`, `PAYMENT_FAILED`, `REFUNDED`).

#### Why Separation is Essential
- `OrderStatus` reflects the **physical garment state** in the cleaning facility:
  `DRAFT` -> `PENDING` -> `CONFIRMED` -> `IN_PROGRESS` -> `COMPLETED` (or `CANCELLED`).
- `PaymentStatus` reflects the **financial balance state**:
  `PENDING` -> `SUCCEEDED` / `FAILED` -> `OUTSTANDING` -> `PARTIALLY_REFUNDED` / `REFUNDED`.
- `PickupStatus` reflects the **inspection & collection state**:
  `SCHEDULED` -> `DETAILS_SUBMITTED` -> `APPROVED` / `REJECTED` -> `COMPLETED`.

#### Cross-State Orthogonality Matrix
| OrderStatus | Allowed PickupStatus | Allowed PaymentStatus | Operational Meaning |
|---|---|---|---|
| `PENDING` | None / Scheduled | None / Not Created | Order placed; awaiting seller confirmation. No charge. |
| `CONFIRMED` | `DETAILS_SUBMITTED`, `APPROVED`, `REJECTED` | `PENDING`, `FAILED`, `SUCCEEDED` | Laundry inspected; customer review & payment in progress. |
| `IN_PROGRESS` | `COMPLETED` | `SUCCEEDED` or `OUTSTANDING` | Laundry in wash/dry/press. Payment either paid or receivable. |
| `COMPLETED` | `COMPLETED` | `SUCCEEDED` or `OUTSTANDING` | Laundry cleaned & returned. Payment complete or on terms. |
| `CANCELLED` | `REJECTED` or None | `REFUNDED` or None | Order cancelled; pre-payment (if any) fully refunded. |

---

## 4. R3: Settlement Logic

### 4.1 TTC Gateway Settlement Architecture

For orders paid through `TTC_GATEWAY`:
1. Customer funds are held in TTC's escrow/settlement pool.
2. Funds are locked for a **15-day cooling period** starting from `paid_at`.
3. After 15 days, funds transition from `COOLING_HOLD` to `ELIGIBLE_FOR_SETTLEMENT`.
4. On **Mondays**, the platform executes weekly batch settlement transfers to sellers.

```
Payment Succeeded at paid_at (e.g. Wednesday, Sep 2)
                 │
                 ▼
      [15-DAY COOLING PERIOD]
 (Protects against damage claims, customer disputes, refunds)
                 │
                 ▼
      Cooling Ends: paid_at + 15 days (Thursday, Sep 17)
                 │
                 ▼
      [STATUS: ELIGIBLE FOR SETTLEMENT]
                 │
                 ▼
      Next Scheduled Settlement Payout: MONDAY (Monday, Sep 21)
                 │
                 ▼
      Aggregated into SellerSettlement Transfer
      (Processed & Disbursed to Seller Bank Account)
```

### 4.2 Monday Payout Calendar Mechanics

The settlement service calculates eligibility deterministically:

$$\text{Eligible Date} = \text{Payment.paid\_at} + 15\text{ days}$$
$$\text{Is Eligible on Date } D \iff \text{Eligible Date} \le D$$

When running a settlement on Monday $M$ (`M.weekday() == 0`):
$$\text{Eligible Payments} = \{ P \mid P.\text{gateway\_type} = \text{TTC\_GATEWAY} \land P.\text{status} \in \{\text{SUCCEEDED}, \text{PARTIALLY\_REFUNDED}\} \land P.\text{settlement\_id IS NULL} \land (P.\text{paid\_at} + 15\text{ days}) \le M \}$$

#### Example Calendar Schedule
| Payment Succeeded (`paid_at`) | 15-Day Hold Expires | Eligible Payout Monday |
|---|---|---|
| Monday, Sep 1, 2026 | Tuesday, Sep 16, 2026 | Monday, Sep 21, 2026 |
| Wednesday, Sep 3, 2026 | Thursday, Sep 18, 2026 | Monday, Sep 21, 2026 |
| Sunday, Sep 6, 2026 | Monday, Sep 21, 2026 | Monday, Sep 21, 2026 (eligible on the Monday) |
| Tuesday, Sep 8, 2026 | Wednesday, Sep 23, 2026 | Monday, Sep 28, 2026 |

### 4.3 Weekly Aggregation Algorithm
1. The platform executes `SettlementService.process_monday_settlement(target_date=date.today())`.
2. Verifies that `target_date` is a Monday (or calculates the next Monday if run in preview mode).
3. Queries eligible payments grouped by `(tenant_id, seller_id, currency)`.
4. For each group:
   - Sums net amounts:
     $$\text{Total Payout} = \sum \left[ \text{retained\_amount} - (\text{gateway\_fee} - \text{gateway\_fee\_reversed}) - (\text{gateway\_tax} - \text{gateway\_tax\_reversed}) - \text{ttc\_commission} - \text{ttc\_commission\_tax} \right]$$
   - If $\text{Total Payout} > 0$:
     - Generates a unique reference: `STL-{YYYYMMDD}-{SELLER_SLUG}-{UUID[:6]}`.
     - Creates `SellerSettlement` record with status `PENDING` -> `PROCESSING` -> `SETTLED`.
     - Updates all included `Payment` rows: `payment.seller_settlement_id = settlement.id`.
     - Logs an immutable `AuditEvent` (`SETTLEMENT_BATCH_GENERATED`).
5. Fully idempotent: Running the settlement twice on the same Monday ignores already-settled payments (`seller_settlement_id IS NOT NULL`).

### 4.4 Seller-Owned Gateway Exemption
For sellers configured with `SELLER_GATEWAY`:
- Customer funds flowed directly to the seller's account.
- **TTC does not impose a 15-day hold.**
- **TTC does not create `SellerSettlement` records.**
- Commission owed to TTC is tracked in `Payment.ttc_commission` and billed via `SellerBillingInvoice` under R2.

---

## 5. Proposed Data Models & Schemas

### 5.1 `order_pickups` Table (`app/models/order.py` or `app/models/pickup.py`)
```python
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
        Index("ix_order_pickups_seller_id_status", "seller_id", "status"),
        Index("ix_order_pickups_tenant_id", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False)

    status: Mapped[str] = mapped_column(String(50), default=PickupStatus.SCHEDULED.value, nullable=False)
    
    # Inspection snapshots
    actual_items_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    driver_notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    customer_notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Timestamps
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
```

### 5.2 Refined `payments` Table (`app/models/payment.py`)
```python
class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    OUTSTANDING = "OUTSTANDING"
    REFUNDED = "REFUNDED"
    PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED"

class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_order_id", "order_id"),
        Index("ix_payments_tenant_id", "tenant_id"),
        Index("ix_payments_seller_id_created_at", "seller_id", "created_at"),
        Index("ix_payments_customer_id", "customer_id"),
        Index("ix_payments_settlement_cooling", "gateway_type", "status", "seller_settlement_id", "paid_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), nullable=False)
    seller_settlement_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("seller_settlements.id", ondelete="SET NULL"), nullable=True)

    gateway_type: Mapped[str] = mapped_column(String(50), nullable=False)  # TTC_GATEWAY, SELLER_GATEWAY
    status: Mapped[str] = mapped_column(String(50), default=PaymentStatus.PENDING.value, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Gateway costs (recorded separately)
    gateway_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    gateway_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    # TTC platform commission (recorded separately)
    ttc_commission: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    ttc_commission_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    # Retained balance
    refunded_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    retained_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Identifiers & dates
    gateway_transaction_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # for OUTSTANDING mode

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
```

### 5.3 Refined `seller_settlements` Table (`app/models/billing.py`)
```python
class SettlementStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SETTLED = "SETTLED"
    FAILED = "FAILED"

class SellerSettlement(Base):
    __tablename__ = "seller_settlements"
    __table_args__ = (
        Index("ix_seller_settlements_seller_id_scheduled", "seller_id", "scheduled_for"),
        Index("ix_seller_settlements_tenant_id", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)

    gateway_type: Mapped[str] = mapped_column(String(50), nullable=False)  # TTC_GATEWAY
    status: Mapped[str] = mapped_column(String(50), default=SettlementStatus.PENDING.value, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    scheduled_for: Mapped[date] = mapped_column(Date, nullable=False)  # Monday date
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reference_id: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
```

---

## 6. API Endpoint Design

### 6.1 Customer Endpoints
1. `GET /api/v1/orders/{order_id}/pickup`
   - Returns pickup status, inspected items, driver notes, and approval requirements.
2. `POST /api/v1/orders/{order_id}/pickup/approve`
   - Customer accepts verified pickup details.
   - Sets `OrderPickup.status = APPROVED`, `approved_at = now()`.
   - Creates `Payment` record in `PENDING` status and initiates payment intent.
   - Returns payment details and checkout client token.
3. `POST /api/v1/orders/{order_id}/pickup/reject`
   - Body: `{"reason": "Discrepancy in shirt count"}`.
   - Sets `OrderPickup.status = REJECTED`.
4. `GET /api/v1/orders/{order_id}/payment`
   - Returns authoritative payment breakdown (`amount`, `gateway_fee`, `gateway_tax`, `ttc_commission`, `status`, `due_date`).
5. `POST /api/v1/orders/{order_id}/payment/pay`
   - Process/retry payment. On success: `Payment.status = SUCCEEDED`, `paid_at = now()`.

### 6.2 Seller Endpoints
1. `POST /api/v1/seller/orders/{order_id}/pickup/submit-details`
   - Seller submits physical inspection items, weights, and driver notes.
   - Order must be in `CONFIRMED`.
   - Sets `OrderPickup.status = DETAILS_SUBMITTED`.
2. `POST /api/v1/seller/orders/{order_id}/pickup/complete`
   - Attempts to finalize pickup and transition order to `IN_PROGRESS`.
   - **Enforces failure mode guard**:
     - If `payment_required_before_pickup == True`: requires `Payment.status == SUCCEEDED`. Else raises `409 Conflict: PAYMENT_REQUIRED_BEFORE_PICKUP`.
     - If `outstanding_receivable_allowed == True`: allows transition even if payment failed; sets `Payment.status = OUTSTANDING` with deadline.
3. `GET /api/v1/seller/settlements`
   - List settlements, cooling balances, and upcoming Monday payouts.
4. `GET /api/v1/seller/settlements/{settlement_id}`
   - Detailed settlement transfer report with constituent payments.

### 6.3 Platform Admin Endpoints
1. `POST /api/v1/admin/settlements/process-weekly`
   - Batch processor for Monday settlements.
   - Parameter: `target_date: date` (defaults to current date, validates `weekday() == 0`).
   - Gathers all eligible payments (`paid_at + 15 days <= target_date`), creates `SellerSettlement` records, and updates payments.

---

## 7. Migration & Rollout Strategy

1. **Alembic Migration (`migrations/versions/xxxx_phase7_commercial_payment_settlement.py`)**:
   - `op.create_table('order_pickups', ...)`
   - `op.create_table('seller_commercial_configs', ...)`
   - `op.create_table('seller_settlements', ...)`
   - `op.create_table('payments', ...)`
   - `op.create_table('refunds', ...)`
   - `op.create_table('seller_billing_invoices', ...)`
   - `op.add_column('orders', sa.Column('reselected_from_order_id', sa.Uuid(), sa.ForeignKey('orders.id', ondelete='SET NULL'), nullable=True))`
2. **Zero Breaking Changes**:
   - Existing order creation (`POST /api/v1/orders`) continues to function identically without breaking existing Phase 7 test suites.
   - `OrderStatus` enum values remain unmodified.
3. **Database Seeding**:
   - Ensure `SellerCommercialConfiguration` is automatically provisioned for every new seller with sensible platform defaults (`marketplace_gateway='TTC_GATEWAY'`, `commercial_model='COMMISSION'`, `commission_rate_percent=10.00`, `payment_required_before_pickup=True`).

---

## 8. Verification Strategy & Test Matrix

| Test Suite | Scenario | Expected Behavior |
|---|---|---|
| `test_payment_timing.py` | Order created via `POST /api/v1/orders` | Order in `PENDING`. No `Payment` record created. No charge made. |
| `test_payment_timing.py` | Seller confirms order -> submits pickup details | Pickup in `DETAILS_SUBMITTED`. Order in `CONFIRMED`. No payment requested yet. |
| `test_payment_timing.py` | Customer approves pickup details | Pickup in `APPROVED`. `Payment` created in `PENDING`. Payment requested. |
| `test_payment_failures.py` | Payment fails under Mode 1 (`payment_required_before_pickup=True`) | `Payment.status = FAILED`. Calling `/pickup/complete` fails with `409 Conflict`. Order remains in `CONFIRMED`. |
| `test_payment_failures.py` | Payment fails under Mode 2 (`outstanding_receivable_allowed=True`) | `Payment.status = OUTSTANDING`. Calling `/pickup/complete` succeeds. Order transitions to `IN_PROGRESS`. |
| `test_gateway_fees.py` | Payment processed through `TTC_GATEWAY` | Separate values recorded for `gateway_fee`, `gateway_tax`, `ttc_commission`, `ttc_commission_tax`. |
| `test_gateway_fees.py` | Partial refund processed | `refunded_amount` updated, `retained_amount` decreased, `ttc_commission` recalculated proportionally. |
| `test_settlement_cooling.py` | Payment on Day 0 under `TTC_GATEWAY` | On Day 10, payment is in cooling hold. Weekly settlement excludes it. |
| `test_settlement_cooling.py` | On Day 16 (next Monday) | Payment is eligible. Settlement batch generates `SellerSettlement` with exact net payout. |
| `test_settlement_seller_gateway.py` | Payment under `SELLER_GATEWAY` | Payment marked `SUCCEEDED`. No cooling hold. No `SellerSettlement` record created. Commission accrued for monthly invoice. |

---

## 9. Conclusion

The separation of the physical order lifecycle (`OrderStatus`) from the payment lifecycle (`PaymentStatus`) and pickup inspection (`OrderPickup`) delivers a clean, resilient, and enterprise-grade architecture. By anchoring payment requests to post-pickup customer approvals, supporting configurable failure modes, and implementing deterministic 15-day/Monday settlement cycles, Phase 7 establishes a solid commercial foundation for TheTextileCare platform.
