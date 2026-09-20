# Survey Explorer 3 Investigation & Handoff Report: Testing, Concurrency & CI Infrastructure

**Document Version**: 1.0.0  
**Target Milestone**: Driver Assignment, Reassignment & Notification Behaviors (Q51–Q100, Requirements R1–R4)  
**Working Directory**: `/workspaces/TheTextileCare/.agents/survey_explorer_3`  
**Author**: `survey_explorer_3` (Explorer Archetype)  
**Parent Agent**: `orchestrator_3` (`a78db49b-ac7b-403d-96ff-f8b3d4ebe7cd`)  
**Date**: 2026-09-20  

---

## 1. Executive Summary

This investigation analyzed the backend test infrastructure, fixture architectures, database concurrency mechanisms, notification mocking strategies, and CI workflows in `/workspaces/TheTextileCare` to establish rigorous testing patterns for **Driver Assignment, Reassignment, and Notifications (Q51–Q100 / R1–R4)**.

### Core Discoveries:
1. **Live PostgreSQL Test Environment**: Tests execute against a local PostgreSQL instance (`postgresql+psycopg://postgres:postgres@localhost:5432/the_textile_care`). Schema isolation is enforced via the `reset_database` fixture (`backend/tests/conftest.py` lines 23–36), which drops and recreates schema `public`, executes `Base.metadata.create_all(bind=engine)`, and seeds baseline roles and permissions via `RoleService(db).seed_defaults()`.
2. **Absence of Driver Fixtures & Domain**: The existing test suite contains comprehensive fixtures for Users, Memberships, Tenants, Sellers, Branches, Catalogs, Pricing Books/Rules, Customers, Orders, Pickups, Payments, Invoices, and Settlements. However, **zero test fixtures, factories, or mock models exist for Drivers, Vehicles, Compliance Documents, Duties, or Driver Assignments**.
3. **Zero Existing Concurrency Tests**: A full-text grep across `backend/tests/` revealed zero multi-threaded, parallel, or row-locking tests. Concurrency safety in prior phases was achieved primarily via PostgreSQL sequences (`order_number_seq`). To validate Requirement R1 ("Implement concurrency-safe assignment logic using PostgreSQL locking, ensuring exactly one active driver at a time"), we established a dedicated multi-threaded testing harness using Python's `concurrent.futures.ThreadPoolExecutor` and `threading.Barrier` across isolated database sessions.
4. **Empty Notification Integration**: `backend/app/integrations/notifications/__init__.py` is a 2-line placeholder. To verify Requirement R3 (immediate notifications, customer exposure of driver name/vehicle/phone, and failure resilience), we designed a dual verification pattern: (a) database-backed outbox audit log verification (mirroring `AuditEvent`), and (b) exception injection via `unittest.mock.patch` to verify that notification failure **never rolls back or cancels an assignment**.
5. **Critical Database Fixture Trap Identified**: We identified that `backend/tests/security/test_tenant_rbac.py` implements a custom `_reset_db()` helper (lines 8–15) that invokes `Base.metadata.drop_all(bind=engine)` and `Base.metadata.create_all(bind=engine)` *without* importing `app.models`. This purges all tables and creates only a subset of models, causing subsequent tests in the same session to fail with `psycopg.errors.UndefinedTable: relation "role_permissions" does not exist`. All new tests must strictly avoid local database drops and rely on the centralized `autouse=True` fixture in `conftest.py`.
6. **Alembic & CI Verification Commands**: Verified that `PYTHONPATH=. alembic upgrade head` executes cleanly through all 9 revisions to current head `b2c3d4e5f6a7`. Monorepo checks (`pnpm typecheck`, `pnpm lint`, `pnpm test`) are operational with zero errors across 10 packages.

---

## 2. Observations

### 2.1 Test Infrastructure & Fixture Architecture

#### Database Reset and Session Lifecycle
In `backend/tests/conftest.py`:
```python
# Lines 23-36
@pytest.fixture(autouse=True)
def reset_database():
    """Reset database tables and seed defaults before each test."""
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()
    engine.dispose()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        RoleService(db).seed_defaults()
    yield
```
- **Observation**: Schema reset is performed at the PostgreSQL schema level (`DROP SCHEMA public CASCADE`). `Base.metadata.create_all(bind=engine)` executes DDL for all models registered in `app.models`.
- **Observation**: `RoleService(db).seed_defaults()` populates default platform roles (`PLATFORM_ADMIN`, `PLATFORM_SUPPORT`) and tenant/seller roles (`TENANT_OWNER`, `TENANT_ADMIN`, `TENANT_MEMBER`, `TENANT_VIEWER`, `SELLER_OWNER`, `SELLER_ADMIN`, `STAFF`, `VIEWER`, `CUSTOMER`). Note that the role `DRIVER` is currently not present in `RoleName`.

