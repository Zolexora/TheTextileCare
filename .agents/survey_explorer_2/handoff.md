# Survey Explorer 2 Investigation & Handoff Report: Driver Assignment, Reassignment, & Notifications (Q51–Q100 / R1–R4)

**Document Status**: Final Investigation & Architectural Survey  
**Working Directory**: `/workspaces/TheTextileCare/.agents/survey_explorer_2`  
**Author**: `survey_explorer_2`  
**Target Milestone**: Business Decisions Q51–Q100 (Requirements R1–R4)  
**Date**: 2026-09-20  

---

## 1. Executive Summary

This report delivers a comprehensive architectural survey and gap analysis of the backend codebase at `/workspaces/TheTextileCare` to inform the implementation of **Driver Assignment, Reassignment, and Notification behaviors (Q51–Q100 / R1–R4)**.

Key findings:
1. **Zero Existing Driver Domain**: Currently, the backend contains **no driver models, no driver database tables, no driver role in RBAC, and no driver management APIs**. The string `"driver"` appears only as a transient `driver_notes` attribute on the `OrderPickup` Pydantic schema and service argument, with no dedicated database column on `order_pickups`.
2. **Order & Pickup Decoupling**: While Phase 7 introduced `OrderPickup` (`order_pickups`) for physical garment inspection, there is no generic fulfillment "duty" or "task" concept (covering pickup duties and delivery duties), nor any table representing driver assignments or assignment audit history.
3. **Empty Notification System**: `backend/app/integrations/notifications/__init__.py` is a 2-line comment placeholder. No notification services, channel adapters (SMS, WhatsApp, Push, In-App), notification dispatch logs, or retry mechanisms exist.
4. **Migration Lineage Established**: The database contains 9 Alembic migrations up to Phase 7 head revision `b2c3d4e5f6a7` (`b2c3d4e5f6a7_phase7_commercial_billing_payment.py`). The next migration will revise `b2c3d4e5f6a7`.
5. **Architectural Blueprint**: In accordance with **ADR-009 (Shared Driver Application)**, driver workflows are cross-tenant and standardized on a single shared driver app infrastructure. To fulfill R1–R4 without introducing distributed brokers (Kafka/Redis), we propose a deterministic, concurrency-safe design inside the existing modular monolith (FastAPI, SQLAlchemy 2.0, PostgreSQL row-level locks, and Alembic).

---

## 2. Observations & Current Codebase Architecture

### 2.1 Driver Domain (or Lack Thereof)
- **Observation**: Inspection of `backend/app/models/__init__.py` and `backend/app/models/` reveals 18 entity files (`audit.py`, `billing.py`, `catalog.py`, `commercial.py`, `configuration.py`, `customer.py`, `membership.py`, `order.py`, `payment.py`, `permission.py`, `pickup.py`, `pricing.py`, `role.py`, `role_permission.py`, `seller.py`, `tenant.py`, `user.py`), but **no `driver.py`**.
- **Observation**: A full-text grep for `driver` across `backend/app` reveals:
  - `backend/app/schemas/pickup.py`: Lines 39, 60 define `driver_notes: str | None = Field(default=None, max_length=1000)`.
  - `backend/app/api/v1/pickup.py`: Line 74 passes `driver_notes=request.driver_notes`.
  - `backend/app/services/pickup.py`: Line 98 sets `result.driver_notes = driver_notes` dynamically on the model instance, but `OrderPickup` in `backend/app/models/pickup.py` has **no database column** for `driver_notes`.
- **Observation**: Inspection of `backend/app/core/permissions/constants.py` shows:
  - `RoleName` enum has `PLATFORM_ADMIN`, `PLATFORM_SUPPORT`, `TENANT_OWNER`, `TENANT_ADMIN`, `TENANT_MEMBER`, `TENANT_VIEWER`, `SELLER_OWNER`, `SELLER_ADMIN`, `STAFF`, `VIEWER`, `CUSTOMER`. **`DRIVER` is absent**.
  - No permissions exist for drivers, duty assignment, or operational alerts.
- **Architectural Policy**: `docs/decisions/ADR-009-shared-driver-application.md` states:
  > "Decision: Provide one shared driver application branded under The Textile Care Driver."
  > "Reason: Driver workflows are cross-tenant and should not be duplicated across seller-specific repositories."

