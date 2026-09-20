# Specification Mining Report: Driver Assignment, Reassignment & Notifications (Q51–Q100, R1–R4)

**Document Version**: 1.0.0  
**Target Milestone**: Driver Logistics Domain (Q51–Q100, R1–R4)  
**Authoritative Locations**:  
- `/workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md` (header `## 2026-09-20T08:01:28Z`)  
- `/workspaces/TheTextileCare/.agents/orchestrator_3/DISPATCH.md`  
- `/workspaces/TheTextileCare/.agents/survey_spec_miner_1/DISPATCH.md`  
- `/workspaces/TheTextileCare/docs/decisions/ADR-009-shared-driver-application.md`  
- `/workspaces/TheTextileCare/docs/architecture/`  

---

## 1. Executive Summary

This report establishes the authoritative specification, domain rules, mathematical priority algorithms, and edge-case contracts for the **TTC Driver Assignment, Reassignment, and Notification behaviors**, addressing business decisions **Q51–Q100** and requirements **R1–R4**.

### Core Findings & Architectural Posture
1. **Authoritative Dispatch (No Accept/Reject)**: In contrast to consumer gig-economy ride-hailing models where drivers may accept or reject dispatch offers, TTC operates an authoritative dispatch model. Once assigned by the system or authorized dispatcher, the task is binding immediately upon the driver.
2. **Deterministic 4-Tier Familiarity Priority Algorithm**:
   $$\text{Priority} = \text{Exact Address Familiarity} \succ \text{Customer Familiarity} \succ \text{Workload Balancing} \succ \text{Geographic Proximity}$$
   This hierarchy guarantees that drivers who have repeatedly serviced a customer's exact location are chosen first, followed by drivers familiar with the customer, followed by the driver with the lowest active workload, and finally shortest distance.
3. **Strict Concurrency Control & Single Active Driver Invariant**: Exactly one active driver can be assigned to a duty at any instant. Concurrent assignment attempts are serialized using PostgreSQL row-level locks (`SELECT ... FOR UPDATE`).
4. **Bifurcated Unavailability Protocol**:
   - **Pre-Duty**: Automatic reassignment attempt to the next eligible driver + operations alert (`WARNING`).
   - **Post-Duty / Late Start**: Automatic reassignment is **strictly prohibited** to avoid losing garment custody or physical route desynchronization. Triggers a high-severity operations alert (`CRITICAL`) requiring dispatcher manual intervention.
5. **Direct Customer Transparency & Resilient Multi-Channel Notifications**: Customers receive the driver's full name, vehicle make/model/plate, and actual unmasked phone number. Notification delivery failures are decoupled from database transactions and **must never roll back or cancel** an assignment.
6. **Payment Decoupling & Modular Monolith Boundary**: In alignment with Phase 7's post-pickup payment architecture, driver assignment eligibility is decoupled from order payment collection. Furthermore, per ADR-009, all operations integrate with the single shared driver app without introducing external distributed message brokers (Kafka/Redis) for this phase.

---

## 2. Q51–Q100 Authoritative Decision Mapping

The 50 business decisions governing driver assignment, reassignment, and notifications are categorized into five functional domains.

### 2.1 Category 1: Driver Profile, Authorization & Compliance (Q51–Q60)

| # | Question / Decision Item | Authoritative Specification & Domain Rule |
|---|--------------------------|-------------------------------------------|
| **Q51** | Driver Profile Entity | A driver is represented by `DriverProfile`, linked 1:1 with a platform `User`, associated with a `Seller` (or marketplace platform pool), storing license, phone, vehicle, and operational status. |
| **Q52** | Operational Status Lifecycle | Drivers have operational statuses: `ACTIVE` (eligible for dispatch), `INACTIVE` (disabled), `ON_LEAVE` (temporarily away), and `SUSPENDED` (compliance or disciplinary block). |
| **Q53** | Real-Time Shift & Duty Availability | Driver availability requires active shift state: `is_on_duty = True` and current active duties count strictly below `max_active_duties`. |
| **Q54** | Vehicle Attributes | Driver vehicle profiles capture `vehicle_type` (`BIKE`, `SCOOTER`, `VAN`, `CAR`), `make`, `model`, `color`, and `license_plate`. All details are customer-facing. |
| **Q55** | Compliance Document Model | Each driver must possess `DriverCompliance` records for: Driving License (`DL`), Vehicle Registration (`RC`), Vehicle Insurance (`INSURANCE`), and Background Check (`BGC`). |
| **Q56** | Compliance Validity Rule | A driver is eligible **only if** all required compliance documents have `is_verified = True` and `valid_until >= current_date`. Any expired document immediately disqualifies the driver. |
| **Q57** | Branch & Territory Scoping | Drivers are anchored to a primary `Branch` (`seller_branches.id`). Candidate pool selection prioritizes drivers affiliated with the order's fulfillment branch. |
| **Q58** | Concurrent Capacity Limits | Each driver has a configurable `max_active_duties` (default: 3). If `active_assignments >= max_active_duties`, driver is excluded from automatic matching. |
| **Q59** | Direct Contact Number | The driver's actual phone number is stored on `DriverProfile` and platform `User`. Direct phone exposure to the customer is mandatory for pickup/delivery coordination. |
| **Q60** | Multi-Tenant Partitioning | Drivers belong strictly to a `tenant_id` and `seller_id`. Single driver app (ADR-009) authenticates cross-tenant credentials but enforces strict tenant boundaries. |