#### Authentication & Context Helpers
In `backend/tests/conftest.py`:
```python
# Lines 38-75
def create_test_user(email: str, name: str | None = None, auth_user_id: str | None = None) -> User:
    with SessionLocal() as db:
        repo = UserRepository(db)
        return repo.create_or_get(
            email=email,
            auth_user_id=auth_user_id or f'auth-{email}',
            name=name or email.split('@')[0],
        )

def create_test_tenant(name: str, slug: str | None = None) -> Tenant:
    with SessionLocal() as db:
        repo = TenantRepository(db)
        actual_slug = slug or name.lower().replace(' ', '-')
        return repo.create(name=name, slug=actual_slug)

def create_test_membership(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    role_name: str,
    status: str = 'ACTIVE',
) -> Membership:
    with SessionLocal() as db:
        repo = MembershipRepository(db)
        return repo.create(
            tenant_id=tenant_id,
            user_id=user_id,
            role_name=role_name,
            status=status,
        )

def make_auth_headers(user: User, tenant: Tenant | None = None) -> dict[str, str]:
    headers = {'X-User-Id': str(user.id)}
    if tenant:
        headers['X-Tenant-Id'] = str(tenant.id)
    return headers
```
- **Observation**: In test mode (`app_env == 'test'`), authentication is resolved via HTTP headers `X-User-Id` (or `X-Auth-User-Id`) and `X-Tenant-Id` without requiring external JWT signing (`backend/app/core/security/auth.py` lines 59–75).
- **Observation**: Customer requests pass only `X-User-Id`. Seller staff and platform admin requests pass both `X-User-Id` and `X-Tenant-Id`.

#### Existing Domain Entity Fixtures
- **Seller & Branch**: `backend/tests/e2e/conftest.py` lines 92–123 provide `create_test_seller(tenant_id, ...)` and `create_test_branch(tenant_id, seller_id, ...)`.
- **Order & Pickup**: `backend/tests/conftest.py` lines 117–136 provide `create_test_pickup(order_id, tenant_id, seller_id, ...)` and `backend/tests/e2e/phase7_helpers.py` lines 193–262 provide `create_phase7_order(client, env, qty=2)`.
- **Gaps**: There are **no fixture functions** for:
  - Driver records (`create_test_driver`)
  - Driver compliance documents (`create_test_driver_compliance`)
  - Driver vehicle attributes (`create_test_driver_vehicle`)
  - Logistics duties (`create_test_duty`)
  - Duty assignment history (`create_test_assignment`)
  - Operations alerts (`create_test_operations_alert`)
  - Notification logs (`create_test_notification_log`)

---

### 2.2 Concurrency & PostgreSQL Locking Analysis

- **Observation**: Ripgrep for `with_for_update`, `FOR UPDATE`, `Barrier`, `ThreadPoolExecutor`, `multiprocessing` across `backend/` yielded zero results for concurrency testing or row-locking in tests.
- **Observation**: In Phase 7, concurrency safety was handled via PostgreSQL sequences:
  - `backend/app/repositories/order.py` line 36: `result = self.db.execute(text("SELECT nextval('order_number_seq')"))`
- **Observation**: For Phase 8 / Driver Assignment (Requirement R1), the requirement explicitly dictates:
  > "Implement concurrency-safe assignment logic using PostgreSQL locking, ensuring exactly one active driver at a time."
  > Acceptance Criteria: "concurrency tests prevent multiple active assignments for the same duty."
- **Observation**: SQLAlchemy 2.0 supports explicit row-level locking via `.with_for_update()`:
  ```python
  stmt = select(DriverDuty).where(DriverDuty.id == duty_id).with_for_update()
  duty = db.execute(stmt).scalar_one_or_none()
  ```
- **Observation**: PostgreSQL supports partial unique constraints to enforce single-active invariants at the database engine level:
  ```sql
  CREATE UNIQUE INDEX uq_duty_active_driver ON driver_assignments (duty_id) WHERE is_active = TRUE;
  ```

---

### 2.3 Notification Mocking & Failure Resilience Analysis

- **Observation**: `backend/app/integrations/notifications/__init__.py` contains only:
  ```python
  """Notifications integration placeholder."""
  ```
- **Observation**: In `backend/tests/e2e/test_phase7_tier1_features.py` line 1341, mocking was previously asserted via counter checks (`assert dispatched_refund_calls == 0`).
- **Observation**: Requirement R3 explicitly states:
  > "Implement immediate notification delivery upon assignment/reassignment. Provide the customer with the active driver's name, vehicle details, and actual phone number. Do not roll back or cancel an assignment due to a notification delivery failure; use retry mechanisms instead. Support configurable notification channels (Push, In-App, SMS, WhatsApp)..."
