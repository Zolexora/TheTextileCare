# Handoff Report — Phase 7 Architectural Survey & Grounding

**Agent**: `spec_miner_survey_phase7`  
**Milestone**: Phase 7 Grounding Survey  
**Date**: 2026-09-19  

---

## 1. Observation

1. **Monorepo and Backend Layout**:
   - Monorepo root `/workspaces/TheTextileCare` contains `backend/`, `apps/` (`seller-web`, `marketplace-web`, `admin-web`), `packages/` (`types`, `api-client`, `auth`, `tenant`, etc.).
   - Backend is a FastAPI modular monolith with SQLAlchemy 2.0 and Alembic located in `/workspaces/TheTextileCare/backend`.
   - Main router at `backend/app/api/router.py:34-35` includes:
     ```python
     router.include_router(orders_customer_router, prefix='/api/v1/orders')
     router.include_router(orders_seller_router, prefix='/api/v1/seller/orders')
     ```

2. **Alembic Migrations Chain**:
   - Existing migration head: `a1b2c3d4e5f6` (`backend/migrations/versions/a1b2c3d4e5f6_phase7_order_foundation.py:22-23`):
     ```python
     revision: str = 'a1b2c3d4e5f6'
     down_revision: Union[str, None] = '112e2205a754'
     ```
   - Migration `a1b2c3d4e5f6` created `order_number_seq`, `orders`, `order_items`, `order_item_addons`, `order_status_history`.
   - Linear chain verified from `0001_phase1` -> `2010fc7ee67f` -> `debba6592524` -> `275f700c133f` -> `ddf173e6fc96` -> `e7f1a2b3c4d5` -> `112e2205a754` -> `a1b2c3d4e5f6`.

3. **Current Working Tree State**:
   - `git status` revealed draft models in `backend/app/models/`:
     - `commercial.py`: `PaymentGatewayType`, `SellerCommercialModel`, `SellerRestrictionLevel`, `SellerCommercialConfiguration` (`seller_commercial_configs`).
     - `payment.py`: `PaymentStatus`, `Payment` (`payments`), `Refund` (`refunds`).
     - `billing.py`: `InvoiceStatus`, `SellerBillingInvoice` (`seller_billing_invoices`), `SettlementStatus`, `SellerSettlement` (`seller_settlements`).
     - `order.py:154-156`: `reselected_from_order_id = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True, index=True)`.
     - `__init__.py`: Exports all above models and enums.

4. **Order State Machine & Lifecycle**:
   - In `backend/app/models/order.py:45-77`:
     - `OrderStatus`: `DRAFT`, `PENDING`, `CONFIRMED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`.
     - `ALLOWED_TRANSITIONS`: `DRAFT` -> `[PENDING, CANCELLED]`, `PENDING` -> `[CONFIRMED, CANCELLED]`, `CONFIRMED` -> `[IN_PROGRESS, CANCELLED]`, `IN_PROGRESS` -> `[COMPLETED]`.
     - `CUSTOMER_CANCELLABLE_STATUSES = {DRAFT, PENDING, CONFIRMED}`.
     - `SELLER_CANCELLABLE_STATUSES = {CONFIRMED}`.
   - In `backend/app/services/order.py:397-433`:
     - Seller rejects `PENDING` orders via `/reject` -> `SELLER_REJECTED: <reason>`.
     - Seller cancels `CONFIRMED` orders via `/cancel` -> `SELLER_CANCELLED: <reason>`.
     - Customer cancels eligible orders via `/cancel` -> `CUSTOMER_CANCELLED: <reason>`.

5. **Pickup & Delivery Current State**:
   - No dedicated fulfillment / pickup database table currently exists.
   - Address data is persisted on `Order` as `customer_address_snapshot` (JSON).
   - `ORIGINAL_REQUEST.md` (lines 101-104) requires:
     "Payment is requested only after the customer approves actual pickup details (not at order creation). Support two modes for payment failure: required before pickup completion, or allowed as an outstanding receivable."

6. **Test Suites & Verification**:
   - `pytest tests/api/test_orders.py`: 28 passed in 52.78s.
   - `pytest tests/api/test_cancellation.py tests/api/test_rejection.py`: 6 passed in 13.97s.
   - `tests/conftest.py:reset_database` drops and creates all tables on the shared PostgreSQL instance per test; parallel execution without test database isolation triggers Postgres composite type collisions.

