# Handoff Report: R2 (Commercial Models & Billing) and R4 (Seller Restrictions & Marketplace Re-selection)

**Agent**: `explorer_survey_phase7_3`  
**Working Directory**: `/workspaces/TheTextileCare/.agents/explorer_survey_phase7_3`  
**Date**: 2026-09-19  
**Type**: Hard Handoff (Investigation & Survey Complete)  

---

## 1. Observation

1. **Commercial Model Definitions**:
   - In `/workspaces/TheTextileCare/backend/app/models/commercial.py`:
     - Lines 14-16:
       ```python
       class SellerCommercialModel(str, Enum):
           COMMISSION = "COMMISSION"
           SUBSCRIPTION = "SUBSCRIPTION"
       ```
     - Lines 18-23:
       ```python
       class SellerRestrictionLevel(str, Enum):
           NONE = "NONE"
           WARNING = "WARNING"
           MARKETPLACE_RESTRICTED = "MARKETPLACE_RESTRICTED"
           WHITE_LABEL_RESTRICTED = "WHITE_LABEL_RESTRICTED"
           FULL_SUSPENSION = "FULL_SUSPENSION"
       ```
     - Lines 25-45: `SellerCommercialConfiguration` defines `seller_id`, `commercial_model`, `commission_rate_percent`, `subscription_fee`, `restriction_level`.
2. **Monthly Billing Invoices**:
   - In `/workspaces/TheTextileCare/backend/app/models/billing.py`:
     - Lines 10-14: `InvoiceStatus` has `PENDING`, `PAID`, `OVERDUE`, `CANCELLED`.
     - Lines 16-40: `SellerBillingInvoice` defines `id`, `seller_id`, `tenant_id`, `invoice_month`, `due_date`, `status`, `currency`, `subtotal`, `tax_total`, `penalty_total`, `total_amount`, `paid_at`.
3. **Payments & Retained Amount Model**:
   - In `/workspaces/TheTextileCare/backend/app/models/payment.py`:
     - Lines 10-17: `PaymentStatus` has `PENDING`, `SUCCEEDED`, `FAILED`, `OUTSTANDING`, `REFUNDED`, `PARTIALLY_REFUNDED`.
     - Lines 40-45:
       ```python
       ttc_commission: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
       ttc_commission_tax: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
       refunded_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
       retained_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
       ```
4. **Order Linking via `reselected_from_order_id`**:
   - In `/workspaces/TheTextileCare/backend/app/models/order.py`:
     - Lines 154-156:
       ```python
       reselected_from_order_id: Mapped[uuid.UUID | None] = mapped_column(
           ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True
       )
       ```
5. **Marketplace Discovery Filtering**:
   - In `/workspaces/TheTextileCare/backend/app/repositories/marketplace.py`:
     - Lines 25-28:
       ```python
       stmt = select(Seller).where(
           Seller.marketplace_status == 'PUBLISHED',
           Seller.status == 'ACTIVE'
       )
       ```
     - Currently filters on `marketplace_status == 'PUBLISHED'`, without an explicit join on `SellerCommercialConfiguration.restriction_level`.
6. **Order Cancellation & Status Invariants**:
   - In `/workspaces/TheTextileCare/backend/app/models/order.py`:
     - Lines 45-54: `OrderStatus` enum consists of `DRAFT`, `PENDING`, `CONFIRMED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`.
     - Lines 57-64: `ALLOWED_TRANSITIONS` permits `PENDING` $\to$ `CANCELLED` and `CONFIRMED` $\to$ `CANCELLED`.
7. **Database Migration State**:
   - Current Alembic head is `backend/migrations/versions/a1b2c3d4e5f6_phase7_order_foundation.py`.
   - The tables `seller_commercial_configs`, `seller_billing_invoices`, `seller_settlements`, `payments`, `refunds`, and the column `orders.reselected_from_order_id` are not yet included in any migration.

---

## 2. Logic Chain

1. **Commercial Model Exclusivity (Observation 1 $\to$ Design Conclusion)**:
   - Observation 1 defines `SellerCommercialModel` as either `COMMISSION` or `SUBSCRIPTION`.
   - Under Model 1 (`COMMISSION`), platform revenue is a percentage cut of the customer payment. Observation 3 shows `retained_amount = amount - refunded_amount`, which is the exact legal and commercial base for computing commission: refunds deduct directly from retained transaction value, making commission zero on full refunds and proportionally reduced on partial refunds. In Model 1, subscription fee is 0.00.
   - Under Model 2 (`SUBSCRIPTION`), the seller pays a flat recurring subscription fee (`subscription_fee`) per monthly cycle, and commission rate on orders is 0.00%.
   - Thus, mutual exclusivity is enforced by ensuring `commission_rate_percent > 0, subscription_fee = 0` for Model 1, and `subscription_fee > 0, commission_rate_percent = 0` for Model 2.

2. **Monthly Billing & Daily Late Penalties (Observations 2 & 1 $\to$ Design Conclusion)**:
   - Monthly billing cycles generate a `SellerBillingInvoice` for the prior calendar month.
   - Idempotency is established by adding a unique constraint `(seller_id, invoice_month)`.
   - Due date is `period_end + invoice_due_days` (default 15 days).
   - If unpaid past `due_date`, the invoice status transitions to `OVERDUE`.
   - Late penalty is deterministically calculated as:
     $$\text{penalty\_total} = \text{round\_half\_up}((\text{subtotal} + \text{tax\_total}) \times \text{daily\_penalty\_rate} \times \text{days\_overdue}, 2)$$
   - This formula is completely idempotent upon re-evaluation throughout the day.