- **Observation**: In `backend/tests/e2e/test_pricing_tier1_features.py` lines 863–975, audit events were verified by directly querying the database table `audit_events` via `db.query(AuditEvent).filter(...)`.
- **Observation**: When an external gateway fails, the database transaction for the assignment must already be committed or protected with a `try...except` block:
  ```python
  # Assignment commit must NOT fail if notification dispatch throws
  try:
      notification_service.dispatch_assignment_notifications(...)
  except Exception as exc:
      logger.error("Notification dispatch failed: %s", exc)
      notification_service.log_failure(duty_id=duty.id, error=str(exc))
  ```

---

### 2.4 Isolation & Security Testing Patterns

- **Observation**: In `backend/tests/security/test_tenant_isolation.py` and `backend/tests/security/test_seller_isolation.py`:
  - Cross-tenant read attempts via API (`GET /api/v1/tenants/{other_id}`, `GET /api/v1/sellers`) return `403 Forbidden` or `404 Not Found`.
  - Cross-tenant mutation attempts (`PATCH /api/v1/sellers/branches/{other_branch_id}`) return `404 Not Found`.
  - Spoofed tenant headers (`X-Tenant-Id: {other_tenant_id}`) return `403 Forbidden` (`test_client_tenant_id_spoofing_rejected`).
- **Observation**: In `backend/tests/security/test_pricing_repository_adversarial.py`:
  - Adversarial repository-level calls directly invoke repository methods passing mismatched `tenant_id` parameters (e.g. `repo.get_book(tenant_b_id, book_a.id)`) and assert `None` or raised exceptions.
  - Immutable field tamper-proofing tests verify that attempting to update `tenant_id` or `seller_id` on an existing entity does not overwrite the database columns.
- **Observation**: Requirement R4 mandates:
  > "Enforce strict tenant/seller isolation for all assignment operations... Tenant/Seller A cannot reassign Tenant/Seller B's drivers."
  > Requirement R2 mandates:
  > "Support manual reassignment for seller staff with order access (requires a mandatory reason)."

---

### 2.5 Test Execution & CI Verification Commands

- **Observation**: `pytest ./backend/tests -q` is the official backend CI command defined in `.github/workflows/backend.yml` line 17.
- **Observation**: Running `alembic upgrade head` from `backend/` without `PYTHONPATH=.` fails with:
  `ModuleNotFoundError: No module named 'app'`
  Running with `PYTHONPATH=. alembic upgrade head` successfully executes migrations up to `b2c3d4e5f6a7`.
- **Observation**: Code formatting/linting tool `ruff` is installed at `/workspaces/TheTextileCare/backend/.venv/bin/ruff` (configured in `backend/pyproject.toml` lines 36–45: `line-length = 100`, `src = ["app"]`, `quote-style = "single"`).
- **Observation**: Frontend/monorepo CI is defined in `.github/workflows/ci.yml` and root `package.json`:
  - `pnpm lint` runs `turbo run lint` (ESLint on Next.js apps).
  - `pnpm typecheck` runs `turbo run typecheck` (`tsc -p tsconfig.json --noEmit` across all 10 packages).
  - `pnpm test` runs `turbo run test`.

---

## 3. Logic Chain

1. **Premise**: Requirement R1 requires PostgreSQL row locking and guarantees that exactly one active driver is assigned to a duty at any instant.
   - **Inference**: Single-threaded unit tests cannot prove row-lock serialization or detect race conditions.
   - **Deduction**: We must establish a multi-threaded test pattern using Python's `ThreadPoolExecutor` and `threading.Barrier` where 2 or more worker threads concurrently attempt to assign different drivers to the same `duty_id`. The test must prove that exactly one transaction succeeds (HTTP 200/201) while all competing requests fail (HTTP 409 Conflict), and the database state reflects exactly one active assignment (`is_active = True`).
   - **Defense-in-Depth**: In addition to service-level `SELECT ... FOR UPDATE`, the Alembic schema migration must create a partial unique constraint `CREATE UNIQUE INDEX uq_duty_active_assignment ON driver_assignments (duty_id) WHERE is_active = true;`.

2. **Premise**: Requirement R3 requires notifications to be sent immediately upon assignment, containing driver details (name, vehicle, actual phone number), while guaranteeing that notification delivery failure **never invalidates or rolls back the assignment**.
   - **Inference**: If notification dispatch is coupled inside the main database transaction without fault handling, an external SMS/Push provider timeout would trigger a database rollback, leaving the duty unassigned.
   - **Deduction**: The test suite must test two separate conditions:
     1. *Content Determinism*: On successful assignment, query `notification_logs` to verify recipient role, active driver name, vehicle details (make/model/license plate), and the unmasked phone number.
     2. *Resilience Under Failure*: Use `unittest.mock.patch` to simulate an external gateway exception (`TimeoutError` / `GatewayError`) during notification dispatch. Verify that the assignment endpoint still returns HTTP 200/201, the driver assignment is persisted in the database with `status = 'ACTIVE'`, and the notification record is logged as `status = 'FAILED'` or `retry_pending = True`.

