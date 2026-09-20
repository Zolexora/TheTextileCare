# Project: TTC Driver Assignment, Reassignment & Notification Behaviors (Q51–Q100 / R1–R4)

## Architecture
- **Layered Modular Monolith**: FastAPI, SQLAlchemy 2.0 (async/sync sessions), Alembic, PostgreSQL (psycopg3).
- **Driver Domain & Shared Application (ADR-009)**:
  - Single shared platform driver app infrastructure (`apps/driver-mobile`).
  - Drivers are registered on the platform (`drivers`), optionally scoped to `tenant_id` / `seller_id` or platform shared pool via `driver_seller_authorizations`.
  - Vehicle details (`driver_vehicles`) capture `make`, `model`, `plate_number`, `vehicle_type`, and `color`.
  - Compliance documents (`driver_compliance_documents`) track `DL`, `RC`, `INSURANCE`, `BGC` with explicit expiration and verification flags.
- **Logistics Duties & Authoritative Assignment (R1, R4)**:
  - Logistics tasks modeled as `driver_duties` (`duty_type`: `PICKUP`, `DELIVERY`).
  - `OrderPickup` (`order_pickups`) and `Order` are coupled with duties upon confirmation without requiring payment completion (Payment Decoupling).
  - Authoritative dispatch: NO accept/reject workflow; assignment is immediately binding.
  - Concurrency safety: PostgreSQL row locking (`SELECT * FROM driver_duties WHERE id = :duty_id FOR UPDATE`) combined with a database engine partial unique index `CREATE UNIQUE INDEX uq_duty_active_assignment ON driver_assignments (duty_id) WHERE is_active = TRUE`. Exactly one driver can be active at a time.
  - Priority Resolution Engine implements strict lexicographical ordering:
    $$\text{Exact Address Familiarity} \succ \text{Customer Familiarity} \succ \text{Workload Balancing} \succ \text{Geographic Proximity}$$
    Deterministic tie-breaking: `created_at ASC`, `id ASC`.
- **Reassignment & Unavailability Protocol (R2)**:
  - Manual reassignment requires authorized seller staff and mandatory non-empty `reassignment_reason`.
  - Bifurcated unavailability:
    - Pre-Duty (`duty_started_at IS NULL`): Automatic reassignment attempt to next eligible driver + operations alert (`WARNING`).
    - Post-Duty (`duty_started_at IS NOT NULL`) or Late Start SLA Breach: Automatic reassignment is **strictly prohibited**. Triggers emergency operations alert (`CRITICAL`) requiring manual human intervention.
  - Auditable assignment history preserved in `driver_assignments`. Replaced drivers are deactivated operationally.
- **Multi-Channel Resilient Notifications (R3)**:
  - Immediate notification dispatch on assignment and reassignment.
  - Customer payload includes active driver full name, vehicle make/model/plate, and actual unmasked phone number.
  - Decoupled resilience: Notification delivery failure **must never roll back or cancel** the assignment transaction; failures are logged to `notification_logs` with status `FAILED` and queued for retry.
  - Channels supported: `PUSH`, `IN_APP`, `SMS`, `WHATSAPP`. Channel governance controlled by Platform Admin (Marketplace) or Seller settings.
- **Tenant & Architectural Boundaries (R4)**:
  - Strict tenant and seller isolation enforced via `TenantContext`. Tenant/Seller A cannot access or reassign Tenant/Seller B's drivers or duties.
  - Explicit domain actions (`assign`, `reassign`, `report-unavailability`) rather than generic mutations.
  - Modular monolith using PostgreSQL; zero external distributed message brokers (Kafka/Redis) for this phase.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Driver Domain Schema & Migration | Alembic migration revising `b2c3d4e5f6a7` creating `drivers`, `driver_vehicles`, `driver_seller_authorizations`, `driver_compliance_documents` | M1 | Survey / Q51-Q56 |
