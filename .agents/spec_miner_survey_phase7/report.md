# Comprehensive Survey & Specification Mining Report: Phase 7 Grounding

**Author**: `spec_miner_survey_phase7`  
**Date**: 2026-09-19  
**Repository**: `/workspaces/TheTextileCare`  
**Target Domain**: Commercial Billing, Payment Timing, Settlement, Seller Restrictions, and Order Foundation Integration (Phase 7)

---

## 1. Executive Summary

This report documents the architectural baseline and authoritative specifications of **The Textile Care (TTC)** platform to ground the implementation of Phase 7 (Commercial Billing, Payment Timing, Settlement, and Seller Restrictions). 

The platform is structured as a **modular monolith** built with:
- **Backend**: FastAPI, SQLAlchemy 2.0 (mapped columns, declarative 2.0 style), Pydantic v2, PostgreSQL (psycopg driver), and Alembic.
- **Frontend / Monorepo Apps**: Turborepo, pnpm workspaces, Next.js applications (`seller-web`, `marketplace-web`, `admin-web`, mobile stubs).
- **Shared Packages**: `packages/types` (TypeScript interfaces), `packages/api-client`, `packages/auth`, `packages/tenant`, `packages/config`, `packages/branding`, `packages/ui`.

Phase 7 builds directly on top of the newly implemented **Order Foundation** (git commit `671cf79` / `2074847`), **Customer & Marketplace Foundation** (Phase 6), **Pricing Engine Foundation** (Phase 5), **Catalog Services** (Phase 4), **Customization Engine** (Phase 3), **Seller Platform** (Phase 2), and **Tenancy/Identity** (Phase 1).

---

## 2. Backend Architecture & Monorepo Layout

### 2.1 Workspace Structure
```
/workspaces/TheTextileCare/
├── apps/
│   ├── admin-web/
│   ├── driver-mobile/
│   ├── marketplace-mobile/
│   ├── marketplace-web/
│   ├── seller-mobile/
│   └── seller-web/
├── backend/
│   ├── alembic.ini
│   ├── pyproject.toml
│   ├── migrations/
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── api/
│   │   │   ├── router.py
│   │   │   └── v1/
│   │   │       ├── audit.py, auth.py, health.py, memberships.py, roles.py, tenants.py
│   │   │       ├── sellers.py, configuration.py, catalog.py, pricing.py, customer.py
│   │   │       ├── marketplace.py, orders.py
│   │   ├── core/
│   │   │   ├── exceptions/ (base.py: ApiError)
│   │   │   ├── middleware/ (security.py)
│   │   │   ├── permissions/ (constants.py: RoleName, PermissionName, DEFAULT_ROLE_PERMISSIONS)
│   │   │   ├── security/ (auth.py)
│   │   │   └── tenant/ (context.py, resolver.py)
│   │   ├── db.py (Base = DeclarativeBase, SessionLocal, engine, get_db)
│   │   ├── config.py (Settings, get_settings)
│   │   ├── dependencies.py (require_authenticated_user, require_tenant_context, require_permission)
│   │   ├── models/ (All SQLAlchemy models and enums)
│   │   ├── repositories/ (Data access layer)
│   │   ├── schemas/ (Pydantic models)
│   │   └── services/ (Business logic)
│   └── tests/ (api, unit, security, integration, e2e)
├── packages/
│   ├── api-client/
│   ├── auth/
│   ├── branding/
│   ├── config/
│   ├── tenant/
│   ├── types/ (TypeScript definitions: order.ts, pricing.ts, customer.ts, etc.)
│   └── ui/
```

### 2.2 API Routing Topology
FastAPI is mounted in `backend/app/main.py`. The top-level router `backend/app/api/router.py` groups v1 routes:
- `/api/v1/health` (`health_router`)
- `/api/v1/auth` (`auth_router`)
- `/api/v1/tenants` (`tenants_router`)
- `/api/v1/memberships` (`memberships_router`)
- `/api/v1/roles` (`roles_router`)
- `/api/v1/audit` (`audit_router`)
- `/api/v1/sellers` (`sellers_router`)
- `/api/v1/configuration` (`configuration_router`)
- `/api/v1/catalog` (`catalog_router`)
- `/api/v1/pricing` (`pricing_router`)
- `/api/v1/customer` (`customer_router`)
- `/api/v1/marketplace` (`marketplace_router`)
- `/api/v1/orders` (`orders_customer_router` — Customer order endpoints)
- `/api/v1/seller/orders` (`orders_seller_router` — Seller order endpoints)

