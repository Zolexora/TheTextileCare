# Handoff Report — Survey Explorer 2 (R1 & R3)

**Agent:** `explorer_survey_phase7_2`  
**Working Directory:** `/workspaces/TheTextileCare/.agents/explorer_survey_phase7_2`  
**Handoff Type:** Hard (Survey Complete)  
**Deliverable:** `/workspaces/TheTextileCare/.agents/explorer_survey_phase7_2/report.md`  

---

## 1. Observation

Direct observations from codebase inspection:
1. **OrderStatus Model (`backend/app/models/order.py:45-64`)**:
   ```python
   class OrderStatus(str, enum.Enum):
       DRAFT = "DRAFT"
       PENDING = "PENDING"
       CONFIRMED = "CONFIRMED"
       IN_PROGRESS = "IN_PROGRESS"
       COMPLETED = "COMPLETED"
       CANCELLED = "CANCELLED"
   ```
   Allowed transitions are strictly linear and operational:
   `PENDING` -> `CONFIRMED` / `CANCELLED`; `CONFIRMED` -> `IN_PROGRESS` / `CANCELLED`; `IN_PROGRESS` -> `COMPLETED`.
2. **Order Creation Pipeline (`backend/app/services/order.py:84-268`)**:
   `OrderService.create_order()` validates customer, seller, branch, and catalog, computes authoritative totals via `PricingService.calculate()`, generates snapshots, and saves the order in `OrderStatus.PENDING`. No payment transaction is created or executed.
3. **Architectural Decisions (`docs/architecture/order-domain.md`, `phase-7-business-resolution.md`)**:
   Documents mandate that orders are historically immutable with respect to commercial definitions and state machines remain minimal and focused.
4. **Existing Commercial Configuration Model (`backend/app/models/commercial.py:10-45`)**:
   Contains `PaymentGatewayType` (`TTC_GATEWAY`, `SELLER_GATEWAY`) and `SellerCommercialConfiguration` with:
   - `payment_required_before_pickup: Mapped[bool] = mapped_column(Boolean, default=True)`
   - `outstanding_receivable_allowed: Mapped[bool] = mapped_column(Boolean, default=False)`
   - `payment_deadline_days: Mapped[int] = mapped_column(default=1)`
5. **Existing Payment and Settlement Models (`backend/app/models/payment.py`, `backend/app/models/billing.py`)**:
   `Payment` separates `gateway_fee`, `gateway_tax`, `ttc_commission`, `ttc_commission_tax`, `refunded_amount`, and `retained_amount`.
   `SellerSettlement` contains `seller_id`, `gateway_type`, `status`, `currency`, `amount`, `scheduled_for` (Date), and `processed_at`.
6. **Absence of Pickup Entity**:
   Grep search for `pickup` across `backend/` confirmed that no pickup domain model, pickup status enum, or pickup inspection table currently exists in the database.

---

## 2. Logic Chain

1. **Premise**: `ORIGINAL_REQUEST.md` (R1 & R5) explicitly dictates: "Do not overload the OrderStatus enum with payment states; keep operational and payment states separate" and "Payment is requested only after the customer approves actual pickup details (not at order creation)".
2. **Operational vs Financial Separation**: From Observation 1 & 3, `OrderStatus` tracks the physical garment lifecycle. Adding payment states (`PAID`, `FAILED`, `REFUNDED`) directly to `OrderStatus` would break existing transition invariants and multiply state complexity. Therefore, `PaymentStatus` (`PENDING`, `SUCCEEDED`, `FAILED`, `OUTSTANDING`, `REFUNDED`, `PARTIALLY_REFUNDED`) must reside exclusively on a separate `Payment` entity.
3. **Pickup Approval as Payment Trigger**: From Observation 2 & 6, because orders are created without charging, and physical inspection occurs upon garment collection, a new entity `OrderPickup` (`order_pickups`) is required. Its lifecycle (`SCHEDULED` -> `DETAILS_SUBMITTED` -> `APPROVED` / `REJECTED` -> `COMPLETED`) decouples the inspection workflow. Customer approval (`OrderPickup.status = APPROVED`) serves as the authoritative event triggering payment request.
4. **Dual Failure Modes**: From Observation 4, `SellerCommercialConfiguration` defines the operational behavior when payment fails:
   - If `payment_required_before_pickup == True`: The seller cannot mark pickup complete; operational order stays in `CONFIRMED` until payment succeeds.
   - If `outstanding_receivable_allowed == True`: Pickup completion is permitted; order moves to `IN_PROGRESS`, and `Payment.status` transitions to `OUTSTANDING` with `due_date = now + payment_deadline_days`.
