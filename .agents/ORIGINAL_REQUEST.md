# Original User Request

## 2026-09-18T08:44:02Z

Create a bash script (`start.sh`) to easily start the various applications within the monorepo workspace for local development (dev mode). This is a single self-contained task; keep it small and focused.

Working directory: /workspaces/TheTextileCare
Integrity mode: development

## Requirements

### R1. App Selection
The script must provide an interactive menu or accept arguments to allow the developer to choose which specific application(s) to start (e.g., `admin-web`, `marketplace-web`, `seller-web`, `backend`).

### R2. Concurrent Execution
When multiple apps are selected, the script must run them concurrently and stream their output, ensuring local development is seamless.

### R3. Tooling Integration
The script should utilize the workspace's existing package manager (`pnpm`) or build system (`turbo`) to execute the `dev` scripts of the selected apps.

## Acceptance Criteria

### Execution & Selection
- [ ] Running `./start.sh` (with no arguments or via menu) clearly shows how to select apps.
- [ ] Selecting a specific app successfully starts only that app's development server.

### Lifecycle & Output
- [ ] Multiple selected apps start concurrently.
- [ ] Stopping the script (e.g., with Ctrl+C) cleanly terminates all background processes started by the script.

## Follow-up — 2026-09-18T09:03:11Z

The user is waiting and has explicitly requested that you speed up the process. Please prioritize speed, wrap up your current testing or implementation phase, bypass excessive adversarial review cycles if it is already functional, and deliver the final `start.sh` script as quickly as possible.

## 2026-09-19T04:33:52Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: Full Team

Implement the **Pricing Engine Foundation** for TTC as a reusable, deterministic, tenant-isolated pricing domain, establishing "How much does it cost?" structurally isolated from the catalog ("What is being offered?").

Working directory: `/workspaces/TheTextileCare`
Integrity mode: development

## Requirements

### R1. Architectural Integrity
Preserve the existing modular monolith architecture (FastAPI, SQLAlchemy 2, Alembic, PostgreSQL). Maintain tenant isolation, existing authentication/RBAC, and configuration-driven structure. Do not introduce microservices, Kafka, EAV tables, or rewrite Phase 1-4 migrations. Create a new Alembic migration for Phase 5.

### R2. Core Pricing Model & Components
Implement `price_books` and `price_rules` entities referencing Phase 4 catalog entities without duplicating data. Support rule types: `FIXED`, `PER_ITEM`, `PER_UNIT`, `PER_WEIGHT`. Create a normalized pricing component breakdown (Base Price, Surcharge, Discount, Tax) using `Decimal` for all monetary calculations (no floating point).

### R3. Deterministic Calculation Service
Implement a deterministic pricing calculation algorithm that resolves precedence (Platform Default → Seller → Branch → Rule), enforces effective dates (`effective_from` / `effective_to`), applies surcharges/discounts/taxes, and returns a strict breakdown without persisting a customer order. Ensure robust tenant, seller, and branch validation. 

### R4. Security & Permissions
Enforce strict tenant isolation (relying exclusively on authenticated context, rejecting cross-tenant references). Prevent ID injection. Add granular Phase 5 permissions (e.g., `pricing.read`, `pricing.manage`) following the principle of least privilege. Emit lifecycle audit events via the existing `AuditService`.

### R5. Integration & APIs
Expose standard REST endpoints under `/api/v1/pricing/` for managing books, rules, and performing deterministic calculations. Export shared TypeScript types (e.g., `PriceBook`, `PricingCalculationResult`) in `packages/types`. Build a minimal pricing management foundation in `apps/seller-web` without duplicating calculation logic.

## Acceptance Criteria

### Security & Isolation
- [ ] Tenant A → Tenant B pricing mutations are explicitly denied (404/403).
- [ ] ID injection across all pricing entities is tested and protected.
- [ ] Privilege escalation is blocked; users with `VIEWER` role cannot mutate pricing.

### Deterministic Calculation
- [ ] Fixed, per-item, per-unit, and per-weight calculations return mathematically exact `Decimal` results.
- [ ] Subtotal + surcharges - discounts + tax = grand total (strictly validated, tested with rounding rules).
- [ ] Priority, effective dates, and branch overrides deterministically select the correct rules.
- [ ] Draft and inactive rules do not leak into active calculations.

### Architecture & Regression
- [ ] Pricing domain is strictly separated from Catalog (no price fields on catalog tables).
- [ ] No orders, checkout, cart, or payment logic is implemented (strictly Pricing Engine).
- [ ] All Phase 1, 2, 3, 4, and 5 tests pass successfully (`pytest`).
- [ ] A fresh database migration (`alembic upgrade head`) succeeds.
- [ ] `pnpm lint`, `pnpm typecheck`, and `pnpm build` pass across all monorepo packages.
- [ ] Comprehensive documentation (architecture, schema, security) is generated in `docs/`.
- [ ] Working tree is clean and committed exactly as: `feat(phase-5): implement pricing engine foundation`.

## 2026-09-19T17:49:20Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Requested team: Full team (multi-part project on an existing codebase)

Implement the commercial billing, payment timing, settlement, and seller restriction foundation for Phase 7 of the TTC (TheTextileCare) platform. 

Working directory: `/workspaces/TheTextileCare`
Integrity mode: development

## Requirements