---

## 3. Database Schemas, Models & Migration History

### 3.1 Migration Chain
Alembic migrations in `backend/migrations/versions/` form a strict linear chain:
1. `0001_phase1` (`0001_phase1_identity_and_tenancy.py`): Creates `users`, `tenants`, `roles`, `permissions`, `role_permissions`, `memberships`, `audit_events`.
2. `2010fc7ee67f` (`2010fc7ee67f_phase2_seller_platform.py`): Creates `sellers`, `seller_branches`, `seller_settings`, `seller_staff_profiles`.
3. `debba6592524` (`debba6592524_phase2_harden_seller_foundation.py`): Creates `business_hours`.
4. `275f700c133f` (`275f700c133f_phase3_customization_engine.py`): Creates `applications`, `configuration_definitions`, `application_modules`, `configuration_values`.
5. `ddf173e6fc96` (`ddf173e6fc96_phase4_catalog_services.py`): Creates `catalogs`, `catalog_categories`, `services`, `service_addons`, `service_branch_availability`, `service_items`.
6. `e7f1a2b3c4d5` (`e7f1a2b3c4d5_phase5_pricing_engine.py`): Creates `price_books`, `price_rules`.
7. `112e2205a754` (`112e2205a754_phase6_marketplace_and_customer.py`): Creates `customers`, `customer_addresses`, `customer_sellers`; adds `marketplace_status` to `sellers` and `is_marketplace_visible` to `seller_branches`.
8. `a1b2c3d4e5f6` (`a1b2c3d4e5f6_phase7_order_foundation.py`): Creates PostgreSQL sequence `order_number_seq`, tables `orders`, `order_items`, `order_item_addons`, `order_status_history`.

### 3.2 Current Phase 7 Working Tree Delta
The working tree contains drafted model files and relationships ready to be integrated and migrated in Phase 7 Part 2:
- `backend/app/models/commercial.py`:
  - `PaymentGatewayType` (`TTC_GATEWAY`, `SELLER_GATEWAY`)
  - `SellerCommercialModel` (`COMMISSION`, `SUBSCRIPTION`)
  - `SellerRestrictionLevel` (`NONE`, `WARNING`, `MARKETPLACE_RESTRICTED`, `WHITE_LABEL_RESTRICTED`, `FULL_SUSPENSION`)
  - `SellerCommercialConfiguration` (`seller_commercial_configs` table): 1:1 with `sellers`, stores gateway preferences, commercial model, commission rate percent, subscription fee, payment timing switches (`payment_required_before_pickup`, `outstanding_receivable_allowed`, `payment_deadline_days`), and current restriction level.
- `backend/app/models/payment.py`:
  - `PaymentStatus` (`PENDING`, `SUCCEEDED`, `FAILED`, `OUTSTANDING`, `REFUNDED`, `PARTIALLY_REFUNDED`)
  - `Payment` (`payments` table): 1:1 or 1:many with `orders.id`, stores gateway type, amount, gateway fee/tax, TTC commission and tax, refunded and retained amount, gateway transaction ID.
  - `Refund` (`refunds` table): FK to `payments.id`, tracking partial/full refund amount, fee reversals, and refund IDs.
- `backend/app/models/billing.py`:
  - `InvoiceStatus` (`PENDING`, `PAID`, `OVERDUE`, `CANCELLED`)
  - `SellerBillingInvoice` (`seller_billing_invoices` table): Monthly billing statement for a seller, tracking subtotal (commission or subscription), taxes, daily penalties, due date, status, payment timestamp.
  - `SettlementStatus` (`PENDING`, `PROCESSING`, `SETTLED`, `FAILED`)
  - `SellerSettlement` (`seller_settlements` table): Tracks disbursements to sellers for orders processed via `TTC_GATEWAY`. Holds funds for cooling period (15 days) and releases on Mondays.