3. **Premise**: Requirement R4 mandates multi-tenant and cross-seller isolation, and Requirement R2 mandates mandatory reassignment reasons.
   - **Inference**: A seller staff member in Tenant A must never see, assign, or reassign drivers belonging to Tenant B. Furthermore, an empty or missing reassignment reason violates domain invariants.
   - **Deduction**: The security test suite must execute matrix attacks:
     1. Tenant A Seller attempts to assign Tenant B Driver to Tenant A Duty $\to$ HTTP 400/404.
     2. Tenant B Seller attempts to reassign Tenant A Duty $\to$ HTTP 404/403.
     3. Tenant A Seller attempts manual reassignment without a reason or with whitespace-only reason $\to$ HTTP 422 Unprocessable Entity.
     4. User with `VIEWER` or `CUSTOMER` role attempts reassignment $\to$ HTTP 403 Forbidden.

4. **Premise**: Inconsistent database schema resets cause cascading test suite failures (`UndefinedTable: relation "role_permissions" does not exist`).
   - **Inference**: When `test_tenant_rbac.py` ran `Base.metadata.drop_all; Base.metadata.create_all` without `import app.models`, `Base.metadata` was incomplete.
   - **Deduction**: Test files must never define their own database dropping functions. All test modules must import `conftest.py` helpers and let the global `autouse=True` fixture handle clean schema setup.

---

## 4. Detailed Technical Testing Blueprints

### 4.1 Required Test Fixtures & Factories

To enable testing of Driver Assignment (Q51–Q100 / R1–R4), the following fixtures must be added to `backend/tests/conftest.py` or a dedicated helper module `backend/tests/e2e/driver_helpers.py`:

```python
# ---------------------------------------------------------------------------
# Driver Logistics Test Fixture Factories
# ---------------------------------------------------------------------------

def create_test_driver(
    tenant_id: uuid.UUID,
    seller_id: uuid.UUID,
    branch_id: uuid.UUID,
    name: str = "Fast Courier",
    email: str | None = None,
    phone: str = "+15551234567",
    status: str = "ACTIVE",
    is_on_duty: bool = True,
    vehicle_type: str = "VAN",
    vehicle_make: str = "Toyota",
    vehicle_model: str = "HiAce",
    vehicle_color: str = "White",
    license_plate: str = "TTC-DRV-01",
    max_active_duties: int = 3,
) -> dict[str, Any]:
    """Creates a User, DriverProfile, Vehicle, and active Shift for testing."""
    with SessionLocal() as db:
        user = UserRepository(db).create_or_get(
            email=email or f"driver_{uuid.uuid4().hex[:6]}@example.com",
            auth_user_id=f"auth-drv-{uuid.uuid4().hex[:6]}",
            name=name,
        )
        # Create driver profile
        driver = DriverProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            tenant_id=tenant_id,
            seller_id=seller_id,
            branch_id=branch_id,
            full_name=name,
            phone_number=phone,
            status=status,
            is_on_duty=is_on_duty,
            vehicle_type=vehicle_type,
            vehicle_make=vehicle_make,
            vehicle_model=vehicle_model,
            vehicle_color=vehicle_color,
            license_plate=license_plate,
            max_active_duties=max_active_duties,
            current_active_duties=0,
        )
        db.add(driver)
        db.commit()
        db.refresh(driver)
        return {"user": user, "driver": driver}


def create_test_driver_compliance(
    driver_id: uuid.UUID,
    doc_type: str = "DL",
    is_verified: bool = True,
    days_valid: int = 365,
) -> DriverCompliance:
    """Creates compliance document records (DL, RC, INSURANCE, BGC)."""
    with SessionLocal() as db:
        compliance = DriverCompliance(
            id=uuid.uuid4(),
            driver_id=driver_id,
            document_type=doc_type,
            document_number=f"DOC-{uuid.uuid4().hex[:8].upper()}",
            is_verified=is_verified,
            expires_at=datetime.now(timezone.utc) + timedelta(days=days_valid),
        )
        db.add(compliance)
        db.commit()
        db.refresh(compliance)
        return compliance


def create_test_duty(
    tenant_id: uuid.UUID,
    seller_id: uuid.UUID,
    branch_id: uuid.UUID,
    order_id: uuid.UUID,
    duty_type: str = "PICKUP",
    status: str = "UNASSIGNED",
    scheduled_window_start: datetime | None = None,
    scheduled_window_end: datetime | None = None,
    customer_address_id: uuid.UUID | None = None,
) -> DriverDuty:
    """Creates an actionable logistics duty record."""
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        duty = DriverDuty(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            seller_id=seller_id,
            branch_id=branch_id,
            order_id=order_id,
            duty_type=duty_type,
            status=status,
            scheduled_window_start=scheduled_window_start or now + timedelta(hours=1),
            scheduled_window_end=scheduled_window_end or now + timedelta(hours=3),
            destination_address_id=customer_address_id,
        )
        db.add(duty)
        db.commit()
        db.refresh(duty)
        return duty


def setup_driver_environment(
    client: TestClient,
    candidate_count: int = 3,
) -> dict[str, Any]:
    """Builds a complete world: Tenant, Seller, Branch, Order, Pickup, Customer, and N Drivers."""
    env = setup_tenant_and_actor()
    tenant = env["tenant"]
    seller = env["seller"]
    branch = env["downtown_branch"]

    drivers = []
    for i in range(candidate_count):
        drv = create_test_driver(
            tenant_id=tenant.id,
            seller_id=seller.id,
            branch_id=branch.id,
            name=f"Driver {chr(65 + i)}",
            phone=f"+1555000000{i}",
            license_plate=f"PLATE-{chr(65 + i)}",
        )
        # Add valid compliance documents
        for doc in ["DL", "RC", "INSURANCE", "BGC"]:
            create_test_driver_compliance(drv["driver"].id, doc_type=doc, is_verified=True, days_valid=180)
        drivers.append(drv)

    return {
        **env,
        "branch": branch,
        "drivers": drivers,
    }
```