| 2 | Driver Domain Models & Schemas | SQLAlchemy 2.0 models and Pydantic v2 schemas for drivers, vehicles, compliance, and seller authorizations | M1 | Survey / Q51-Q56 |
| 3 | Driver RBAC & Permission Registration | Register permissions (`driver.manage`, `driver.view`, `duty.manage`, `duty.view`, `duty.reassign`, `operations_alert.view`) and `RoleName.DRIVER` | M1 | Survey / Q51-Q52 |
| 4 | Driver Eligibility Evaluation Service | Strict gate: active status, on-duty shift, seller authorization, compliance validity (`DL`, `RC`, `INSURANCE`, `BGC`), and active duty capacity (`max_active_duties`) | M1 | Survey / R1, Q53-Q58 |
| 5 | 4-Tier Algorithmic Familiarity & Priority Engine | Deterministic ranking: Exact Address Familiarity > Customer Familiarity > Workload Balancing > Geographic Proximity; tie-break by seniority | M1 | Survey / R1, Q71-Q80 |
| 6 | Driver Management REST Endpoints | Admin & Seller endpoints for driver onboarding, vehicles, compliance, shift status under `/api/v1/seller/drivers` and `/api/v1/platform/drivers` | M1 | Survey / Q51-Q60 |
| 7 | Logistics Duty & Assignment Schema & Migration | Migration creating `driver_duties`, `driver_assignments` (with partial unique index `uq_duty_active_assignment`), and `operations_alerts` | M2 | Survey / Q61-Q70 |
| 8 | Duty Domain Models & Schemas | SQLAlchemy 2.0 models and Pydantic v2 schemas for `DriverDuty`, `DriverAssignment`, `OperationsAlert` | M2 | Survey / Q61-Q65 |
| 9 | Duty Creation & Fulfillment Coupling | Auto-provision `PICKUP` duties from `OrderPickup` and `DELIVERY` duties from confirmed orders | M2 | Survey / Q61, Q67 |
| 10 | Concurrency-Safe Authoritative Assignment Engine | PostgreSQL `SELECT ... FOR UPDATE` locking on duty, enforcing single active driver invariant without accept/reject | M2 | Survey / R1, Q62-Q66 |
| 11 | Assignment Timeout Fallback & Pool Exhaustion | Primary branch pool -> secondary pool expansion -> `NO_DRIVER_AVAILABLE` operations alert without cancelling order | M2 | Survey / R1, Q69-Q70 |
| 12 | Manual Driver Reassignment Engine | `POST /api/v1/seller/duties/{duty_id}/reassign` requiring non-empty `reassignment_reason`, deactivating previous driver | M2 | Survey / R2, Q81-Q82 |
| 13 | Bifurcated Driver Unavailability Protocol | Pre-duty: auto-reassign + `WARNING` ops alert; Post-duty / late start: manual intervention ONLY + `CRITICAL` ops alert, no auto-reassign | M2 | Survey / R2, Q83-Q87 |
| 14 | Auditable Assignment & Duty History | Append-only tracking in `driver_assignments` (`assigned_at`, `unassigned_at`, `is_active`, `reason`, `actor_user_id`) | M2 | Survey / R2, Q88-Q89 |
| 15 | Operations Alert Engine & REST Endpoints | Store and query alerts in `operations_alerts` under `/api/v1/seller/alerts/` and `/api/v1/platform/alerts/` | M2 | Survey / R2, Q90 |
| 16 | Multi-Channel Notification Schema & Migration | Migration creating `notification_logs` and `notification_configs` | M3 | Survey / Q91-Q100 |
| 17 | Notification Domain Models & Schemas | SQLAlchemy 2.0 models and Pydantic v2 schemas for `NotificationLog`, `NotificationConfig`, and dispatch payloads | M3 | Survey / Q91-Q96 |
| 18 | Multi-Channel Adapters | Dispatch adapters for `PUSH`, `IN_APP`, `SMS`, `WHATSAPP` | M3 | Survey / R3, Q95 |
| 19 | Immediate Notification Delivery on Assignment | Customer payload includes driver full name, vehicle make/model/plate, and actual unmasked phone number; notifications to drivers | M3 | Survey / R3, Q91-Q93, Q97-Q98 |
| 20 | Decoupled Notification Failure Resilience & Retries | Notification failures NEVER roll back assignments; logged with status `FAILED` and queued for retry | M3 | Survey / R3, Q94 |
| 21 | Notification Channel Configuration & Governance | Platform admin controls for Marketplace; seller controls for Full-Access Sellers | M3 | Survey / R3, Q96 |
| 22 | Notification Management REST Endpoints | Query logs, retry failed notifications, and update channel configs under `/api/v1/notifications/` | M3 | Survey / R3, Q91-Q100 |
| 23 | Tenant & Seller Isolation Enforcement | Strict tenant context filtering on all queries and mutations; Seller A cannot view or reassign Seller B drivers/duties | M1, M2, M3 | Survey / R4, Q60, Q99 |
| 24 | Payment Decoupling Architectural Boundary | Duty assignment independent of payment completion; orders progress to pickup assignment before payment | M1, M2 | Survey / R4, Q68 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Driver Domain Foundation, Compliance & Priority Engine | Features 1–6, 23, 24: Driver migration, models, schemas, RBAC permissions, driver eligibility engine, 4-tier familiarity priority engine, driver management APIs, unit & service tests | none | PLANNED |
| M2 | Logistics Duties, Concurrency-Safe Assignment & Reassignment Engine | Features 7–15, 23, 24: Duty migration, models, schemas, duty lifecycle, PostgreSQL row locking (`FOR UPDATE`), single active driver invariant, automatic & manual assignment, pre/post duty unavailability, operations alerts, REST APIs, concurrency tests | M1 | PLANNED |
| M3 | Multi-Channel Resilient Notification Engine & APIs | Features 16–22, 23: Notification migration, models, schemas, channel adapters (Push, In-App, SMS, WhatsApp), customer payload with unmasked phone & vehicle details, decoupled failure resilience with retries, configuration APIs | M1, M2 | PLANNED |
| M4 | Final Milestone: 100% E2E Test Suite & Adversarial Hardening | Phase 1: Pass 100% of E2E tests (Tiers 1–4) published in `TEST_READY.md`. Phase 2: Adversarial Coverage Hardening (Tier 5) with Challengers finding edge-case coverage gaps. Full monorepo CI validation (`pytest`, `alembic upgrade head`, `ruff`, `mypy`/`pyright`) | M1, M2, M3 | PLANNED |