### 2.2 Category 2: Logistics Duties & Concurrency-Safe Assignment (Q61–Q70)

| # | Question / Decision Item | Authoritative Specification & Domain Rule |
|---|--------------------------|-------------------------------------------|
| **Q61** | Logistics Duty Entity | A task is modeled as a `DriverDuty` (or `OrderDuty`), specifying `duty_type` (`PICKUP`, `DELIVERY`), `order_id`, `pickup_id` (if pickup), destination coordinates, and scheduled time window. |
| **Q62** | Authoritative Dispatch | No accept/reject workflow. When an assignment transaction commits, the duty is binding. The driver app shows assigned duties immediately in the active queue. |
| **Q63** | Duty State Transitions | Duty lifecycle: `UNASSIGNED` $\to$ `ASSIGNED` $\to$ `IN_PROGRESS` $\to$ `COMPLETED` (or `CANCELLED`, `FAILED`). |
| **Q64** | Single Active Driver Invariant | At any given time, exactly one driver can hold `status = ACTIVE` on a given `duty_id`. Multiple concurrent active assignments are strictly prohibited. |
| **Q65** | Concurrency Row-Level Locking | All assignment and reassignment transactions must acquire a PostgreSQL row lock: `SELECT * FROM driver_duties WHERE id = :duty_id FOR UPDATE`. |
| **Q66** | Manual Assignment Contract | Authorized dispatcher inputs `duty_id`, `driver_id`, and optional `notes`. Endpoint verifies tenant isolation, seller matching, and driver eligibility before locking. |
| **Q67** | Automatic Assignment Trigger | Automatic assignment triggers when an order transitions to `CONFIRMED`, when a pickup slot is scheduled, or upon an automated pre-duty reassignment event. |
| **Q68** | Payment Decoupling Invariant | Assignment does NOT require order payment completion. Pickup duties are dispatched while the order is in `CONFIRMED` before customer approves pickup details. |
| **Q69** | Assignment Fallback & Timeout | If no preferred tier-1 driver is available within the primary branch pool within the timeout window, search expands to secondary pools (neighboring branches of same seller). |
| **Q70** | Exhausted Pool Handling | If all candidate pools are exhausted without finding an eligible driver, the duty remains `UNASSIGNED`. The order is **never cancelled**; an operations alert is raised. |

### 2.3 Category 3: Algorithmic Priority, Familiarity & Workload (Q71–Q80)

| # | Question / Decision Item | Authoritative Specification & Domain Rule |
|---|--------------------------|-------------------------------------------|
| **Q71** | Precedence Order Definition | Driver candidates are ranked strictly by: 1) Exact address familiarity, 2) Customer familiarity, 3) Workload balancing, 4) Distance. |
| **Q72** | Tier 1: Exact Address Familiarity | Count of completed duties where `duty.destination_address_id == candidate.completed_address_id` (or normalized coordinate proximity $\le 25\text{m}$). Highest count wins. |
| **Q73** | Tier 2: Customer Familiarity | If Tier 1 is tied (e.g., both 0 or equal), count of completed duties for `order.customer_id` across all addresses. Highest count wins. |
| **Q74** | Tier 3: Workload Balancing | If Tier 2 is tied, candidate with the fewest active duties currently in `ASSIGNED` or `IN_PROGRESS` ranks higher ($\min(\text{active\_duties})$). |
| **Q75** | Tier 4: Geographic Proximity | If Tier 3 is tied, shortest Haversine distance between driver location (or branch base) and customer coordinates ranks higher ($\min(\text{distance})$). |
| **Q76** | Deterministic Tie-Breaking | If all 4 tiers evaluate identically, resolve deterministically by driver registration seniority (`driver.created_at ASC`), followed by `driver.id ASC`. |
| **Q77** | Pre-Ranking Eligibility Gate | Candidate drivers must pass all binary gates: `status == ACTIVE`, `is_on_duty == True`, `compliance_valid == True`, `seller_id == duty.seller_id`, `active_duties < max_active_duties`. |
| **Q78** | Familiarity Lookback Scope | Historical familiarity evaluates all completed duties in database history (default all-time, configurable lookback e.g. 180 days). |
| **Q79** | Branch Boundary Scoping | Primary matching evaluates drivers assigned to `duty.branch_id`. Fallback evaluates same-seller drivers within maximum service radius. |
| **Q80** | Algorithmic Determinism | Ranking produces an immutable ordered list of eligible driver IDs. The engine assigns candidate at index 0. |

### 2.4 Category 4: Reassignments, Unavailability & Operational Alerts (Q81–Q90)