- `backend/app/models/order.py`:
  - Field addition: `reselected_from_order_id: Mapped[uuid.UUID | None]` (FK `orders.id`, ondelete `SET NULL`), linking re-selected alternative seller orders back to original cancelled order.

*Migration Note*: A new Alembic migration (`phase7_commercial_and_settlement`) revising `a1b2c3d4e5f6` must be generated to officially create these 5 tables and the foreign key column on `orders`.

---

## 4. Deep Architectural Probing

### 4.1 Tenancy, Authentication & RBAC
- **Tenant Context**: Tenancy is multi-tenant with strict isolation. Each seller has its own `tenant_id` (1:1 with seller).
- **Resolver**: `TenantResolver` determines tenant from request headers (`X-Tenant-Id`) or user's primary membership.
- **Dependencies**:
  - `require_authenticated_user`: Authenticates user from `X-User-Id` (or session).
  - `require_tenant_context`: Guarantees tenant context and active membership.
  - `require_permission(permission_name)`: Enforces fine-grained RBAC per `PermissionName`.
- **Existing Permissions Matrix**:
  - Defined in `app/core/permissions/constants.py`.
  - Phase 7 order permissions currently defined: `order.read`, `order.manage`, `order.confirm`, `order.process`, `order.cancel`.
  - Commercial & Billing permissions to be added in Phase 7:
    - `commercial.read`, `commercial.manage`
    - `billing.read`, `billing.manage`
    - `settlement.read`, `settlement.manage`
    - `payment.read`, `payment.process`

### 4.2 Sellers & Marketplace Presence
- `Seller.status`: Lifecycle status (`PENDING`, `ACTIVE`, `SUSPENDED`).
- `Seller.marketplace_status`: Marketplace visibility (`DRAFT`, `PUBLISHED`).
- Orders can only be created against sellers where `marketplace_status == 'PUBLISHED'` and branches where `status == 'ACTIVE'` and `is_marketplace_visible == True`.
- `SellerCommercialConfiguration` controls whether the seller operates on commission (Model 1) or subscription (Model 2), their gateway setup, and restriction enforcement.

### 4.3 Customer Domain & Data Isolation
- `Customer`: Platform-level entity (1:1 with `User`).
- `CustomerAddress`: Stored securely and private to the customer. When an order is placed, an immutable snapshot (`customer_address_snapshot`) is embedded in JSON on the `Order` record to preserve historical fidelity even if the customer later edits or deletes the address.
- `CustomerSeller`: Explicit relationship created atomically on first order placement (`_ensure_customer_seller_link`).

### 4.4 Deterministic Pricing & Snapshot Architecture
- `PricingService.calculate(tenant_id, request)`: Deterministic calculation engine. Evaluates scoped price books with precedence (`BRANCH` overrides `SELLER` overrides `PLATFORM_DEFAULT`).
- `Order` snapshot fields:
  - `pricing_snapshot`: Complete breakdown (`currency`, `subtotal`, `total_surcharges`, `total_discounts`, `total_tax`, `grand_total`, item breakdowns).
  - `catalog_snapshot`: Service names, items, add-on names at creation time.
  - `customer_snapshot`: Name, email, phone at creation time.
  - `customer_address_snapshot`: Full delivery/pickup address at creation time.
- **Price Drift Protection**: `OrderCreateRequest.previewed_grand_total` is checked against current server calculation. If different, raises HTTP 409 `PRICE_CHANGED` preventing stale checkout prices.

### 4.5 Order Lifecycle & State Machine
- `OrderStatus` enum: `DRAFT`, `PENDING`, `CONFIRMED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`.
- `ALLOWED_TRANSITIONS`:
  - `DRAFT` → `PENDING`, `CANCELLED`
  - `PENDING` → `CONFIRMED`, `CANCELLED`
  - `CONFIRMED` → `IN_PROGRESS`, `CANCELLED`
  - `IN_PROGRESS` → `COMPLETED`
  - `COMPLETED` → none (terminal)
  - `CANCELLED` → none (terminal)