3. **Overdue Enforcement & Automated Cancellation (Observations 1, 5, 6 $\to$ Design Conclusion)**:
   - When days overdue exceed `overdue_restriction_days` (e.g. 7 days), restriction level transitions to `MARKETPLACE_RESTRICTED`.
   - Observation 5 shows marketplace discovery queries check `Seller.marketplace_status`. Enforcing restrictions requires either synchronizing `Seller.marketplace_status = 'SUSPENDED'` or querying `SellerCommercialConfiguration.restriction_level not in ('MARKETPLACE_RESTRICTED', 'FULL_SUSPENSION')`.
   - Any order for the restricted seller currently in `OrderStatus.PENDING` must be transitioned to `OrderStatus.CANCELLED` with `cancellation_reason = "SELLER_RESTRICTED"`.
   - In accordance with Observation 6, orders already in `CONFIRMED` or `IN_PROGRESS` remain unaffected to avoid disrupting ongoing garment care.

4. **Zero-Refund Invariant & Customer Seller Re-selection (Observations 3, 4, 6 $\to$ Design Conclusion)**:
   - Under R1, payment is only captured upon customer approval of pickup details (which occurs after `CONFIRMED`).
   - At `PENDING` status, no customer payment has been charged (`Payment` status is `PENDING` or non-existent, collected balance is $0.00$).
   - Therefore, auto-cancelling `PENDING` orders with `SELLER_RESTRICTED` requires no gateway refund or ledger reversal.
   - The customer can then re-select an alternative seller via `POST /api/v1/orders/{order_id}/reselect`.
   - The new order sets `new_order.reselected_from_order_id = original_order.id` (Observation 4).
   - To ensure idempotency and prevent duplicate re-selections, the backend checks that no existing order has `reselected_from_order_id == original_order.id`.
   - The new order executes fresh deterministic pricing via Phase 5 `PricingService.calculate` against the new seller's catalog, creating fresh snapshots and a new order number.

5. **Separation of Concerns & Tenant Isolation (Observations 1, 2, 3, 6 $\to$ Design Conclusion)**:
   - In accordance with R5, `OrderStatus` is strictly operational (`PENDING`, `CONFIRMED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`) and is never overloaded with payment states.
   - Financial statuses reside in `PaymentStatus` and `InvoiceStatus`.
   - Compliance statuses reside in `SellerRestrictionLevel`.
   - All commercial and billing queries enforce `tenant_id` boundaries via `TenantContext`.

---

## 3. Caveats

1. **Alembic Migration Pending**: While models exist in code, no migration has been created to create the tables in PostgreSQL. The implementation team must create an Alembic migration following `a1b2c3d4e5f6_phase7_order_foundation.py`.
2. **Scheduled Job Infrastructure**: The project uses FastAPI and PostgreSQL without a separate Celery/Redis queue for jobs. Automated monthly invoice generation and daily penalty evaluations should be designed as idempotent service methods callable via admin CLI commands or scheduled cron endpoints.
3. **Gateway Settlement Pairing**: R2 defines the invoicing of commissions/subscriptions, while R3 defines the settlement of collected funds for TTC Gateway. For TTC Gateway sellers on Model 1, platforms can either deduct commission directly during settlement payout or include it in the monthly invoice. The survey report documents how both approaches align.

---

## 4. Conclusion

1. The architectural foundation for R2 and R4 is structurally sound and directly builds upon Phase 5 (Pricing Engine) and Phase 6 (Marketplace & Customer).
2. The core data models (`SellerCommercialConfiguration`, `SellerBillingInvoice`, `Payment`, `Refund`) and the `reselected_from_order_id` attribute provide a cohesive schema basis.
3. An Alembic migration must be added to materialize these entities in PostgreSQL.
4. Services and API endpoints must be implemented for:
   - Commercial configuration management (`CommercialService`)
   - Monthly billing generation and daily penalty calculations (`BillingService`)
   - Seller restriction enforcement and bulk cancellation of `PENDING` orders (`OrderService`)
   - Customer seller re-selection endpoint `POST /api/v1/orders/{order_id}/reselect` (`OrderService`)
5. Detailed specifications and contract designs are fully detailed in `/workspaces/TheTextileCare/.agents/explorer_survey_phase7_3/report.md`.

---

## 5. Verification Method

To independently verify the findings in this report:

1. **Inspect Draft Models and Code Structure**:
   ```bash
   view_file AbsolutePath="/workspaces/TheTextileCare/backend/app/models/commercial.py"
   view_file AbsolutePath="/workspaces/TheTextileCare/backend/app/models/billing.py"
   view_file AbsolutePath="/workspaces/TheTextileCare/backend/app/models/payment.py"
   view_file AbsolutePath="/workspaces/TheTextileCare/backend/app/models/order.py" StartLine=150 EndLine=160
   ```
2. **Verify Migration Status**:
   ```bash
   find_by_name SearchDirectory="/workspaces/TheTextileCare/backend/migrations/versions" Pattern="*.py"
   ```
   Confirms head is `a1b2c3d4e5f6_phase7_order_foundation.py` and commercial/billing tables are not yet migrated.
3. **Verify Order Status Separation**:
   ```bash
   grep_search Query="class OrderStatus" SearchPath="/workspaces/TheTextileCare/backend/app/models/order.py"
   ```
   Confirms `OrderStatus` only contains operational states (`DRAFT`, `PENDING`, `CONFIRMED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`).
4. **Invalidation Conditions**:
   - The analysis would be invalidated if customer payments were captured at order creation rather than post-pickup approval (which would break the zero-refund invariant for re-selection).
   - The analysis would be invalidated if commercial models were allowed to combine both subscription fees and percentage commissions simultaneously without mutual exclusivity.