| # | Question / Decision Item | Authoritative Specification & Domain Rule |
|---|--------------------------|-------------------------------------------|
| **Q81** | Manual Reassignment Auth | Permitted only for users with `logistics.reassign` or `order.process` permissions within the duty's tenant and seller (`SELLER_OWNER`, `SELLER_ADMIN`, `STAFF`). |
| **Q82** | Mandatory Reason Invariant | Manual reassignment requires a non-empty `reason` string (min 3 characters, max 1000). Requests with missing or whitespace-only reasons are rejected with HTTP 422. |
| **Q83** | Pre-Duty Unavailability Definition | Driver becomes unavailable while `duty.status == ASSIGNED` and driver has **not** yet initiated route/progress (`IN_PROGRESS`). |
| **Q84** | Pre-Duty Automatic Reassignment | System automatically invokes priority selection algorithm for next eligible driver, deactivates former driver, logs audit trail, and generates an `INFO`/`WARNING` operations alert. |
| **Q85** | Post-Duty Unavailability Definition | Driver reports vehicle breakdown, accident, or distress while `duty.status == IN_PROGRESS` (garments physically collected or in transit). |
| **Q86** | Post-Duty Reassignment Prohibition | Automatic reassignment is **strictly prohibited** for post-duty unavailability. System must generate a `CRITICAL` operations alert requiring manual human intervention. |
| **Q87** | Late Start SLA Breach | If current time exceeds `scheduled_window_start + late_threshold_minutes` and status is still `ASSIGNED`: do NOT automatically reassign; trigger `LATE_START` operations alert. |
| **Q88** | Immutable Assignment History | All assignments are logged in append-only table `duty_assignment_history` with `duty_id`, `driver_id`, `assigned_at`, `unassigned_at`, `status`, `reason`, and `actor_id`. |
| **Q89** | Operational Access Revocation | When a driver is replaced, their assignment record is set to `status = REASSIGNED`. Driver app queries filter by `status == ACTIVE`, instantly removing order details. |
| **Q90** | Operations Alert Tiers | Alerts are stored in `operations_alerts`: `INFO` (pre-duty auto-reassign success), `WARNING` (pre-duty reassignment fallback/exhaustion), `CRITICAL` (post-duty breakdown, late start). |

### 2.5 Category 5: Multi-Channel Notifications & Security Boundaries (Q91–Q100)

| # | Question / Decision Item | Authoritative Specification & Domain Rule |
|---|--------------------------|-------------------------------------------|
| **Q91** | Immediate Delivery Trigger | Assignment or reassignment emits immediate notification jobs upon database transaction commit. |
| **Q92** | Customer Notification Payload | Customer notification payload must contain: driver full name, vehicle type, make, model, license plate, and driver's actual phone number. |
| **Q93** | Unmasked Phone Requirement | Phone masking is disabled per R3 specification; actual driver phone number is exposed to customer for direct operational contact. |
| **Q94** | Failure Resilience Invariant | Notification dispatch failures (SMS gateway timeout, push service down) **must never abort or rollback** the assignment database transaction. |
| **Q95** | Multi-Channel Capabilities | Supported channels: `PUSH` (driver & customer mobile apps), `IN_APP` (feed/message center), `SMS` (SMS gateway), and `WHATSAPP` (business API). |
| **Q96** | Channel Preference Governance | Channel routing is governed by Platform Admin (for Marketplace) or configured within platform capabilities by Full-Access Sellers. |
| **Q97** | Replaced Driver Notification | When reassigned, the replaced driver receives an immediate notification: "Duty Reassigned — You are no longer assigned to Duty #X". |
| **Q98** | Customer Reassignment Notification | Customer receives an immediate update notification: "Driver Updated — Your driver is now [New Driver Name] ([Vehicle Plate]), Phone: [Phone]". |
| **Q99** | Strict Multi-Tenant Isolation | Tenant A staff cannot view or reassign Tenant B's duties or drivers. Cross-tenant mutation attempts return HTTP 403 Forbidden or 404 Not Found. |
| **Q100** | Monolith Architecture & ADR-009 | Single shared driver application (`apps/driver-mobile`), modular monolith backend, PostgreSQL as sole locking mechanism; no external message brokers (Kafka/Redis). |

---

## 3. Detailed Requirements Analysis (R1–R4)

### 3.1 R1. Driver Assignment & Eligibility

#### 3.1.1 Eligibility Gates
A driver $D$ is eligible for assignment to duty $U$ at branch $B$ and seller $S$ if and only if all the following predicates hold:
$$\text{Eligible}(D, U) \iff \begin{cases}
D.\text{status} = \text{ACTIVE} \\
D.\text{is\_on\_duty} = \text{True} \\
D.\text{seller\_id} = U.\text{seller\_id} \\
D.\text{branch\_id} = U.\text{branch\_id} \quad (\text{or approved for seller zone}) \\
\text{ComplianceValid}(D) = \text{True} \\
D.\text{active\_duties\_count} < D.\text{max\_active\_duties}
\end{cases}$$

Where compliance validity requires:
$$\text{ComplianceValid}(D) \iff \forall doc \in \{\text{DL}, \text{RC}, \text{INSURANCE}, \text{BGC}\}: doc.\text{is\_verified} = \text{True} \land doc.\text{valid\_until} \ge \text{today}()$$