## Interface Contracts

### Driver Service ↔ Priority Engine (M1)
- `DriverEligibilityService.get_eligible_candidates(seller_id: UUID, branch_id: UUID, required_capacity: int = 1) -> list[Driver]`
  - Validates: `status == ACTIVE`, `is_on_duty == True`, `compliance_valid == True`, `active_duties < max_active_duties`.
- `PriorityResolutionEngine.rank_candidates(duty: DriverDuty, candidates: list[Driver]) -> list[DriverRankingResult]`
  - Computes:
    1. `address_familiarity_score`: completed duties count at destination address.
    2. `customer_familiarity_score`: completed duties count for customer.
    3. `workload_score`: -1 * count of current active duties.
    4. `proximity_score`: -1 * Haversine distance in meters.
  - Returns deterministically sorted candidates; candidate at index 0 is primary.

### Assignment Service ↔ Duty & Concurrency Engine (M2)
- `AssignmentService.assign_driver(duty_id: UUID, driver_id: UUID | None, actor_user_id: UUID | None, is_auto: bool = False, notes: str | None = None) -> DriverAssignment`
  - Acquires row lock: `SELECT * FROM driver_duties WHERE id = :duty_id FOR UPDATE`.
  - Verifies duty is unassigned or reassignable.
  - If `driver_id` is None, calls `PriorityResolutionEngine`.
  - Inserts `DriverAssignment(status=ACTIVE, is_active=True)`.
  - Enforces database partial unique index: `uq_duty_active_assignment`.
  - Triggers notification job asynchronously.