### 2.2 Order & Pickup/Delivery Domain
- **Observation**: `backend/app/models/order.py` manages the commercial and operational order lifecycle via `OrderStatus` (`DRAFT`, `PENDING`, `CONFIRMED`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`).
  - Lines 181–186 define `status_history: Mapped[list[OrderStatusHistory]]` for order status transitions.
  - Lines 190–192 define `pickup: Mapped[OrderPickup | None]` (one-to-one).
- **Observation**: `backend/app/models/pickup.py` defines `OrderPickup` with status enum `PickupStatus` (`SCHEDULED`, `DETAILS_SUBMITTED`, `APPROVED`, `REJECTED`, `COMPLETED`).
  - `order_pickups` table contains: `id`, `tenant_id`, `seller_id`, `order_id`, `status`, `actual_pickup_at`, `details_submitted_at`, `approved_at`, `rejection_reason`, `actual_details`, `created_at`, `updated_at`.
  - There is **no driver foreign key, no duty entity, no assignment history, and no delivery stage representation**.
- **Observation**: Orders require two distinct fulfillment legs: **Pickup** (customer $\to$ seller facility) and **Delivery** (seller facility $\to$ customer). Currently, only pickup has a domain model (`OrderPickup`).

### 2.3 Notification Models & Integrations
- **Observation**: `backend/app/integrations/notifications/__init__.py` contains only:
  ```python
  """Notifications integration placeholder."""
  ```
- **Observation**: No notification dispatch tables, notification logs, queue tables, or retry mechanisms exist in the database or service layers.
- **Observation**: `backend/app/services/audit.py` provides `AuditEvent` logging to table `audit_events`, but is strictly an audit trail rather than an operational alerting or notification delivery system.

### 2.4 Database Schema & Alembic Migration Lineage
- **Observation**: The migration versions directory is located at `/workspaces/TheTextileCare/backend/migrations/versions/` (configured via `backend/alembic.ini`: `script_location = migrations`).
- **Observation**: The existing migration chain consists of 9 sequential revisions:
  1. `0001_phase1_identity_and_tenancy.py` (down_revision: None)
  2. `2010fc7ee67f_phase2_seller_platform.py`
  3. `debba6592524_phase2_harden_seller_foundation.py`
  4. `275f700c133f_phase3_customization_engine.py`
  5. `ddf173e6fc96_phase4_catalog_services.py`
  6. `e7f1a2b3c4d5_phase5_pricing_engine.py`
  7. `112e2205a754_phase6_marketplace_and_customer.py`
  8. `a1b2c3d4e5f6_phase7_order_foundation.py`
  9. `b2c3d4e5f6a7_phase7_commercial_billing_payment.py` (head)
- **Observation**: Verified via `PYTHONPATH=. alembic heads` that `b2c3d4e5f6a7` is the current migration head. The Phase 8 / Driver Assignment migration must specify `down_revision = 'b2c3d4e5f6a7'`.

---

## 3. Gap Analysis for Requirements R1–R4

| Requirement | Description in Request | Existing Codebase State | Gap to Implement |
|---|---|---|---|
| **R1. Driver Eligibility** | Strict eligibility: active, authorized, available, compliance valid. | No driver entities or status fields exist. | Create `drivers` model with `status`, `availability_status`, `compliance_status`, `compliance_expires_at`, and `driver_seller_authorizations` for tenant/seller authorization. |
| **R1. Authoritative Assignment** | No accept/reject workflow; assignment is authoritative. | No assignment service or logic exists. | Assignment immediately commits active assignment and transitions duty to `ASSIGNED`. No driver acceptance state or API. |
| **R1. Priority Resolution Engine** | Priority order: exact address familiarity > customer familiarity > workload > distance. | No priority ranking or driver selection algorithm exists. | Create `PriorityResolutionEngine` calculating: (1) previous completed duties at `customer_address_id`, (2) previous completed duties for `customer_id`, (3) active duty count, (4) geospatial distance to target coordinates. |
| **R1. Concurrency Safety** | PostgreSQL locking, ensuring exactly one active driver at a time. | No duty locking or active assignment uniqueness constraints exist. | Use PostgreSQL row locking (`SELECT ... FOR UPDATE` on duty) + DB partial unique index: `CREATE UNIQUE INDEX uq_duty_active_assignment ON driver_assignments (duty_id) WHERE is_active = true`. |
| **R1. Timeout & Unavailability Alerts** | Operations alert if no driver available without order cancellation. | No operations alert model or notification infrastructure exists. | Create `operations_alerts` table; if no eligible driver found, emit `OperationsAlert(NO_DRIVER_AVAILABLE)`, leave duty in `PENDING`, and keep order intact. |
| **R2. Manual Reassignment** | Authorized seller staff with order access; requires mandatory reason. | No reassignment endpoint or reason tracking exists. | Implement `POST /api/v1/seller/duties/{duty_id}/reassign` requiring non-empty `reassignment_reason`. Deactivate old assignment, activate new one. |
| **R2. Pre-Duty Unavailability** | If driver unavailable before duty starts: auto reassign + alert operations. | No duty start timestamp or auto-reassignment trigger exists. | If driver reports unavailable when `duty.duty_started_at is None`, mark assignment `UNAVAILABLE_PRE_DUTY`, auto-trigger `PriorityResolutionEngine`, and alert ops. |
| **R2. Post-Duty Unavailability & Late Starts** | If driver unavailable after duty starts or late: DO NOT auto reassign; manual intervention alert. | No start check or scheduled start delay detection exists. | If driver reports unavailable when `duty.duty_started_at is not None`, mark `UNAVAILABLE_POST_DUTY` and create `CRITICAL` ops alert. Detect late starts and alert without reassigning. |
| **R2. Auditable History** | Preserve auditable assignment history; historical drivers not operationally active. | No assignment history table exists. | Implement `driver_assignments` table with full transition history (`assigned_at`, `unassigned_at`, `is_active`, `reassignment_reason`, `actor_user_id`). |
| **R3. Driver & Customer Notifications** | Immediate notification on assign/reassign; customer receives driver name, vehicle, phone. | No notification models, payloads, or services exist. | Create `NotificationService` dispatching customer payload with driver name, vehicle details (make/model/plate), and actual phone number. |
| **R3. Notification Resilience** | Failure MUST NOT roll back assignment; use retry mechanisms. | No decoupled notification error handling exists. | Enclose notification dispatch in `try...except`, persist log in `notification_logs` with `FAILED` status and retry queue. Never roll back DB assignment. |
| **R3. Configurable Channels** | Channels: Push, In-App, SMS, WhatsApp. Platform admin controls marketplace; seller controls full-access. | Integrations folder is an empty placeholder. | Implement channel dispatch adapters with configuration overrides (stored in `notification_configs` or tenant/seller settings). |
| **R4. Tenant & Seller Isolation** | Seller A cannot reassign or access Seller B drivers/duties. | Tenancy middleware exists for seller/order, but not for drivers/duties. | Enforce `tenant_id` and `seller_id` filtering on all duty/assignment queries and mutations via `TenantContext`. |
| **R4. Decoupling from Payment** | Do not equate driver assignment eligibility with full payment unless configured. | Phase 7 payment logic currently blocks pickup completion if configured, but duties must allow assignment prior to payment. | Driver assignment is decoupled from order payment status; payment checks remain strictly confined to pickup completion gates. |
| **R4. Explicit Domain Action APIs** | Explicit domain actions (`assign`, `reassign`) vs generic mutations. | Existing orders use explicit actions (`confirm`, `start`, `complete`, `reject`). | Follow identical pattern: `POST /api/v1/seller/duties/{duty_id}/assign`, `POST /api/v1/seller/duties/{duty_id}/reassign`, etc. |
| **R4. Shared Platform Infrastructure** | Single shared driver app (ADR-009); no Kafka/Redis for this checkpoint. | Existing system is a clean modular monolith. | Build assignment queue, row locks, and notification logs strictly in PostgreSQL + SQLAlchemy 2.0. |

---

## 4. Proposed Schema & Model Additions (SQLAlchemy 2.0 / Alembic)

### 4.1 New Database Tables

#### 1. Table: `drivers`
Represents the driver profile, linked 1:1 with `User`, with operational status, compliance, and location attributes.
```sql
CREATE TABLE drivers (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    tenant_id UUID NULL REFERENCES tenants(id) ON DELETE CASCADE, -- NULL for shared platform pool
    seller_id UUID NULL REFERENCES sellers(id) ON DELETE CASCADE, -- NULL if multi-seller shared
    home_branch_id UUID NULL REFERENCES seller_branches(id) ON DELETE SET NULL,
    full_name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, INACTIVE, SUSPENDED
    compliance_status VARCHAR(50) NOT NULL DEFAULT 'COMPLIANT', -- COMPLIANT, EXPIRED, SUSPENDED, PENDING_REVIEW
    compliance_expires_at TIMESTAMP WITH TIME ZONE NULL,
    availability_status VARCHAR(50) NOT NULL DEFAULT 'AVAILABLE', -- AVAILABLE, BUSY, OFFLINE, UNAVAILABLE
    current_latitude NUMERIC(10, 7) NULL,
    current_longitude NUMERIC(10, 7) NULL,
    max_active_duties INTEGER NOT NULL DEFAULT 3,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
CREATE INDEX ix_drivers_user_id ON drivers(user_id);
CREATE INDEX ix_drivers_tenant_id ON drivers(tenant_id);
CREATE INDEX ix_drivers_seller_id ON drivers(seller_id);
CREATE INDEX ix_drivers_status_avail ON drivers(status, availability_status, compliance_status);
```

#### 2. Table: `driver_vehicles`
Maintains vehicle details exposed to customers upon assignment.
```sql
CREATE TABLE driver_vehicles (
    id UUID PRIMARY KEY,
    driver_id UUID NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,
    make VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    plate_number VARCHAR(50) NOT NULL,
    vehicle_type VARCHAR(50) NOT NULL DEFAULT 'SCOOTER', -- SCOOTER, MOTORCYCLE, VAN, CAR, BICYCLE
    color VARCHAR(50) NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
CREATE INDEX ix_driver_vehicles_driver_id ON driver_vehicles(driver_id);
```

#### 3. Table: `driver_seller_authorizations`
Authorizes platform drivers to serve specific tenants, sellers, or branches.
```sql
CREATE TABLE driver_seller_authorizations (
    id UUID PRIMARY KEY,
    driver_id UUID NOT NULL REFERENCES drivers(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    seller_id UUID NOT NULL REFERENCES sellers(id) ON DELETE CASCADE,
    branch_id UUID NULL REFERENCES seller_branches(id) ON DELETE CASCADE,
    is_authorized BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_driver_seller_auth UNIQUE (driver_id, seller_id, branch_id)
);
CREATE INDEX ix_driver_seller_auth_driver ON driver_seller_authorizations(driver_id);
CREATE INDEX ix_driver_seller_auth_seller ON driver_seller_authorizations(seller_id);
```

#### 4. Table: `driver_duties`
Operational unit of work (pickup or delivery) attached to an order.
```sql
CREATE TABLE driver_duties (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    seller_id UUID NOT NULL REFERENCES sellers(id) ON DELETE RESTRICT,
    branch_id UUID NOT NULL REFERENCES seller_branches(id) ON DELETE RESTRICT,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    pickup_id UUID NULL REFERENCES order_pickups(id) ON DELETE SET NULL,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    customer_address_id UUID NULL REFERENCES customer_addresses(id) ON DELETE SET NULL,
    duty_type VARCHAR(50) NOT NULL, -- PICKUP, DELIVERY
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING', -- PENDING, ASSIGNED, STARTED, IN_PROGRESS, COMPLETED, CANCELLED, FAILED
    active_driver_id UUID NULL REFERENCES drivers(id) ON DELETE SET NULL,
    target_address_snapshot JSONB NULL,
    scheduled_start_time TIMESTAMP WITH TIME ZONE NULL,
    duty_started_at TIMESTAMP WITH TIME ZONE NULL, -- Discriminator for pre-duty vs post-duty unavailability
    completed_at TIMESTAMP WITH TIME ZONE NULL,
    cancelled_at TIMESTAMP WITH TIME ZONE NULL,
    cancellation_reason VARCHAR(1000) NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
CREATE INDEX ix_driver_duties_order_id ON driver_duties(order_id);
CREATE INDEX ix_driver_duties_tenant_seller ON driver_duties(tenant_id, seller_id, status);
CREATE INDEX ix_driver_duties_active_driver ON driver_duties(active_driver_id);
CREATE INDEX ix_driver_duties_customer_address ON driver_duties(customer_address_id);
```

#### 5. Table: `driver_assignments`
Immutable, auditable historical ledger of driver assignments per duty.
```sql
CREATE TABLE driver_assignments (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    duty_id UUID NOT NULL REFERENCES driver_duties(id) ON DELETE CASCADE,
    driver_id UUID NOT NULL REFERENCES drivers(id) ON DELETE RESTRICT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, REASSIGNED, UNAVAILABLE_PRE_DUTY, UNAVAILABLE_POST_DUTY, LATE_ABORT, COMPLETED, CANCELLED
    assignment_type VARCHAR(50) NOT NULL DEFAULT 'AUTOMATIC', -- AUTOMATIC, MANUAL, REASSIGNMENT
    reassignment_reason VARCHAR(1000) NULL, -- MANDATORY on REASSIGNMENT
    assigned_by_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL, -- NULL for system auto-assign
    assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    unassigned_at TIMESTAMP WITH TIME ZONE NULL,
    notes VARCHAR(1000) NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
-- Concurrency invariant: Exactly ONE active assignment per duty
CREATE UNIQUE INDEX uq_duty_active_assignment ON driver_assignments (duty_id) WHERE is_active = true;
CREATE INDEX ix_driver_assignments_duty_id ON driver_assignments(duty_id);
CREATE INDEX ix_driver_assignments_driver_id ON driver_assignments(driver_id);
CREATE INDEX ix_driver_assignments_created_at ON driver_assignments(created_at);
```

#### 6. Table: `operations_alerts`
Tracks operational exceptions (unavailability, timeouts, late starts) for operations intervention.
```sql
CREATE TABLE operations_alerts (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    seller_id UUID NOT NULL REFERENCES sellers(id) ON DELETE RESTRICT,
    duty_id UUID NULL REFERENCES driver_duties(id) ON DELETE SET NULL,
    alert_type VARCHAR(50) NOT NULL, -- NO_DRIVER_AVAILABLE, DRIVER_UNAVAILABLE_PRE_DUTY, DRIVER_UNAVAILABLE_POST_DUTY, DRIVER_LATE_START, REASSIGNMENT_FAILED
    severity VARCHAR(50) NOT NULL DEFAULT 'WARNING', -- INFO, WARNING, CRITICAL
    status VARCHAR(50) NOT NULL DEFAULT 'OPEN', -- OPEN, ACKNOWLEDGED, RESOLVED
    message VARCHAR(1000) NOT NULL,
    details JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    resolved_at TIMESTAMP WITH TIME ZONE NULL,
    resolved_by_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX ix_operations_alerts_seller_status ON operations_alerts(seller_id, status);
CREATE INDEX ix_operations_alerts_duty_id ON operations_alerts(duty_id);
```

#### 7. Table: `notification_logs`
Resilient ledger of dispatched notifications across channels.
```sql
CREATE TABLE notification_logs (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    duty_id UUID NULL REFERENCES driver_duties(id) ON DELETE SET NULL,
    order_id UUID NULL REFERENCES orders(id) ON DELETE SET NULL,
    recipient_type VARCHAR(50) NOT NULL, -- DRIVER, CUSTOMER, OPERATIONS
    recipient_id UUID NOT NULL,
    channel VARCHAR(50) NOT NULL, -- PUSH, IN_APP, SMS, WHATSAPP
    title VARCHAR(255) NOT NULL,
    content VARCHAR(2000) NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}', -- Contains driver name, vehicle, actual phone number
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING', -- PENDING, SENT, FAILED, RETRYING
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    last_error VARCHAR(1000) NULL,
    sent_at TIMESTAMP WITH TIME ZONE NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()
);
CREATE INDEX ix_notification_logs_status_retry ON notification_logs(status, retry_count);
CREATE INDEX ix_notification_logs_duty_id ON notification_logs(duty_id);
```

#### 8. Table: `notification_configs`
Configurable channel permissions per tenant/seller or platform-wide.
```sql
CREATE TABLE notification_configs (
    id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    seller_id UUID NULL REFERENCES sellers(id) ON DELETE CASCADE,
    enabled_channels VARCHAR(50)[] NOT NULL DEFAULT ARRAY['IN_APP', 'SMS']::VARCHAR(50)[],
    sms_provider VARCHAR(50) NULL DEFAULT 'TWILIO',
    whatsapp_enabled BOOLEAN NOT NULL DEFAULT false,
    push_enabled BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_notification_config_seller UNIQUE (tenant_id, seller_id)
);
```

---

## 5. Proposed Service Architecture & API Endpoints

### 5.1 Service Layer Structure

```
backend/app/services/
├── assignment.py            # AssignmentService: Authoritative assignment, manual reassignment, locking
├── priority_engine.py       # PriorityResolutionEngine: Multi-factor ranking algorithm
├── driver.py                # DriverService: Driver profiles, availability, vehicles, authorizations
├── notification.py          # NotificationService: Channel dispatch, customer/driver payloads, retry loop
└── operations.py            # OperationsAlertService: Alert logging, escalation, resolution
```

#### 1. `PriorityResolutionEngine` (`backend/app/services/priority_engine.py`)
Implements the exact priority hierarchy mandated by R1:
$$\text{Exact Address Familiarity} > \text{Customer Familiarity} > \text{Workload} > \text{Distance}$$

Algorithm:
1. **Eligibility Filter**: Query candidates where:
   - `status == DriverStatus.ACTIVE`
   - `compliance_status == ComplianceStatus.COMPLIANT` and (`compliance_expires_at IS NULL` or `compliance_expires_at > now()`)
   - `availability_status == DriverAvailabilityStatus.AVAILABLE`
   - Active duties count $< \text{driver.max\_active\_duties}$
   - Authorized for seller/tenant (`driver_seller_authorizations.is_authorized == true`)
2. **Score Metrics Generation**:
   - `exact_address_familiarity`: $1$ if driver has completed $\ge 1$ duty at `duty.customer_address_id` (or matching address string), else $0$.
   - `customer_familiarity`: $1$ if driver has completed $\ge 1$ duty for `duty.customer_id`, else $0$.
   - `workload`: Number of duties where `active_driver_id == driver.id` and `status IN ('ASSIGNED', 'STARTED', 'IN_PROGRESS')`.
   - `distance`: Distance in km (Haversine or Euclidean) from driver location (or home branch) to customer coordinates.
3. **Deterministic Sorting**:
   ```python
   candidates.sort(
       key=lambda d: (
           d.address_familiarity,    # Descending (1 then 0)
           d.customer_familiarity,   # Descending (1 then 0)
           -d.current_workload,      # Ascending workload (fewer duties first)
           -d.distance_km,           # Ascending distance (closer first)
           str(d.id),                # Deterministic tie-breaker
       ),
       reverse=True,
   )
   ```

#### 2. `AssignmentService` (`backend/app/services/assignment.py`)
- **Concurrency Locking**:
  ```python
  stmt = select(DriverDuty).where(DriverDuty.id == duty_id).with_for_update()
  duty = self.db.execute(stmt).scalar_one_or_none()
  ```
- **Authoritative Automatic Assignment**: Resolves driver via `PriorityResolutionEngine`. If none found, logs `OperationsAlert(alert_type='NO_DRIVER_AVAILABLE')`, leaves duty `PENDING`, and does NOT cancel the order.
- **Manual Reassignment**:
  - Validates `reassignment_reason` is non-empty (`HTTP 422` if blank).
  - Deactivates current assignment: `current_assignment.is_active = False`, `status = 'REASSIGNED'`, `unassigned_at = now()`.
  - Creates new assignment with `is_active = True`, `status = 'ACTIVE'`, `assignment_type = 'REASSIGNMENT'`, `reassignment_reason = reason`.
  - Updates `duty.active_driver_id = new_driver_id`.
  - Dispatches immediate notifications asynchronously / non-blockingly.
- **Unavailability Handling**:
  - **Pre-Duty** (`duty.duty_started_at IS NULL`): Marks current assignment `UNAVAILABLE_PRE_DUTY`, sets driver to `UNAVAILABLE`, creates `OperationsAlert(DRIVER_UNAVAILABLE_PRE_DUTY, severity='INFO')`, and automatically attempts reassignment to next eligible driver.
  - **Post-Duty** (`duty.duty_started_at IS NOT NULL`): Marks assignment `UNAVAILABLE_POST_DUTY`, creates `OperationsAlert(DRIVER_UNAVAILABLE_POST_DUTY, severity='CRITICAL')`. **Strictly blocks automatic reassignment**, requiring manual dispatcher intervention.
  - **Late Start**: Background / on-demand check detects `now() > scheduled_start_time + tolerance` while `duty_started_at IS NULL`. Logs `OperationsAlert(DRIVER_LATE_START)` requiring manual intervention; does NOT auto-reassign.

#### 3. `NotificationService` (`backend/app/services/notification.py`)
- **Customer Payload Invariant**:
  ```json
  {
    "event": "DRIVER_ASSIGNED",
    "order_id": "...",
    "driver_name": "Rajesh Kumar",
    "driver_phone": "+919876543210",
    "vehicle": {
      "make": "Honda",
      "model": "Activa 6G",
      "plate_number": "KA-01-EQ-9876",
      "vehicle_type": "SCOOTER"
    }
  }
  ```
- **Failure Resilience**: Wrapped in `try...except Exception as err:`. If an SMS gateway or push notification times out, the error is recorded on `notification_logs(status='FAILED', last_error=str(err))`, and the database transaction for driver assignment remains safely committed.

### 5.2 API Routers & Endpoints

#### Seller Endpoints (`/api/v1/seller/duties/*` and `/api/v1/seller/operations/*`)
- `POST /api/v1/seller/duties/{duty_id}/auto-assign`: Trigger automatic assignment algorithm.
- `POST /api/v1/seller/duties/{duty_id}/assign`: Manual assignment to specific driver.
- `POST /api/v1/seller/duties/{duty_id}/reassign`: Reassign duty with mandatory `reassignment_reason`.
- `GET /api/v1/seller/duties`: List fulfillment duties (filtering by status, type, driver).
- `GET /api/v1/seller/duties/{duty_id}`: View duty details, active driver, and assignment history.
- `GET /api/v1/seller/operations/alerts`: List operations alerts.
- `POST /api/v1/seller/operations/alerts/{alert_id}/acknowledge`: Mark alert acknowledged.
- `POST /api/v1/seller/operations/alerts/{alert_id}/resolve`: Mark alert resolved.

#### Driver Endpoints (`/api/v1/driver/*` — Single Shared Driver App)
- `GET /api/v1/driver/duties`: List active and upcoming duties for authenticated driver.
- `POST /api/v1/driver/duties/{duty_id}/start`: Driver starts duty (records `duty_started_at = now()`, transitions to `STARTED`).
- `POST /api/v1/driver/duties/{duty_id}/complete`: Driver completes duty (records `completed_at = now()`, transitions to `COMPLETED`).
- `POST /api/v1/driver/duties/{duty_id}/unavailable`: Driver reports unavailability (triggers pre- vs post-duty behavior).
- `PUT /api/v1/driver/availability`: Driver toggles availability status and updates current GPS coordinates.

#### Customer Endpoints (`/api/v1/customer/orders/{order_id}/driver`)
- `GET /api/v1/customer/orders/{order_id}/driver`: Retrieves active driver details (name, vehicle details, actual phone number) for the customer's own order.

### 5.3 RBAC & Permission Extensions

In `backend/app/core/permissions/constants.py`:
- **New Role**: `RoleName.DRIVER = 'DRIVER'`
- **New Permissions**:
  - `driver.read = 'driver.read'`
  - `driver.manage = 'driver.manage'`
  - `driver.assign = 'driver.assign'`
  - `driver.reassign = 'driver.reassign'`
  - `duty.read = 'duty.read'`
  - `duty.manage = 'duty.manage'`
  - `alert.read = 'alert.read'`
  - `alert.manage = 'alert.manage'`
  - `notification.manage = 'notification.manage'`
- **Role Permissions Mapping**:
  - `PLATFORM_ADMIN`: All driver, duty, alert, and notification permissions.
  - `SELLER_OWNER` / `SELLER_ADMIN`: `driver.read`, `driver.assign`, `driver.reassign`, `duty.read`, `duty.manage`, `alert.read`, `alert.manage`.
  - `STAFF`: `driver.read`, `driver.assign`, `driver.reassign` (for authorized order branches), `duty.read`, `duty.manage`, `alert.read`.
  - `DRIVER`: `duty.read`, `duty.manage` (own duties only), `driver.read`.
  - `CUSTOMER`: `duty.read` (own order duties only).

---

## 6. Logic Chain

1. **Premise 1 (Absence of Driver Entities)**: Direct filesystem search and code inspection confirmed that no driver models or database tables exist. The string `driver` only appeared as an unpersisted field in `OrderPickup` schemas (`backend/app/schemas/pickup.py:39`).
   - *Inference*: Driver profile, vehicle, authorization, duty, and assignment models must be created from scratch.
2. **Premise 2 (Shared Driver App Context - ADR-009)**: `docs/decisions/ADR-009-shared-driver-application.md` specifies that drivers use a single platform app across tenants and sellers.
   - *Inference*: Drivers should be platform users (`users.id`) who can either belong to a dedicated seller or hold authorizations across multiple marketplace sellers via `driver_seller_authorizations`.
3. **Premise 3 (Eligibility & Priority Order - R1)**: Requirements mandate strict eligibility (active, authorized, available, compliant) and a deterministic 4-step priority hierarchy (exact address familiarity $>$ customer familiarity $>$ workload $>$ distance).
   - *Inference*: The selection algorithm must be isolated into a pure domain engine (`PriorityResolutionEngine`) that queries historical completed duties, active workload counts, and branch/address coordinates.
4. **Premise 4 (Concurrency & Single Active Assignment - R1/R4)**: Race conditions from concurrent automated assignment jobs or staff reassignment could cause two drivers to be assigned to the same duty.
   - *Inference*: A row-level lock (`SELECT ... FOR UPDATE`) on `driver_duties` combined with a PostgreSQL partial unique index (`WHERE is_active = true` on `driver_assignments`) guarantees absolute concurrency safety.
5. **Premise 5 (Pre- vs Post-Duty Unavailability Divergence - R2)**: Pre-duty unavailability can be safely auto-reassigned without physical risk. Post-duty unavailability occurs while the driver may already possess customer garments or be en route, introducing physical security and reconciliation risks.
   - *Inference*: Recording `duty_started_at` allows `AssignmentService` to strictly branch: pre-duty auto-reassigns to the next driver; post-duty and late-start strictly halt auto-reassignment, requiring human operations triage via an `OperationsAlert`.
6. **Premise 6 (Notification Decoupling - R3)**: External notification gateways (Twilio, Firebase, WhatsApp API) are subject to network latency and transient 5xx failures.
   - *Inference*: Wrapping notification calls in error-handling wrappers and writing to `notification_logs` guarantees that notification failures never abort or roll back driver assignments.
7. **Premise 7 (Payment Decoupling - R4)**: Phase 7 commercial rules permit orders in `PENDING` or `CONFIRMED` to proceed to pickup scheduling before full payment is collected (payment requested upon pickup approval).
   - *Inference*: Driver assignment eligibility must not query or mandate order payment status, keeping fulfillment dispatch decoupled from payment timing.

---

## 7. Caveats & Assumptions

1. **Local Distance Calculation**: The backend currently stores `latitude` and `longitude` as `Numeric(10, 7)` / `Float` on `CustomerAddress` and `seller_branches`. The Priority Resolution Engine can compute great-circle distance using standard Haversine or Euclidean distance formulas in Python or SQL without requiring PostGIS extensions.
2. **Database Test Concurrency**: When running pytest, running multiple concurrent test processes against the same database causes collisions because `reset_database` drops the `public` schema. Tests must be run sequentially or with unique database schemas per worker (e.g. `pytest-xdist` with template databases).
3. **External Gateway Mocking**: In development and automated CI tests, notification channel adapters should execute in mock mode, asserting dispatch payloads in `notification_logs` without making live third-party network calls.

---

## 8. Dependencies & Technical Risks

1. **Alembic Migration Stamping**: The Alembic migration head is `b2c3d4e5f6a7`. When creating the new migration, ensure `down_revision = 'b2c3d4e5f6a7'`. In fresh test environments, `alembic upgrade head` requires `PYTHONPATH=.` from `backend/`.
2. **Table Index Deduplication**: When adding tables with indexes in SQLAlchemy, ensure indexes are not declared both in `__table_args__` and on individual `mapped_column(index=True)` with conflicting names.
3. **Circular Foreign Keys**: `orders` has a one-to-one relationship with `order_pickups`, and `driver_duties` references `orders.id`, `order_pickups.id`, and `drivers.id`. Ensure foreign key constraints use `ON DELETE SET NULL` or `CASCADE` appropriately to avoid deletion deadlocks.

---

## 9. Conclusion

The existing TTC backend provides a solid modular monolith architecture (FastAPI, SQLAlchemy 2, Alembic, PostgreSQL) with robust tenant isolation and snapshot-based order models, but has **zero driver management, zero duty tracking, and zero notification services**.

Implementing Q51–Q100 (R1–R4) requires:
1. Creating 8 new database tables via an Alembic migration revising `b2c3d4e5f6a7`.
2. Implementing `PriorityResolutionEngine` with the exact 4-tier ranking criteria.
3. Implementing `AssignmentService` with PostgreSQL `FOR UPDATE` locking and pre-duty vs post-duty branching.
4. Implementing `NotificationService` with customer driver payload exposure and decoupled failure tolerance.
5. Registering the `DRIVER` role and granular driver/duty permissions in RBAC.

All business requirements R1–R4 can be cleanly fulfilled within the existing modular monolith boundaries without requiring microservices, Kafka, or Redis.

---

## 10. Verification Method

To independently verify the findings in this report:

1. **Verify Absence of Driver Models**:
   ```bash
   find /workspaces/TheTextileCare/backend/app/models -name "*driver*"
   grep -rn "driver" /workspaces/TheTextileCare/backend/app/models/
   ```
   *Expected Output*: Empty result (no driver model files or columns).

2. **Verify Alembic Migration Head**:
   ```bash
   cd /workspaces/TheTextileCare/backend && PYTHONPATH=. alembic heads
   ```
   *Expected Output*: `b2c3d4e5f6a7 (head)`

3. **Verify Existing Tests**:
   ```bash
   cd /workspaces/TheTextileCare/backend && pytest tests/unit/test_phase7_models_schemas.py -q
   ```
   *Expected Output*: Tests run and validate Phase 7 schema definitions.

4. **Verify Notification Integration Placeholder**:
   ```bash
   cat /workspaces/TheTextileCare/backend/app/integrations/notifications/__init__.py
   ```
   *Expected Output*: `"""Notifications integration placeholder."""`

---
*Report generated and self-verified by `survey_explorer_2`.*