#### 3.1.2 Priority Scoring Function
Given a set of eligible drivers $\mathcal{E}$, each driver $d \in \mathcal{E}$ is assigned a deterministic score vector:
$$\mathbf{S}(d) = \Big( \text{AddressFamiliarity}(d, U.\text{addr\_id}), \;\; \text{CustomerFamiliarity}(d, U.\text{cust\_id}), \;\; -\text{ActiveDuties}(d), \;\; -\text{Distance}(d.\text{loc}, U.\text{loc}), \;\; -d.\text{created\_at}.\text{timestamp}(), \;\; -d.\text{id} \Big)$$

Candidates are sorted lexicographically in descending order:
$$d^* = \arg\max_{d \in \mathcal{E}} \mathbf{S}(d)$$

#### 3.1.3 Concurrency Control & Row-Level Locking
To ensure that two concurrent dispatch actions (or automated triggers) never assign multiple drivers to the same duty:
```sql
BEGIN;
SELECT * FROM driver_duties 
WHERE id = :duty_id AND tenant_id = :tenant_id 
FOR UPDATE;

-- Verify duty.status in ('UNASSIGNED', 'ASSIGNED')
-- Update assignment state atomically
UPDATE driver_duties 
SET status = 'ASSIGNED', active_driver_id = :selected_driver_id, updated_at = NOW() 
WHERE id = :duty_id;

INSERT INTO duty_assignment_history (duty_id, driver_id, status, assigned_at, actor_user_id) 
VALUES (:duty_id, :selected_driver_id, 'ACTIVE', NOW(), :actor_id);
COMMIT;
```

---

### 3.2 R2. Reassignment & Unavailable Drivers

#### 3.2.1 State Matrix & Transition Rules

| Trigger Event | Duty Status | Action Taken | Operational Alert Raised | Manual Intervention Required? |
| :--- | :--- | :--- | :--- | :--- |
| **Dispatcher Manual Reassign** | `ASSIGNED` | Reassign to specified eligible driver; set previous driver assignment to `REASSIGNED`. | `INFO`: `MANUAL_REASSIGNMENT` | Yes (initiated by user) |
| **Pre-Duty Driver Unavailable** | `ASSIGNED` | Automatically re-run priority selection algorithm to assign next best driver. | `WARNING`: `PRE_DUTY_REASSIGNMENT` | No (automatic, unless pool empty) |
| **Pre-Duty Pool Exhausted** | `ASSIGNED` | Duty moves to `UNASSIGNED`; remains in order lifecycle (order NOT cancelled). | `WARNING`: `DUTY_UNASSIGNED_NO_DRIVER` | Yes (staff must assign or adjust) |
| **Post-Duty Driver Unavailable** | `IN_PROGRESS` | **Block automated reassignment.** Retain active assignment; flag emergency state. | `CRITICAL`: `POST_DUTY_UNAVAILABLE_EMERGENCY` | **Yes (Strictly Mandatory)** |
| **Late Duty Start SLA Breach** | `ASSIGNED` | **Block automated reassignment.** Mark duty as late start. | `CRITICAL`: `LATE_DUTY_START` | **Yes (Strictly Mandatory)** |

#### 3.2.2 Mandatory Reassignment Reason
Any manual reassignment endpoint call (`POST /api/v1/logistics/duties/{duty_id}/reassign`) requires payload:
```json
{
  "new_driver_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "reason": "Driver vehicle flat tire reported at 08:30 AM"
}
```
Validation rules:
- `reason` is required.
- `len(reason.strip()) >= 3`.
- Empty or whitespace strings return HTTP 422 Unprocessable Entity.

---

### 3.3 R3. Driver & Customer Notifications

#### 3.3.1 Customer Notification Payload
When duty is assigned or reassigned, customer receives:
```json
{
  "event": "DRIVER_ASSIGNED",
  "order_id": "a0000000-0000-0000-0000-000000000001",
  "duty_type": "PICKUP",
  "driver": {
    "name": "Alex Johnson",
    "phone": "+15550192834",
    "vehicle": {
      "type": "VAN",
      "make": "Ford",
      "model": "Transit",
      "color": "White",
      "license_plate": "ABC-1234"
    }
  },
  "scheduled_window": {
    "start": "2026-09-20T10:00:00Z",
    "end": "2026-09-20T12:00:00Z"
  }
}
```

#### 3.3.2 Non-Blocking Failure Resilience Architecture
```
[Assignment Service]
        │
        ▼
   (Begin DB Tx)
        │
   Update DriverDuty & History
        │
   (Commit DB Tx) ───────────────► Assignment is Guaranteed Permanent
        │
        ▼ (Post-Commit / Background Task)
   [Notification Service]
        │
   Try Dispatch Channels (Push, SMS, WhatsApp, In-App)
        │
   ┌────┴───────────────────────────┐
   │ Success                        │ Failure
   ▼                                ▼
Log Notification Sent         Log Failure to notification_retries
                              Schedule Exponential Backoff Retry
                              (Assignment NOT Rolled Back!)
```

---

### 3.4 R4. Security & Architectural Boundaries