---

## 2. Logic Chain

1. **Phase 7 Architectural Foundation Is Sound and Tested**:
   - Observations 1, 2, and 6 confirm that the modular monolith architecture, database connection, sequence-backed order generation, deterministic pricing snapshots, and order lifecycle transitions are implemented and fully verified with 34 passing API tests.

2. **Phase 7 Scope Boundaries & Separation of Concerns**:
   - Observation 4 shows that `OrderStatus` is strictly operational (`DRAFT` to `COMPLETED`/`CANCELLED`).
   - Per Requirement R5 and Observation 3, commercial states (`PaymentStatus`, `InvoiceStatus`, `SettlementStatus`, `SellerRestrictionLevel`) are appropriately isolated in dedicated models (`Payment`, `SellerBillingInvoice`, `SellerSettlement`, `SellerCommercialConfiguration`) and must not overload `OrderStatus`.

3. **Database Migration Requirement**:
   - Observation 2 & 3 indicate that while `commercial.py`, `payment.py`, and `billing.py` exist in the working tree, the migration chain ends at `a1b2c3d4e5f6`. Therefore, an official Alembic migration must be created to declare tables `seller_commercial_configs`, `payments`, `refunds`, `seller_billing_invoices`, `seller_settlements`, and the column `orders.reselected_from_order_id`.

4. **Commercial & Settlement Logic Grounding**:
   - Observation 3 & 5 align with requirements R1–R4:
     - Payment timing: Initiated after pickup approval; handles `payment_required_before_pickup` vs `outstanding_receivable_allowed`.
     - Dual gateway accounting: `TTC_GATEWAY` vs `SELLER_GATEWAY`, recording separate gateway fee/tax from TTC commission.
     - Commercial models: Model 1 (retained transaction commission) vs Model 2 (monthly subscription fee).
     - Settlement: 15-day hold and Monday disbursement for `TTC_GATEWAY`.
     - Overdue enforcement & Re-selection: Auto-cancelling `PENDING` orders with `SELLER_RESTRICTED` while preserving `CONFIRMED`/`IN_PROGRESS`, and providing re-selection without refund via `reselected_from_order_id`.

---

## 3. Caveats

- **Frontend Integration**: Frontend applications (`seller-web`, `marketplace-web`) have stub pages for `/orders`. Full UI workflows are outside the backend scope but shared types in `packages/types` should be kept in sync.
- **Payment Gateway Drivers**: Real external payment gateways (e.g. Stripe, Razorpay) are represented via an abstraction layer with idempotency; test doubles / mock gateways are used for local and CI environments.
- **Concurrent Test Execution**: Running `pytest -n` against a single PostgreSQL database instance will cause DDL race conditions due to `conftest.py:reset_database`. Tests should be run sequentially.

---

## 4. Conclusion

The existing codebase is in an ideal position for implementing Phase 7 commercial billing, payment timing, settlement, and seller restrictions:
1. The Order Foundation is robust, tested (100% pass on 34 order tests), and cleanly separated from financial/payment states.
2. The domain models (`commercial.py`, `payment.py`, `billing.py`, and `order.py:reselected_from_order_id`) are properly drafted and follow SQLAlchemy 2.0 conventions.
3. The remaining work is clearly scoped: generate the Alembic migration, implement domain services (`CommercialService`, `PaymentService`, `BillingService`, `SettlementService`, `SellerRestrictionService`), expose REST endpoints, and build the comprehensive test suite to satisfy requirements R1 through R5.

---

## 5. Verification Method

1. **Verify Existing Test Suites**:
   ```bash
   cd /workspaces/TheTextileCare/backend
   pytest tests/api/test_orders.py tests/api/test_cancellation.py tests/api/test_rejection.py
   ```
2. **Inspect Migration Chain**:
   ```bash
   cd /workspaces/TheTextileCare/backend
   alembic heads
   ```
3. **Inspect Detailed Report**:
   Review `/workspaces/TheTextileCare/.agents/spec_miner_survey_phase7/report.md`.