### R1. Payment Abstraction & Timing
Payment is requested only after the customer approves actual pickup details (not at order creation). Support two modes for payment failure: required before pickup completion, or allowed as an outstanding receivable. Support two payment gateway scenarios: TTC Payment Gateway and Seller's own gateway. Gateway fees and taxes must be recorded separately from TTC commissions.

### R2. Commercial Models & Billing
Implement two mutually exclusive commercial models for marketplace sellers: Model 1 (Percentage Commission based on retained transaction amount) and Model 2 (Fixed Monthly Subscription). Create a monthly TTC billing system with configurable billing dates, payment deadlines, and daily late-payment penalties.

### R3. Settlement Logic
For the TTC Payment Gateway, implement a settlement model that holds funds for a 15-day cooling period and settles eligible amounts on Mondays. For seller-owned gateways, TTC does not impose holds or create settlement transfers.

### R4. Seller Restrictions & Marketplace Re-selection
Implement configurable overdue enforcement levels (e.g., WARNING, MARKETPLACE_RESTRICTED, FULL_SUSPENSION). If a seller becomes restricted, any `PENDING` marketplace orders must be automatically `CANCELLED` (reason: `SELLER_RESTRICTED`). Customers must then be given an explicit choice to re-select an alternative seller, generating a new order linked to the original. Existing operational orders (`CONFIRMED`, `IN_PROGRESS`) remain unaffected.

### R5. Architecture & Security
Do not overload the `OrderStatus` enum with payment states; keep operational and payment states separate. Reuse existing pricing and snapshot architectures. Ensure strict tenant/seller data isolation. Financial mutations must be idempotent.

## Acceptance Criteria

### Testing & Verification
- [ ] **Payment Timing:** Tests verify that order creation does not charge the customer, and payment is requested only after pickup details are approved.
- [ ] **Commercial & Gateway:** Tests verify commission calculation (including partial/full refunds), and separate recording of gateway fees/taxes.
- [ ] **Settlement:** Tests verify the 15-day hold logic for TTC gateways and direct settlement for seller gateways.
- [ ] **Restrictions:** Tests verify `PENDING` marketplace orders are cancelled when a seller becomes restricted, and re-selection creates a new valid order without refunding (since no payment occurred yet).
- [ ] **Regression & CI:** The full Phase 1–7 test suite passes. Fresh DB migration succeeds (`alembic upgrade head`). Backend linting and typechecking pass.

## 2026-09-20T08:01:28Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: Full team (multi-part project on an existing codebase)

Implement the finalized TTC business decisions regarding Driver Assignment, Reassignment, and Notification behaviors (Q51–Q100).

Working directory: `/workspaces/TheTextileCare`
Integrity mode: development

## Requirements

### R1. Driver Assignment & Eligibility
Implement automatic and manual driver assignment logic based on strict eligibility rules (active, authorized, available, compliance valid). Do not use an accept/reject workflow; assignment is authoritative. Driver preference must follow the established priority order (exact address familiarity > customer familiarity > workload > distance). Implement concurrency-safe assignment logic using PostgreSQL locking, ensuring exactly one active driver at a time.

### R2. Reassignment & Unavailable Drivers
Support manual reassignment for seller staff with order access (requires a mandatory reason). 
- If a driver is unavailable **before** duty starts: Automatically attempt reassignment to another eligible driver and alert operations. 
- If a driver is unavailable **after** duty starts, or fails to start on time: Do not automatically reassign; trigger an operations alert requiring manual intervention.
Preserve an auditable assignment history; historical drivers are no longer operationally active.

### R3. Driver & Customer Notifications
Implement immediate notification delivery upon assignment/reassignment. Provide the customer with the active driver's name, vehicle details, and actual phone number. Do not roll back or cancel an assignment due to a notification delivery failure; use retry mechanisms instead. Support configurable notification channels (Push, In-App, SMS, WhatsApp) controlled by platform admin (Marketplace) or within platform capabilities (Full-Access Seller).

### R4. Security & Architectural Boundaries
Enforce strict tenant/seller isolation for all assignment operations. Do not equate driver assignment eligibility with full payment unless configured. Extend existing explicit domain action APIs (e.g., `assign`, `reassign`) rather than generic status mutations. Rely on the shared platform infrastructure and single driver app; do not build seller-specific custom apps or distributed infrastructure (Kafka/Redis) for this checkpoint.

## Acceptance Criteria

### Testing & Verification
- [ ] **Automatic Assignment:** Tests verify preferred driver selection, timeout fallback, expanded pool usage, and operations alerts if no driver is available (without order cancellation).
- [ ] **Driver Unavailability:** Tests verify automatic reassignment before duty starts, and manual-only reassignment if unavailable after duty start or if late.
- [ ] **Manual Reassignment:** Tests verify authorized staff can reassign with a mandatory reason, and that the history reflects the change with only one active driver.
- [ ] **Notifications & Information:** Tests verify immediate notification triggers for both driver and customer, including the exposure of the driver's actual phone number, and that notification failures do not invalidate assignments.
- [ ] **Isolation & Concurrency:** Tests verify that Seller/Tenant A cannot reassign Seller/Tenant B's drivers, and concurrency tests prevent multiple active assignments for the same duty.
- [ ] **Regression & CI:** The full existing test suite passes without regressions. Fresh DB migrations succeed (`alembic upgrade head`). Backend linting and typechecking pass.