1. **Strict Multi-Tenant Isolation**:
   - `DriverProfile`, `DriverDuty`, and `DutyAssignmentHistory` must declare `tenant_id` and `seller_id`.
   - APIs enforce `TenantContext`. Queries enforce `WHERE tenant_id = :tenant_id AND seller_id = :seller_id`.
   - A dispatcher from Seller A attempting to assign Seller B's driver or reassign Seller B's duty receives HTTP 403 Forbidden or HTTP 404 Not Found.
2. **Payment Decoupling**:
   - Under Phase 7 architecture, order pickup occurs **before** final payment is requested or collected.
   - Assigning a driver to a pickup duty must succeed when `order.status == CONFIRMED` regardless of whether payment has occurred.
   - Even if `payment_required_before_pickup == True`, payment is required before **completing** pickup, not before **assigning** a driver.
3. **Explicit Domain Verbs**:
   - Endpoints must NOT be generic `PATCH /api/v1/duties/{id}` with arbitrary status mutations.
   - Endpoints must be explicit semantic actions:
     - `POST /api/v1/logistics/duties/{duty_id}/assign`
     - `POST /api/v1/logistics/duties/{duty_id}/reassign`
     - `POST /api/v1/logistics/duties/{duty_id}/unassign`
     - `POST /api/v1/logistics/duties/{duty_id}/start`
     - `POST /api/v1/logistics/duties/{duty_id}/complete`
4. **Modular Monolith & ADR-009**:
   - Shared mobile application: `apps/driver-mobile`.
   - Single PostgreSQL database with transactions and row-locking.
   - Zero external brokers (no Kafka clusters, no RabbitMQ nodes, no Redis Celery workers for this phase).

---

## 4. Features Discovered

| # | Category | Feature | Description | Inputs | Outputs | Error Behavior | Discovered Via |
|---|----------|---------|-------------|--------|---------|----------------|----------------|
| 1 | R1: Eligibility | Driver Profile & Compliance Registration | Creation and maintenance of driver profile and required compliance documents (DL, RC, Insurance, Background Check). | Driver personal info, vehicle details, document files, expiry dates | `DriverProfileResponse` with compliance status | 400 on duplicate user or invalid date format; 403 cross-tenant | Q51, Q54, Q55 |
| 2 | R1: Eligibility | Driver Shift & Availability Management | Driver toggle for on-duty status and real-time operational availability check against active duty capacity. | `is_on_duty: bool` | Updated duty status and capacity metrics | 400 if driver suspended; 403 cross-tenant | Q52, Q53, Q58 |
| 3 | R1: Eligibility | Strict Binary Eligibility Filter | Evaluates driver candidate against active status, shift state, compliance expiration, and max capacity. | `driver_id`, `seller_id`, `branch_id` | `bool (is_eligible)`, exclusion reason list | Returns `False` and reason if disqualified | Q56, Q77, R1 |
| 4 | R1: Assignment | 4-Tier Familiarity Priority Ranking | Deterministic algorithm ranking eligible drivers: Address Familiarity $\succ$ Customer Familiarity $\succ$ Workload $\succ$ Distance. | `duty_id`, list of eligible candidate driver IDs | Ordered list of candidate drivers with score breakdowns | Empty list if no eligible drivers available | Q59, Q71-Q76, R1 |
| 5 | R1: Assignment | Authoritative Automatic Duty Assignment | Dispatches preferred candidate to duty; immediately binding without driver accept/reject step. | `duty_id` | `DutyAssignmentResponse` with active driver details | Raises operations alert if no driver eligible; order untouched | Q62, Q67, R1 |
| 6 | R1: Assignment | Concurrency-Safe Row Locking | PostgreSQL `SELECT ... FOR UPDATE` serialization preventing duplicate active driver assignments under high concurrency. | `duty_id`, DB transaction session | Acquired exclusive row lock on duty | Prevents race condition; second transaction reads updated state | Q64, Q65, R1 |
| 7 | R1: Assignment | Timeout Fallback to Secondary Pools | Expands candidate search radius/branch pool if primary branch pool has no available driver within timeout window. | `duty_id`, timeout threshold | Secondary candidate list or expanded search result | Escalates to operations alert if secondary pool also empty | Q69, Q70, R1 |
| 8 | R2: Reassignment | Authorized Manual Reassignment | Allows authorized seller staff (`STAFF`, `SELLER_ADMIN`, `SELLER_OWNER`) to reassign a duty with mandatory reason. | `duty_id`, `new_driver_id`, `reason: str` | Updated `DutyAssignmentResponse`, new active driver | 422 if reason empty; 403 if unauthorized or cross-tenant | Q69, Q70, Q81, Q82, R2 |
| 9 | R2: Reassignment | Pre-Duty Unavailability Auto-Reassignment | When driver becomes unavailable before starting duty, automatically re-runs priority assignment and emits alert. | `duty_id`, driver unavailability trigger | Reassigned duty with new driver, `WARNING` alert | Duty marked unassigned if no alternate driver; alert escalated | Q71, Q83, Q84, R2 |
| 10 | R2: Reassignment | Post-Duty Unavailability Emergency Lockout | Blocks automatic reassignment if driver is unavailable after duty starts (`IN_PROGRESS`); emits critical operations alert. | `duty_id`, driver breakdown event | Duty kept in emergency status, `CRITICAL` alert | Rejects automated reassignment; requires manual dispatcher action | Q72, Q85, Q86, R2 |
| 11 | R2: Reassignment | Late Duty Start SLA Monitor | Detects when scheduled window start has elapsed without driver starting duty; alerts operations without auto-reassignment. | `duty_id`, `current_time`, late threshold | `CRITICAL` operations alert for late start | Does NOT automatically reassign; requires manual intervention | Q73, Q87, R2 |
| 12 | R2: Reassignment | Immutable Assignment History & Access Revocation | Records all assignment transitions in append-only log; deactivates replaced driver's operational view. | `duty_id`, `driver_id`, `status`, `reason`, `actor_id` | `DutyAssignmentHistory` entry; previous driver set to `REASSIGNED` | Database constraint ensures history cannot be altered | Q74-Q76, Q88, Q89, R2 |
| 13 | R3: Notifications | Immediate Customer Assignment Notification | Emits customer notification with active driver full name, vehicle make/model/plate, and actual phone number. | `duty_id`, `driver_id`, `customer_id` | Customer notification dispatch job | Does not block assignment on delivery failure | Q81-Q84, Q91-Q93, R3 |
| 14 | R3: Notifications | Immediate Driver Assignment Notification | Dispatches task details (pickup/delivery address, window, customer name) to driver mobile app upon assignment. | `duty_id`, `driver_id` | Driver push / in-app notification job | Dispatched asynchronously | Q88, Q91, R3 |
| 15 | R3: Notifications | Reassigned Driver Revocation Notification | Sends notification to replaced driver informing them that duty assignment was cancelled/reassigned. | `duty_id`, `previous_driver_id`, `reason` | Driver unassignment notification job | Asynchronous dispatch | Q89, Q97, R3 |
| 16 | R3: Notifications | Resilient Failure Decoupling & Retries | Guarantees that notification delivery failures do not roll back database assignment transactions; retries queued. | Notification payload, recipient channel | Retry queue entry with exponential backoff | Retries up to max attempts, logs dead letter alert | Q85, Q94, R3 |
| 17 | R3: Notifications | Configurable Multi-Channel Routing | Routes notifications across Push, In-App, SMS, and WhatsApp per platform admin and seller capabilities. | Channel config, user preference, message payload | Channel dispatch events | Gracefully skips unconfigured channels | Q86, Q87, Q95, Q96, R3 |
| 18 | R4: Security | Strict Tenant/Seller Isolation Boundary | Blocks cross-tenant access and prevents Seller A from querying or assigning Seller B's drivers or duties. | `TenantContext`, `duty_id`, `driver_id` | Enforced SQL query filter | HTTP 403 / 404 on cross-tenant mismatch | Q91, Q99, R4 |
| 19 | R4: Security | Order Payment Decoupling | Ensures driver assignment operates independently of order payment status; assignments proceed on `CONFIRMED` orders. | `order_id`, `duty_id` | Successful assignment without payment check | Only blocks pickup completion if `payment_required_before_pickup` | Q68, R4 |
| 20 | R4: Architecture | Explicit Domain Action REST APIs | Exposes semantic actions (`/assign`, `/reassign`, `/unassign`, `/start`, `/complete`) rather than generic CRUD mutations. | HTTP POST with domain action payloads | Standard API response envelope | HTTP 400/409 on invalid lifecycle transition | Q92, R4 |