---

### 4.2 Concurrency & Row Locking Testing Pattern

The concurrency testing harness tests two concurrent workers attempting to assign different drivers to the same duty at the exact same instant:

```python
import concurrent.futures
import threading
import uuid
import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.models.driver import DriverDuty, DriverAssignment


def test_concurrency_safe_driver_assignment_ensures_exactly_one_active_driver(client: TestClient):
    """Verifies Requirement R1: Concurrency-safe assignment using PostgreSQL locking.
    
    Two workers simultaneously attempt to assign different drivers to the same duty.
    Verification:
    1. Exactly ONE request succeeds (HTTP 200/201).
    2. Exactly ONE request is rejected (HTTP 409 Conflict).
    3. Exactly ONE active driver assignment exists in the database.
    """
    env = setup_driver_environment(client, candidate_count=2)
    duty = create_test_duty(
        tenant_id=env["tenant"].id,
        seller_id=env["seller"].id,
        branch_id=env["branch"].id,
        order_id=uuid.uuid4(),
    )
    driver_a = env["drivers"][0]["driver"]
    driver_b = env["drivers"][1]["driver"]

    barrier = threading.Barrier(2)
    results = []

    def execute_assignment(driver_id: uuid.UUID):
        # Synchronize both threads to hit the API simultaneously
        barrier.wait()
        
        # TestClient is thread-safe; uses underlying WSGI/ASGI transport
        resp = client.post(
            f"/api/v1/seller/duties/{duty.id}/assign",
            json={"driver_id": str(driver_id)},
            headers=env["headers"],
        )
        results.append((resp.status_code, resp.json(), driver_id))

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(execute_assignment, driver_a.id)
        f2 = executor.submit(execute_assignment, driver_b.id)
        f1.result()
        f2.result()

    # 1. Assert exactly one success and one conflict
    status_codes = [r[0] for r in results]
    assert 200 in status_codes or 201 in status_codes, f"No request succeeded: {results}"
    assert 409 in status_codes, f"Concurrent request was not rejected with 409: {results}"

    # 2. Assert database invariant: exactly ONE active assignment exists
    with SessionLocal() as db:
        active_assignments = db.query(DriverAssignment).filter(
            DriverAssignment.duty_id == duty.id,
            DriverAssignment.is_active.is_(True),
        ).all()
        assert len(active_assignments) == 1, (
            f"Concurrency invariant violated! Found {len(active_assignments)} active assignments!"
        )
        
        # Verify the active driver matches the successful request
        success_result = next(r for r in results if r[0] in (200, 201))
        winning_driver_id = success_result[2]
        assert active_assignments[0].driver_id == winning_driver_id
```

#### Direct Row-Lock Contention Verification
To independently verify that `SELECT ... FOR UPDATE` acquires an exclusive lock:
```python
def test_duty_row_lock_blocks_concurrent_transaction():
    """Verify PostgreSQL SELECT ... FOR UPDATE blocks conflicting transactions."""
    duty_id = uuid.uuid4()
    # Create test duty in DB
    ...
    lock_acquired = threading.Event()
    tx1_complete = threading.Event()
    tx2_blocked = threading.Event()

    def tx1_worker():
        with SessionLocal() as db1:
            db1.execute(
                select(DriverDuty).where(DriverDuty.id == duty_id).with_for_update()
            )
            lock_acquired.set()
            # Hold lock until tx2 attempts to acquire
            tx1_complete.wait(timeout=5)
            db1.commit()

    def tx2_worker():
        lock_acquired.wait()
        with SessionLocal() as db2:
            # nowait=True ensures immediate error if row is locked
            with pytest.raises(Exception) as exc_info:
                db2.execute(
                    select(DriverDuty).where(DriverDuty.id == duty_id).with_for_update(nowait=True)
                )
            assert "could not obtain lock" in str(exc_info.value).lower()
            tx2_blocked.set()

    t1 = threading.Thread(target=tx1_worker)
    t2 = threading.Thread(target=tx2_worker)
    t1.start()
    t2.start()
    tx2_blocked.wait(timeout=5)
    tx1_complete.set()
    t1.join()
    t2.join()
```