- **Role-based Cancellation Semantics**:
  - Customer can cancel from: `DRAFT`, `PENDING`, `CONFIRMED` (`CUSTOMER_CANCELLABLE_STATUSES`). Cancellation reason formatted as: `CUSTOMER_CANCELLED: <reason>`. Customer cannot cancel `IN_PROGRESS` or `COMPLETED`.
  - Seller can reject a `PENDING` order via `/reject` (`SELLER_REJECTED: <reason>`).
  - Seller can cancel a `CONFIRMED` order via `/cancel` (`SELLER_CANCELLED: <reason>`).
  - Neither customer nor seller can cancel `IN_PROGRESS` or `COMPLETED` orders.
- **Audit Logging**: Every status transition generates an entry in `order_status_history` and emits an `AuditEvent` (`ORDER_CONFIRMED`, `ORDER_STARTED`, `ORDER_COMPLETED`, `ORDER_CANCELLED`).

### 4.6 Pickups & Deliveries (Gap Analysis & Requirements)
- **Current State**: The existing database contains no dedicated `pickups` or `order_pickup_delivery` table. Address information is captured in `customer_address_snapshot` on `Order`.
- **Phase 7 Requirement R1**:
  - Payment is NOT requested at order creation. Order creation creates the order in `PENDING` state with no initial charge.
  - Actual pickup details (e.g. verified item counts, pickup execution) must be approved by the customer before payment is requested.
  - Two failure modes for payment:
    1. `payment_required_before_pickup`: If payment fails, pickup completion cannot proceed until resolved.
    2. `outstanding_receivable_allowed`: If payment fails, order can proceed with payment marked as `OUTSTANDING`.
  - Implementation requires clear payment request triggers tied to pickup detail approval.

### 4.7 Commercial Billing, Settlement & Seller Restrictions (Requirements R2–R4)
- **R2: Commercial Models & Monthly Billing**:
  - Model 1: Commission based on retained transaction amount (`retained_amount = amount - refunded_amount`). Gateway fees/taxes are recorded separately and not counted towards TTC commission.
  - Model 2: Fixed monthly subscription fee.
  - Monthly invoices generated for each seller (`SellerBillingInvoice`), with configurable billing dates, due dates, and daily late-payment penalties if overdue.
- **R3: Settlement Logic**:
  - `TTC_GATEWAY`: Settlement held for 15-day cooling period. Eligible funds are scheduled for payout on the following Monday.
  - `SELLER_GATEWAY`: Direct pass-through; TTC does not impose holds or create settlement payouts.
- **R4: Seller Restrictions & Re-Selection**:
  - Overdue invoices trigger restriction levels: `WARNING`, `MARKETPLACE_RESTRICTED`, `FULL_SUSPENSION`.
  - When restricted: Any `PENDING` marketplace orders for that seller must be automatically cancelled with cancellation reason `SELLER_RESTRICTED`.
  - Existing operational orders (`CONFIRMED`, `IN_PROGRESS`) remain active and unaffected.
  - Customers are notified and offered explicit marketplace re-selection to alternative sellers.
  - Re-selection generates a new order linked via `reselected_from_order_id`, carrying forward items/configuration without issuing a refund (since no payment was charged on the pending order).

---