---

## 5. Edge Cases & Boundary Conditions

| # | Feature | Input / Condition | Observed / Required Behavior |
|---|---------|-------------------|-----------------------------|
| 1 | 4-Tier Priority | Two eligible drivers have identical exact address familiarity, identical customer familiarity, identical workload, and identical distance. | Secondary deterministic tie-breaker resolves by driver registration seniority (`driver.created_at ASC`), followed by `driver.id ASC`. Zero randomness. |
| 2 | Eligibility | Driver has valid driving license, RC, and background check, but vehicle insurance expired at 00:00:00 today. | Driver is **immediately disqualified** by the binary compliance gate. Does not enter candidate scoring pool. |
| 3 | Eligibility | Driver has 2 active assignments and `max_active_duties = 2`. | Driver is excluded from automatic matching. Once an active assignment is completed, driver immediately becomes eligible again. |
| 4 | Pre-Duty Reassign | Driver reports unavailable pre-duty, but the candidate pool is completely exhausted (no other eligible drivers in branch or seller pool). | Previous driver is deactivated; duty transitions to `UNASSIGNED`; an escalated `WARNING` operations alert is emitted. Order is **NOT cancelled**. |
| 5 | Post-Duty Reassign | Driver crashes vehicle with garments in transit (`duty.status == IN_PROGRESS`); dispatcher tries calling automated reassignment. | System rejects automated reassignment. Requires explicit manual dispatcher intervention (`POST /api/v1/logistics/duties/{duty_id}/reassign`) with mandatory reason. |
| 6 | Late Duty Start | Scheduled window start was 08:00 AM; current time is 08:31 AM (threshold 30 mins); duty remains in `ASSIGNED`. | System emits `CRITICAL` operations alert `LATE_DUTY_START`. System does **NOT** automatically reassign. |
| 7 | Manual Reassign | Dispatcher submits manual reassignment with `reason: ""` or `reason: "   "`. | Endpoint returns HTTP 422 Unprocessable Entity (`reassignment_reason cannot be empty or whitespace`). Transaction rejected. |
| 8 | Notification | SMS provider returns HTTP 504 Gateway Timeout during assignment notification dispatch. | Assignment transaction commits successfully in PostgreSQL. Notification failure is captured in retry queue; assignment is **never rolled back**. |
| 9 | Cross-Tenant | Seller A staff user submits manual reassignment request specifying a `driver_id` owned by Seller B. | Endpoint rejects with HTTP 404 Not Found or HTTP 403 Forbidden. Cross-tenant assignment blocked. |
| 10 | Concurrency | Two dispatcher users simultaneously click "Assign Driver" for the same unassigned duty within 5 milliseconds. | PostgreSQL `SELECT ... FOR UPDATE` row lock blocks the second transaction until the first commits. Second transaction detects duty is already `ASSIGNED` and returns HTTP 409 Conflict. |
| 11 | Payment Decoupling | Order is in `CONFIRMED` state; customer has not made any payment. | Automatic or manual driver assignment succeeds completely. Decoupled from payment. |
| 12 | Driver Operational View | Driver A was assigned to Duty 101. Dispatcher reassigns Duty 101 to Driver B. Driver A refreshes mobile app. | Duty 101 is completely gone from Driver A's active duties feed. Operational access revoked. Driver A receives a "Duty Reassigned" push notification. |