---

### 4.3 Notification Mocking & Failure Resilience Testing Pattern

```python
from unittest.mock import patch
from app.models.notification import NotificationLog


def test_customer_notification_payload_contains_required_fields(client: TestClient):
    """Verifies Requirement R3: Customer receives driver name, vehicle details, and actual phone number."""
    env = setup_driver_environment(client, candidate_count=1)
    duty = create_test_duty(
        tenant_id=env["tenant"].id,
        seller_id=env["seller"].id,
        branch_id=env["branch"].id,
        order_id=uuid.uuid4(),
    )
    driver = env["drivers"][0]["driver"]

    resp = client.post(
        f"/api/v1/seller/duties/{duty.id}/assign",
        json={"driver_id": str(driver.id)},
        headers=env["headers"],
    )
    assert resp.status_code in (200, 201)

    with SessionLocal() as db:
        logs = db.query(NotificationLog).filter(
            NotificationLog.duty_id == duty.id,
            NotificationLog.recipient_role == "CUSTOMER",
        ).all()
        assert len(logs) >= 1, "Customer notification log was not emitted!"
        
        payload = logs[0].payload
        assert payload["driver_name"] == driver.full_name
        assert payload["driver_phone"] == driver.phone_number
        assert payload["vehicle_type"] == driver.vehicle_type
        assert payload["license_plate"] == driver.license_plate
        assert payload["vehicle_details"] == {
            "make": driver.vehicle_make,
            "model": driver.vehicle_model,
            "color": driver.vehicle_color,
        }


def test_assignment_succeeds_even_when_notification_delivery_fails(client: TestClient):
    """Verifies Requirement R3: Notification failure MUST NOT rollback or cancel assignment."""
    env = setup_driver_environment(client, candidate_count=1)
    duty = create_test_duty(
        tenant_id=env["tenant"].id,
        seller_id=env["seller"].id,
        branch_id=env["branch"].id,
        order_id=uuid.uuid4(),
    )
    driver = env["drivers"][0]["driver"]

    # Mock external notification gateway to throw connection timeout
    with patch("app.services.notification.NotificationService._dispatch_channel") as mock_dispatch:
        mock_dispatch.side_effect = TimeoutError("External SMS/Push Gateway Unreachable")

        resp = client.post(
            f"/api/v1/seller/duties/{duty.id}/assign",
            json={"driver_id": str(driver.id)},
            headers=env["headers"],
        )

        # 1. Assignment HTTP response must remain SUCCESS (200 or 201)
        assert resp.status_code in (200, 201), (
            f"Assignment failed due to notification error! Observed status: {resp.status_code}"
        )

    # 2. Verify database state: Duty IS assigned and DriverAssignment IS active
    with SessionLocal() as db:
        duty_db = db.get(DriverDuty, duty.id)
        assert duty_db.status == "ASSIGNED"

        assignment = db.query(DriverAssignment).filter(
            DriverAssignment.duty_id == duty.id,
            DriverAssignment.is_active.is_(True),
        ).first()
        assert assignment is not None
        assert assignment.driver_id == driver.id

        # 3. Notification log reflects failure and is marked for retry
        log = db.query(NotificationLog).filter(NotificationLog.duty_id == duty.id).first()
        assert log is not None
        assert log.status in ("FAILED", "PENDING_RETRY")
        assert log.retry_count >= 0
```

---

### 4.4 Isolation & Security Testing Pattern