- `AssignmentService.reassign_driver(duty_id: UUID, new_driver_id: UUID | None, reason: str, actor_user_id: UUID) -> DriverAssignment`
  - Validates `reason` is non-empty (min 3 chars).
  - Acquires row lock: `SELECT * FROM driver_duties WHERE id = :duty_id FOR UPDATE`.
  - Deactivates previous assignment (`is_active=False`, `unassigned_at=now()`, `status=REASSIGNED`).
  - If pre-duty unavailability: auto-reassigns + creates `OperationsAlert(WARNING)`.
  - If post-duty unavailability or late start: raises `CRITICAL` alert; blocks auto-reassignment.

### Notification Engine ↔ Assignment Lifecycle (M3)
- `NotificationService.notify_assignment(duty: DriverDuty, assignment: DriverAssignment, previous_driver_id: UUID | None = None) -> NotificationDispatchResult`
  - Gathers driver full name, vehicle make/model/plate, unmasked actual phone number.
  - Dispatches immediate customer notification across configured channels (`PUSH`, `IN_APP`, `SMS`, `WHATSAPP`).
  - Dispatches assignment notification to new driver; reassignment notification to previous driver (if applicable).
  - Enclosed in decoupled transaction boundary: exceptions caught, logged to `notification_logs` as `FAILED`, scheduled for retry. Returns success status without raising.

## Code Layout
```
backend/
├── app/
│   ├── models/
│   │   ├── driver.py            # M1: Driver, DriverVehicle, DriverSellerAuthorization, DriverCompliance
│   │   ├── duty.py              # M2: DriverDuty, DriverAssignment, OperationsAlert
│   │   └── notification.py      # M3: NotificationLog, NotificationConfig
│   ├── schemas/
│   │   ├── driver.py            # M1: Pydantic schemas for driver domain
│   │   ├── duty.py              # M2: Pydantic schemas for duty, assignment, alerts
│   │   └── notification.py      # M3: Pydantic schemas for notifications
│   ├── services/
│   │   ├── driver.py            # M1: Driver CRUD, compliance verification
│   │   ├── priority_engine.py   # M1: 4-tier algorithmic priority resolution
│   │   ├── duty.py              # M2: Duty lifecycle, pickup/delivery coupling
│   │   ├── assignment.py        # M2: Concurrency-safe assignment, reassignment & unavailability
│   │   ├── operations_alert.py  # M2: Operational alerts logging & queries
│   │   └── notification.py      # M3: Resilient multi-channel notification engine
│   ├── api/v1/
│   │   ├── driver.py            # M1: Driver management REST endpoints
│   │   ├── duty.py              # M2: Duty & assignment REST endpoints
│   │   ├── alerts.py            # M2: Operations alerts REST endpoints
│   │   └── notification.py      # M3: Notification logs & configs REST endpoints
│   └── core/permissions/
│       └── constants.py         # M1: Driver roles & permissions
├── migrations/versions/
│   └── c3d4e5f6a7b8_phase8_driver_assignment_notifications.py  # Alembic migration (down_revision: b2c3d4e5f6a7)
└── tests/
    ├── unit/
    │   ├── test_driver_priority_engine.py
    │   ├── test_driver_eligibility.py
    │   └── test_notification_resilience.py
    ├── integration/
    │   ├── test_driver_assignment_concurrency.py
    │   ├── test_driver_reassignment_unavailability.py
    │   └── test_driver_notifications.py
    └── e2e/
        ├── test_driver_tier1_features.py
        ├── test_driver_tier2_boundaries.py
        ├── test_driver_tier3_combinations.py
        ├── test_driver_tier4_scenarios.py
        └── test_driver_tier5_adversarial.py
```