---

## 6. Recommendation for Feature Inventory & Milestones

To execute Phase 8 in alignment with orchestrator and engineering tracks, we recommend structuring the work into five focused milestones:

### 6.1 Recommended Milestones

```
M1: Logistics & Driver Domain Models, Compliance & Alembic Migration
    ├── DriverProfile, DriverVehicle, DriverCompliance models
    ├── DriverDuty, DutyAssignmentHistory models
    ├── Alembic migration adding tables, indices, and foreign keys
    └── RBAC permissions registration (driver.read, driver.manage, logistics.assign, logistics.reassign)

M2: Deterministic 4-Tier Familiarity Algorithm & Eligibility Engine
    ├── Binary eligibility filter (active, on-duty, compliance validity, max capacity)
    ├── 4-Tier scoring engine (Address Familiarity > Customer Familiarity > Workload > Distance)
    ├── Deterministic tie-breaking logic
    └── Concurrency-safe assignment service with PostgreSQL row-locking (SELECT ... FOR UPDATE)

M3: Reassignment & Unavailability State Machine (Pre-Duty vs Post-Duty)
    ├── Manual reassignment endpoint with mandatory reason validation
    ├── Pre-duty unavailability automatic reassignment engine
    ├── Post-duty unavailability emergency freeze & critical alert handler
    ├── Late start SLA monitor
    └── Append-only assignment audit logging & operational access revocation

M4: Multi-Channel Resilient Notification Engine
    ├── Customer notification payload formatter (driver name, vehicle plate, actual phone)
    ├── Driver assignment and reassignment notification dispatchers
    ├── Non-blocking execution decoupling (assignment never rolled back on notification error)
    ├── Retry queue mechanism with exponential backoff
    └── Configurable channel matrix (Push, In-App, SMS, WhatsApp)

M5: Security, Tenant Isolation & E2E Verification
    ├── Strict tenant/seller isolation enforcement across all logistics endpoints
    ├── Payment decoupling validation
    ├── Comprehensive opaque-box test suites (Tiers 1–4)
    └── Monorepo CI verification (pytest, alembic upgrade, linting, typechecking)
```

---

## 7. Formal 5-Component Handoff Report

### 7.1 Observation
- **`ORIGINAL_REQUEST.md` (lines 125–164)**:
  - Line 133: "Implement the finalized TTC business decisions regarding Driver Assignment, Reassignment, and Notification behaviors (Q51–Q100)."
  - Line 141: "Implement automatic and manual driver assignment logic based on strict eligibility rules (active, authorized, available, compliance valid). Do not use an accept/reject workflow; assignment is authoritative. Driver preference must follow the established priority order (exact address familiarity > customer familiarity > workload > distance). Implement concurrency-safe assignment logic using PostgreSQL locking, ensuring exactly one active driver at a time."
  - Line 144–147: "If a driver is unavailable **before** duty starts: Automatically attempt reassignment to another eligible driver and alert operations. If a driver is unavailable **after** duty starts, or fails to start on time: Do not automatically reassign; trigger an operations alert requiring manual intervention. Preserve an auditable assignment history; historical drivers are no longer operationally active."
  - Line 150–151: "Implement immediate notification delivery upon assignment/reassignment. Provide the customer with the active driver's name, vehicle details, and actual phone number. Do not roll back or cancel an assignment due to a notification delivery failure; use retry mechanisms instead. Support configurable notification channels (Push, In-App, SMS, WhatsApp)..."
  - Line 153–154: "Enforce strict tenant/seller isolation... Do not equate driver assignment eligibility with full payment unless configured... shared platform infrastructure and single driver app (ADR-009); do not build seller-specific custom apps or distributed infrastructure (Kafka/Redis)..."