## 5. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | Orders | Concurrency-Safe Order Number | DB sequence `order_number_seq` formatting `ORD-{YYYYMMDD}-{SEQ:06d}` | DB sequence `nextval` | Formatted order string | Sequence exhaustion handled by bigint | `backend/app/models/order.py`, `migrations/versions/a1b2c3d4e5f6` |
| 2 | Orders | Order Creation Pipeline | Recalculates catalog & pricing server-side, validates seller/branch, builds snapshots | `OrderCreateRequest` (seller, branch, items, address) | `OrderResponse` (status `PENDING`) | 404 seller/branch/address, 422 invalid catalog, 409 price changed | `backend/app/services/order.py:84` |
| 3 | Orders | Price Drift Protection | Validates customer previewed total against authoritative pricing engine | `previewed_grand_total` Decimal | Matches or raises error | 409 `PRICE_CHANGED` with current vs previewed amounts | `backend/app/services/order.py:130` |
| 4 | Orders | Order Idempotency | Customer-scoped idempotency key preventing duplicate orders | `Idempotency-Key` header | Returns existing order without reprocessing | 409 if key reuse with conflicting payload | `backend/app/services/order.py:108` |
| 5 | Orders | Customer Order Cancellation | Allows customer to cancel orders in eligible statuses (`DRAFT`, `PENDING`, `CONFIRMED`) | `order_id`, `OrderCancelRequest` | `OrderResponse` (`CANCELLED`, reason `CUSTOMER_CANCELLED: ...`) | 409 if in `IN_PROGRESS` or `COMPLETED`, 404 if not found/wrong customer | `backend/app/services/order.py:291` |
| 6 | Orders | Seller Order Rejection | Seller rejects `PENDING` orders only | `order_id`, `OrderCancelRequest` | `OrderResponse` (`CANCELLED`, reason `SELLER_REJECTED: ...`) | 409 if status is not `PENDING` | `backend/app/services/order.py:397` |
| 7 | Orders | Seller Order Cancellation | Seller cancels `CONFIRMED` orders | `order_id`, `OrderCancelRequest` | `OrderResponse` (`CANCELLED`, reason `SELLER_CANCELLED: ...`) | 409 if status not in `CONFIRMED` | `backend/app/services/order.py:415` |
| 8 | Orders | Seller Order Confirmation | Transitions `PENDING` order to `CONFIRMED` | `order_id`, `OrderStatusTransitionRequest` | `OrderResponse` (`CONFIRMED`, `confirmed_at` timestamp) | 409 if not `PENDING`, 404 if not seller's order | `backend/app/services/order.py:363` |
| 9 | Orders | Seller Order Processing | Transitions `CONFIRMED` to `IN_PROGRESS` | `order_id`, `OrderStatusTransitionRequest` | `OrderResponse` (`IN_PROGRESS`) | 409 if not `CONFIRMED` | `backend/app/services/order.py:374` |
| 10 | Orders | Seller Order Completion | Transitions `IN_PROGRESS` to `COMPLETED` | `order_id`, `OrderStatusTransitionRequest` | `OrderResponse` (`COMPLETED`, `completed_at` timestamp) | 409 if not `IN_PROGRESS` | `backend/app/services/order.py:386` |
| 11 | Orders | Order Reselection Linkage | Links new order to an original cancelled order when customer re-selects seller | `reselected_from_order_id` (UUID FK) | Order linked to parent order | Foreign key constraint on orders.id | `backend/app/models/order.py:154` |
| 12 | Commercial | Commercial Configuration | Configures seller commercial model, commission rate, subscription, gateway assignments | `SellerCommercialConfiguration` | Commercial configuration entity | Uniqueness constraint on seller_id | `backend/app/models/commercial.py:25` |
| 13 | Commercial | Payment Timing Modes | Configures whether payment failure blocks pickup or is outstanding receivable | `payment_required_before_pickup`, `outstanding_receivable_allowed` | Boolean flags | Enforced during payment processing | `backend/app/models/commercial.py:38` |
| 14 | Commercial | Payment Status Lifecycle | Tracks payments separately from order lifecycle | `PaymentStatus` (`PENDING`, `SUCCEEDED`, `FAILED`, `OUTSTANDING`, `REFUNDED`, `PARTIALLY_REFUNDED`) | Status string | Operational status unaffected by payment status | `backend/app/models/payment.py:10` |
| 15 | Commercial | Separate Gateway Financials | Records gateway fees and taxes separately from platform commissions | `gateway_fee`, `gateway_tax`, `ttc_commission`, `ttc_commission_tax` | Numeric financial records | Numeric(10, 2) exact decimal validation | `backend/app/models/payment.py:35` |
| 16 | Commercial | Refund & Fee Tracking | Tracks refunds and reversed gateway fees against payments | `Refund` model, `refunded_amount`, `retained_amount` | Refund record, updated payment balances | Cannot refund more than payment amount | `backend/app/models/payment.py:52` |
| 17 | Billing | Monthly Billing Invoice | Monthly billing for commission, subscription fees, and daily late penalties | `SellerBillingInvoice` (`invoice_month`, `due_date`, amounts) | Invoice record with `InvoiceStatus` | Overdue status triggers restriction checks | `backend/app/models/billing.py:16` |
| 18 | Settlement | 15-Day Settlement Hold | Holds payout funds for 15 days, then releases on following Monday | `SellerSettlement` (`scheduled_for`, `processed_at`) | Settlement record with `SettlementStatus` | Blocked if gateway is `SELLER_GATEWAY` | `backend/app/models/billing.py:47` |
| 19 | Restrictions | Seller Restriction Levels | Restricts seller access upon overdue invoices (`WARNING`, `MARKETPLACE_RESTRICTED`, `FULL_SUSPENSION`) | `SellerRestrictionLevel` | Restriction level applied to seller config | `PENDING` orders auto-cancelled with `SELLER_RESTRICTED` | `backend/app/models/commercial.py:18` |
| 20 | Auditing | Lifecycle Event Logging | Centralized append-only audit trail for orders, pricing, and tenancy | `AuditService.log_event` | `AuditEvent` record in `audit_events` | Non-blocking or transactionally committed | `backend/app/services/audit.py` |