5. **Gateway Routing & Settlement Rules**: From Observation 4 & 5, `TTC_GATEWAY` pools customer funds in TTC custody, requiring a 15-day cooling hold from `paid_at` to hedge against disputes, followed by weekly Monday payouts via `SellerSettlement`. Conversely, `SELLER_GATEWAY` routes funds directly to the seller; TTC holds no funds, enforces no cooling hold, and generates no settlement payouts (TTC commission is invoiced monthly via `SellerBillingInvoice`).
6. **Fee & Tax Accounting**: From Observation 5, third-party payment processor costs (`gateway_fee`, `gateway_tax`) are tracked independently from platform revenues (`ttc_commission`, `ttc_commission_tax`), allowing accurate retained-amount adjustments and commission recalculations upon partial or full refunds.

---

## 3. Caveats

1. **Cooling Period Baseline**: The 15-day cooling period calculation is anchored to `Payment.paid_at`. If future business rules prefer anchoring to `Order.completed_at` (fulfillment completion), the filter in `SettlementService` can be toggled without architectural rework.
2. **Seller Direct Gateway Integration**: For `SELLER_GATEWAY`, it is assumed the seller's direct processor webhooks will notify TTC to record payment completion for audit and monthly commission invoicing.
3. **Scope Discipline**: This investigation was strictly read-only; no source code or database migrations were modified.

---

## 4. Conclusion

R1 (Payment Abstraction & Timing) and R3 (Settlement Logic) have been fully designed and integrated against TheTextileCare architecture:
1. `OrderStatus` remains strictly operational; payment states reside on `Payment`.
2. Post-pickup inspection is encapsulated in `OrderPickup` (`order_pickups`). Customer approval is the sole trigger for payment requests.
3. Configurable failure modes (hard gate vs outstanding receivable) are mapped cleanly to `SellerCommercialConfiguration`.
4. Platform gateway (`TTC_GATEWAY`) enforces a deterministic 15-day cooling hold and Monday payouts; seller-owned gateways (`SELLER_GATEWAY`) bypass platform settlement.
5. Third-party gateway fees/taxes are cleanly separated from platform commissions and taxes.

Full specifications, schemas, state transition matrices, and API designs are documented in `/workspaces/TheTextileCare/.agents/explorer_survey_phase7_2/report.md`.

---

## 5. Verification Method

To verify the findings and proposed contracts independently:
1. **Inspect Models & Tables**:
   `python -c "import app.models; from app.db import Base; print(sorted(Base.metadata.tables.keys()))"`
2. **Inspect Existing Order State Transitions**:
   View `backend/app/models/order.py:57-64` and `backend/app/services/order.py:438-460` to verify that `OrderStatus` does not contain payment states.
3. **Review Architectural Report**:
   Inspect `/workspaces/TheTextileCare/.agents/explorer_survey_phase7_2/report.md` for complete data schemas, API specifications, and mathematical formulas.
4. **Invalidation Conditions**:
   - Any proposal to add `PAID`, `UNPAID`, or `REFUNDED` to `OrderStatus`.
   - Any payment transaction execution during `POST /api/v1/orders`.
   - Creating settlement transfers for `SELLER_GATEWAY` transactions.