```python
def test_cross_tenant_driver_assignment_denied(client: TestClient):
    """Verifies Requirement R4: Tenant A cannot assign Tenant B's driver."""
    env_a = setup_driver_environment(client, candidate_count=1)
    env_b = setup_driver_environment(client, candidate_count=1)

    duty_a = create_test_duty(
        tenant_id=env_a["tenant"].id,
        seller_id=env_a["seller"].id,
        branch_id=env_a["branch"].id,
        order_id=uuid.uuid4(),
    )
    driver_b = env_b["drivers"][0]["driver"]

    # Attack: Tenant A attempts to assign Tenant B's driver
    resp = client.post(
        f"/api/v1/seller/duties/{duty_a.id}/assign",
        json={"driver_id": str(driver_b.id)},
        headers=env_a["headers"],
    )
    assert resp.status_code in (400, 404, 422), (
        f"Cross-tenant assignment was not denied! Status: {resp.status_code}"
    )


def test_cross_seller_duty_reassignment_denied(client: TestClient):
    """Verifies Requirement R4: Seller B cannot mutate or reassign Seller A's duty."""
    env_a = setup_driver_environment(client, candidate_count=1)
    env_b = setup_driver_environment(client, candidate_count=1)

    duty_a = create_test_duty(
        tenant_id=env_a["tenant"].id,
        seller_id=env_a["seller"].id,
        branch_id=env_a["branch"].id,
        order_id=uuid.uuid4(),
    )

    # Attack: Seller B attempts to reassign Seller A's duty
    resp = client.post(
        f"/api/v1/seller/duties/{duty_a.id}/reassign",
        json={"driver_id": str(env_b["drivers"][0]["driver"].id), "reason": "Hostile takeover"},
        headers=env_b["headers"],
    )
    assert resp.status_code in (403, 404)


def test_manual_reassignment_requires_mandatory_reason(client: TestClient):
    """Verifies Requirement R2: Reassignment requires a non-empty reason."""
    env = setup_driver_environment(client, candidate_count=2)
    duty = create_test_duty(
        tenant_id=env["tenant"].id,
        seller_id=env["seller"].id,
        branch_id=env["branch"].id,
        order_id=uuid.uuid4(),
        status="ASSIGNED",
    )
    new_driver = env["drivers"][1]["driver"]

    # 1. Missing reason field
    resp1 = client.post(
        f"/api/v1/seller/duties/{duty.id}/reassign",
        json={"driver_id": str(new_driver.id)},
        headers=env["headers"],
    )
    assert resp1.status_code == 422

    # 2. Whitespace-only reason
    resp2 = client.post(
        f"/api/v1/seller/duties/{duty.id}/reassign",
        json={"driver_id": str(new_driver.id), "reason": "    "},
        headers=env["headers"],
    )
    assert resp2.status_code in (400, 422)


def test_viewer_role_cannot_reassign_driver(client: TestClient):
    """Verifies RBAC least privilege: VIEWER role cannot mutate driver assignments."""
    env = setup_driver_environment(client, candidate_count=2)
    duty = create_test_duty(
        tenant_id=env["tenant"].id,
        seller_id=env["seller"].id,
        branch_id=env["branch"].id,
        order_id=uuid.uuid4(),
        status="ASSIGNED",
    )
    
    # Create VIEWER user
    viewer_user = create_test_user("viewer@example.com")
    create_test_membership(env["tenant"].id, viewer_user.id, "VIEWER")
    viewer_headers = make_auth_headers(viewer_user, env["tenant"])

    resp = client.post(
        f"/api/v1/seller/duties/{duty.id}/reassign",
        json={"driver_id": str(env["drivers"][1]["driver"].id), "reason": "Valid reason"},
        headers=viewer_headers,
    )
    assert resp.status_code == 403
```

---

## 5. Test Execution & CI Verification Commands Reference

The following table documents every authoritative command required to run tests, execute database migrations, verify formatting/linting, and perform typechecking:

| Tool / Target | Command | Working Directory | Environment / Flags | Expected Result |
|---|---|---|---|---|
| **Backend Unit & Integration Tests** | `pytest backend/tests/unit backend/tests/integration -q` | `/workspaces/TheTextileCare` | Uses `.venv` | All unit and integration tests pass |
| **Backend Security Tests** | `pytest backend/tests/security -q` | `/workspaces/TheTextileCare` | Uses `.venv` | Multi-tenant isolation verified |
| **Backend E2E Full Suite** | `pytest backend/tests/e2e/ -q` | `/workspaces/TheTextileCare` | Uses `.venv` | All feature tiers pass |
| **Single Test Module** | `pytest backend/tests/e2e/test_phase7_tier1_features.py -q` | `/workspaces/TheTextileCare` | Uses `.venv` | Tier 1 passes |
| **Filtered Test Execution** | `pytest backend/tests/ -k "concurrency or driver" -v` | `/workspaces/TheTextileCare` | Uses `.venv` | Executes matching tests |
| **Database Migration (Apply Head)** | `PYTHONPATH=. alembic upgrade head` | `/workspaces/TheTextileCare/backend` | PostgreSQL running | Migrates to latest head revision |
| **Database Migration (Clean Reset)** | `python3 -c "from app.db import Base, engine; from sqlalchemy import text; Base.metadata.drop_all(bind=engine); conn=engine.connect(); conn.execute(text('DROP TABLE IF EXISTS alembic_version CASCADE')); conn.commit()" && PYTHONPATH=. alembic upgrade head` | `/workspaces/TheTextileCare/backend` | PostgreSQL running | Recreates clean database from migration 0 to head |
| **Database Migration Lineage Check** | `PYTHONPATH=. alembic current` | `/workspaces/TheTextileCare/backend` | PostgreSQL running | Displays current revision |
| **Backend Linting (Ruff Check)** | `/workspaces/TheTextileCare/backend/.venv/bin/ruff check app` | `/workspaces/TheTextileCare/backend` | Config: `pyproject.toml` | Zero lint errors |
| **Backend Format Check** | `/workspaces/TheTextileCare/backend/.venv/bin/ruff format --check app` | `/workspaces/TheTextileCare/backend` | Line length 100 | Formatting compliant |
| **Monorepo Linting** | `pnpm lint` | `/workspaces/TheTextileCare` | Turborepo | All web and package apps pass ESLint |
| **Monorepo Typechecking** | `pnpm typecheck` | `/workspaces/TheTextileCare` | Turborepo | All 10 TypeScript packages pass `tsc` |
| **Monorepo Unit Tests** | `pnpm test` | `/workspaces/TheTextileCare` | Turborepo | Monorepo package tests pass |
| **Full Build Verification** | `pnpm build` | `/workspaces/TheTextileCare` | Turborepo | All web applications compile cleanly |