---

## 6. Edge Cases & Observed Behaviors

| # | Feature | Input | Observed Behavior |
|---|---------|-------|-------------------|
| 1 | Order Creation | Client sends `previewed_grand_total = 100.00` but server price rule computes `120.00` | Server rejects with HTTP 409 `PRICE_CHANGED` and returns both current and previewed totals in error payload. |
| 2 | Idempotency | Customer posts same `Idempotency-Key` twice with identical payload | Second request returns HTTP 200/201 with the exact existing order without inserting duplicates or double billing. |
| 3 | Customer Cancellation | Customer attempts to cancel order with status `IN_PROGRESS` or `COMPLETED` | Server returns HTTP 409 `INVALID_ORDER_STATUS_TRANSITION` ("Order in status '...' cannot be cancelled by the customer"). |
| 4 | Seller Cancellation | Seller attempts to cancel order with status `PENDING` via `/cancel` endpoint | Server returns HTTP 409 `INVALID_ORDER_STATUS_TRANSITION`. Seller must use explicit `/reject` endpoint for `PENDING` orders. |
| 5 | Seller Rejection | Seller attempts to reject order that has already been `CONFIRMED` | Server returns HTTP 409 `INVALID_ORDER_STATUS_TRANSITION` ("Only PENDING orders can be rejected"). |
| 6 | Cross-Tenant Seller Order Query | Seller A attempts to view or mutate Seller B's order via `/api/v1/seller/orders/{order_id}` | Server returns HTTP 404 `ORDER_NOT_FOUND`, maintaining complete seller data isolation. |
| 7 | Cross-Customer Order Query | Customer A attempts to view or cancel Customer B's order | Server returns HTTP 404 `ORDER_NOT_FOUND`, preventing cross-customer access. |
| 8 | Inactive Branch / Unlisted Seller | Order create request references a branch with `is_marketplace_visible == False` or seller with `marketplace_status == 'DRAFT'` | Server rejects with HTTP 404 `INVALID_BRANCH` or `INVALID_SELLER`. |
| 9 | Pytest Database Reset Concurrency | Two test processes or background tasks invoke `conftest.py:reset_database` concurrently | PostgreSQL table drop/create causes composite type collisions in `pg_type` (`duplicate key value violates unique constraint "pg_type_typname_nsp_index"`). Tests must run sequentially. |
| 10 | Seller Restriction Auto-Cancel | Seller restriction escalates to `MARKETPLACE_RESTRICTED` while seller has `PENDING` orders and `CONFIRMED` orders | `PENDING` orders are cancelled with reason `SELLER_RESTRICTED`; `CONFIRMED` and `IN_PROGRESS` orders remain active and operational. |
| 11 | Reselection No-Refund | Customer reselects an alternative seller after order was cancelled due to `SELLER_RESTRICTED` | New order created linked to old order; no refund issued because `PENDING` order had not yet requested or collected payment. |
| 12 | Payment Timing vs Order Creation | Customer places new order on marketplace | Order is placed with `status = PENDING`. No charge is created on the payment gateway at this point. |