- **`docs/decisions/ADR-009-shared-driver-application.md` (lines 6–10)**:
  - "Provide one shared driver application branded under The Textile Care Driver. Driver workflows are cross-tenant and should not be duplicated across seller-specific repositories."
- **`docs/architecture/order-domain.md` & `backend/app/models/pickup.py`**:
  - `OrderPickup` manages physical garment collection (`SCHEDULED`, `DETAILS_SUBMITTED`, `APPROVED`, `REJECTED`, `COMPLETED`).
  - Payment is triggered solely upon customer approval of pickup details; hence, driver pickup assignment occurs while payment is pending.
- **`backend/app/models/customer.py` (lines 79–80)**:
  - Customer addresses record `latitude` and `longitude` (`Numeric(10, 7)`), providing coordinates for distance and familiarity calculations.
- **`backend/app/models/seller.py` (lines 78–79)**:
  - Seller branches record `latitude` and `longitude` (`float`), providing base coordinates for branch logistics.

### 7.2 Logic Chain
1. *From R1 specification*: Drivers cannot reject dispatches. Therefore, assignment is authoritative and binding immediately upon committing the database transaction.
2. *From Q51–Q60 & R1*: Eligibility requires active operational status, active shift (`is_on_duty`), unexpired verified compliance documents, and active duties below `max_active_duties`. Disqualified candidates must be pruned before scoring.
3. *From Q71–Q76 & R1*: The 4-tier priority hierarchy (Exact Address Familiarity $\succ$ Customer Familiarity $\succ$ Workload $\succ$ Distance) must be evaluated deterministically. Exact address familiarity is the primary sort key, followed by customer familiarity, followed by ascending workload, followed by ascending distance, with registration date as tie-breaker.
4. *From Q64–Q65 & R1*: High-concurrency operations (e.g. concurrent dispatchers) could cause double-assignment races. PostgreSQL row-level locks (`SELECT ... FOR UPDATE`) on the duty record serialize mutations and ensure exactly one active assignment exists.
5. *From Q83–Q87 & R2*: When a driver becomes unavailable pre-duty, garments are not at risk, allowing automated re-running of the priority algorithm. Post-duty (or after late start SLA breach), physical custody of garments or real-time location is uncertain; automated reassignment could create catastrophic operational divergence. Therefore, post-duty unavailability strictly requires manual dispatcher intervention and critical alerts.
6. *From Q88–Q89 & R2*: Replaced drivers must immediately lose visibility of the customer's order and address to protect customer privacy and prevent duplicate pickups.
7. *From Q91–Q94 & R3*: The customer requires the driver's name, vehicle plate, and actual phone number. If notification delivery fails (e.g. SMS provider error), rolling back the assignment would cancel an authorized dispatch. Therefore, notification dispatch must be decoupled from the assignment transaction.
8. *From Q99–Q100 & R4*: Multi-tenancy is enforced via `TenantContext`. In accordance with ADR-009, all driver interactions occur via the shared driver app, without external message brokers.

### 7.3 Caveats
- **Live GPS Tracking**: Real-time continuous GPS telemetry streaming (e.g. WebSockets / MQTT) is not part of this checkpoint; distance calculation relies on driver's last known branch/static coordinates or latest reported position.
- **External SMS/WhatsApp Providers**: Actual live SMS/WhatsApp provider API keys are mockable/configurable interfaces in local development and testing environments; resilient retry queues and error-handling behavior must be verified via unit/e2e test doubles.

### 7.4 Conclusion
The specifications for TTC Driver Assignment, Reassignment, and Notifications (Q51–Q100, R1–R4) are fully mapped, verified against existing monorepo architecture, and ready for decomposition into milestones M1 through M5. All business invariants, priority algorithms, failure handling semantics, and edge cases have been exhaustively documented.

### 7.5 Verification Method
To independently verify this specification report and validate the findings:
1. **Inspect Authoritative Requirements**:
   ```bash
   cat /workspaces/TheTextileCare/.agents/ORIGINAL_REQUEST.md
   cat /workspaces/TheTextileCare/.agents/survey_spec_miner_1/DISPATCH.md
   cat /workspaces/TheTextileCare/docs/decisions/ADR-009-shared-driver-application.md
   ```
2. **Inspect Existing Database Models**:
   ```bash
   # Review existing pickup model and lack of driver fields
   head -n 50 /workspaces/TheTextileCare/backend/app/models/pickup.py
   # Review customer address coordinate support
   grep -n "latitude" /workspaces/TheTextileCare/backend/app/models/customer.py
   grep -n "latitude" /workspaces/TheTextileCare/backend/app/models/seller.py
   ```
3. **Validate Proposed Architecture Against Invariants**:
   - Verify authoritative dispatch has no driver accept/reject states.
   - Verify 4-tier sorting order: Address Familiarity > Customer Familiarity > Workload > Distance.
   - Verify pre-duty auto-reassignment vs post-duty manual-only intervention.
   - Verify customer payload includes actual phone number and vehicle details.
   - Verify assignment transaction does not rollback on notification failures.