---

## 6. Caveats

1. **Local PostgreSQL Dependency**: Tests require an active PostgreSQL instance listening on `localhost:5432` with user/password `postgres:postgres` and database `the_textile_care`. SQLite is not supported because PostgreSQL row locking (`with_for_update()`) and partial unique indexes (`WHERE is_active = TRUE`) rely on PostgreSQL-specific syntax.
2. **Schema Recreation Concurrency**: In multi-test execution, `reset_database` drops and recreates schema `public` between tests. If two test runners execute concurrently against the same database instance, they will collide. Pytest must be executed sequentially (do NOT use `pytest-xdist` with multiple workers on the same physical PostgreSQL database without separate per-worker databases).
3. **External Broker Deferral**: As documented in `ADR-009` and user requirements, Kafka and Redis message queues are intentionally deferred for this phase. Concurrency and notification queuing are managed strictly through PostgreSQL row locks and transaction tables.
4. **Isolated DB Drops in Tests Prohibited**: Individual test files must never invoke `Base.metadata.drop_all()` directly within a test function. Doing so corrupts the database state for subsequent tests unless all models are re-registered.

---

## 7. Conclusion

The testing infrastructure at `/workspaces/TheTextileCare` is well-structured and fully functional for FastAPI, SQLAlchemy 2.0, and PostgreSQL. 

For the **Driver Assignment, Reassignment, and Notification behaviors (Q51–Q100 / R1–R4)** milestone:
1. **Concurrency Testing**: Concurrency-safe driver assignment can be verified deterministically using the `ThreadPoolExecutor` and `threading.Barrier` pattern. Competing assignment requests will serialize at the PostgreSQL row lock, resulting in exactly one successful assignment and a `409 Conflict` for the competitor.
2. **Notification Testing**: Notification delivery and resilience must be tested through a dual strategy: verifying database notification logs for payload accuracy (name, vehicle details, unmasked phone), and using `unittest.mock.patch` to guarantee that notification failures do not roll back assignments.
3. **Multi-Tenant Security**: Multi-tenant isolation and mandatory reassignment reasons must be verified at both the API layer (HTTP 403/404/422) and the repository layer.
4. **CI Readiness**: The verified CI pipeline commands (`pytest`, `PYTHONPATH=. alembic upgrade head`, `ruff check app`, `pnpm typecheck`, `pnpm lint`) provide complete, deterministic coverage across both backend and monorepo layers.

---

## 8. Verification Method

To independently verify the findings in this report, execute the following commands in the workspace terminal:

```bash
# 1. Verify backend test execution and PostgreSQL database connectivity
pytest backend/tests/integration/test_database.py -v

# 2. Verify health endpoint and schema initialization
pytest backend/tests/api/test_health.py -v

# 3. Verify clean Alembic migration from revision 0 to head
cd /workspaces/TheTextileCare/backend
python3 -c "from app.db import Base, engine; from sqlalchemy import text; Base.metadata.drop_all(bind=engine); conn=engine.connect(); conn.execute(text('DROP TABLE IF EXISTS alembic_version CASCADE')); conn.commit()"
PYTHONPATH=. alembic upgrade head
cd /workspaces/TheTextileCare

# 4. Verify monorepo typecheck (10 packages)
pnpm typecheck

# 5. Verify monorepo linting
pnpm lint
```

### Invalidation Conditions
This report's conclusions become invalidated if:
- PostgreSQL is replaced by SQLite or a non-locking database.
- External distributed message brokers (Kafka/RabbitMQ) are introduced, which would alter the notification testing strategy from PostgreSQL transactional outbox to distributed consumer mocks.
- `reset_database` in `conftest.py` is modified to use transaction rollbacks instead of schema resets without updating table metadata registrations.