---

## 7. Test Infrastructure & Verification Patterns

### 7.1 Test Setup & Conftest Fixtures
- Test runner: `pytest` (configured in `backend/pyproject.toml`).
- Auto-use fixture: `tests/conftest.py:reset_database()`:
  - Invokes `Base.metadata.drop_all(bind=engine)`.
  - Invokes `Base.metadata.create_all(bind=engine)`.
  - Seeds default roles and permissions via `RoleService(db).seed_defaults()`.
- Helper fixtures in `tests/conftest.py` & `tests/api/test_orders.py`:
  - `_create_user(email)`
  - `_create_tenant(name)`
  - `_make_seller_world(tenant_id, user_id)` (creates seller, branch, catalog, service, items, add-ons, pricing)
  - `make_auth_headers(user, tenant)` / `_customer_headers` / `_seller_headers`

### 7.2 Existing Test Suite Health
- **Orders API Suite** (`tests/api/test_orders.py`): 28 tests covering order creation, multi-item pricing snapshots, idempotency, price drift detection, tenant isolation, customer isolation, status transitions, snapshot immutability, and decimal precision. **All 28 tests pass.**
- **Cancellation Suite** (`tests/api/test_cancellation.py`): 3 tests verifying customer and seller cancellation semantics and boundary restrictions. **All 3 tests pass.**
- **Rejection Suite** (`tests/api/test_rejection.py`): 3 tests verifying seller rejection of pending orders and prevention of rejection on confirmed orders. **All 3 tests pass.**
- **Health & Config Suites** (`tests/api/test_health.py`, `tests/unit/test_config.py`): **All pass.**

### 7.3 Execution Guideline
Because `tests/conftest.py` resets the shared PostgreSQL database tables between tests, tests must be run **sequentially** (avoiding `-n` parallel workers without database per-worker isolation) to prevent DDL catalog collisions.

---

## 8. Implementation Plan & Architectural Constraints for Phase 7

1. **Alembic Migration**:
   - Create migration `b2c3d4e5f6a7_phase7_commercial_billing_settlement.py` revising `a1b2c3d4e5f6`.
   - Tables to create: `seller_commercial_configs`, `payments`, `refunds`, `seller_billing_invoices`, `seller_settlements`.
   - Alter `orders` table: Add `reselected_from_order_id` nullable foreign key to `orders.id`.
2. **Services & Repositories**:
   - `CommercialService`: Manage seller commercial configurations, commission calculation, and restriction level updates.
   - `PaymentService`: Handle payment requests triggered after pickup detail approval, manage dual gateway routing (`TTC_GATEWAY` vs `SELLER_GATEWAY`), process refunds, and record separate gateway fees/taxes.
   - `BillingService`: Monthly invoice generation, due date enforcement, late penalty calculations.
   - `SettlementService`: 15-day hold logic and Monday payout scheduling for TTC gateway transactions.
   - `SellerRestrictionService`: Check overdue invoices, transition restriction levels, automatically cancel `PENDING` marketplace orders with reason `SELLER_RESTRICTED`, and facilitate re-selection creating linked orders without refund.
3. **API Endpoints**:
   - Commercial config: `/api/v1/seller/commercial`
   - Payments & Pickup Approval: `/api/v1/orders/{order_id}/pickup/approve`, `/api/v1/orders/{order_id}/payment`
   - Invoices: `/api/v1/seller/billing/invoices`, `/api/v1/platform/billing/invoices`
   - Settlements: `/api/v1/seller/settlements`
   - Restrictions & Reselection: `/api/v1/orders/{order_id}/reselect`
4. **Permissions & Security**:
   - Add new permissions to `PermissionName` and map them in `DEFAULT_ROLE_PERMISSIONS`.
   - Strictly enforce tenant and seller isolation across all financial and restriction endpoints.
   - Ensure all monetary math uses `Decimal` and calculations are deterministic.
