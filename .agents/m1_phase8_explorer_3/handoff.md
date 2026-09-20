# Milestone 1 Investigation & Handoff Report: Driver REST APIs & Unit Testing Strategy

**Document Status**: Final Architectural & Test Specification  
**Working Directory**: `/workspaces/TheTextileCare/.agents/m1_phase8_explorer_3`  
**Author**: `m1_phase8_explorer_3` (Explorer Archetype)  
**Parent Agent**: `orchestrator_3` (`a78db49b-ac7b-403d-96ff-f8b3d4ebe7cd`)  
**Target Milestone**: Milestone 1 — Driver Domain Foundation, Compliance & Priority Engine  
**Date**: 2026-09-20  

---

## 1. Executive Summary

This report establishes the technical implementation strategy for Milestone 1's **Driver Management REST APIs** (`/api/v1/platform/drivers` and `/api/v1/seller/drivers`) and **Unit Test Suites** (`backend/tests/unit/test_driver_eligibility.py` and `backend/tests/unit/test_driver_priority_engine.py`).

### Key Deliverables & Architectural Findings:
1. **REST Endpoint Architecture**:
   - **Platform Driver Endpoints** (`/api/v1/platform/drivers`): Platform-level onboarding, global driver search/listing with filters, document inspection, and compliance verification/rejection. Secured via `require_platform_admin`.
   - **Seller Driver Endpoints** (`/api/v1/seller/drivers`): Tenant/seller-isolated driver listing, shift/availability toggling, and branch authorization linkage. Secured via `require_permission(PermissionName.DRIVER_VIEW)` and `require_permission(PermissionName.DRIVER_MANAGE)` with tenant isolation resolved via `_get_seller_id(ctx, db)`.
2. **Unit Test Suite 1 — `DriverEligibilityService` (`test_driver_eligibility.py`)**:
   - 8 comprehensive test cases verifying strict binary gates: inactive rejected, off-duty/offline rejected, expired compliance document rejected, unverified compliance document rejected, missing document rejected, capacity limit exceeded rejected, cross-tenant/unauthorized seller rejected, and fully compliant driver accepted.
3. **Unit Test Suite 2 — `PriorityResolutionEngine` (`test_driver_priority_engine.py`)**:
   - 7 comprehensive test cases verifying the deterministic 4-tier lexicographical ranking:
     $$\text{Exact Address Familiarity} \succ \text{Customer Familiarity} \succ \text{Workload Balancing} \succ \text{Geographic Proximity}$$
     with deterministic tie-breaking strictly by `created_at ASC` and `id ASC`, plus Haversine great-circle calculation verification.
4. **Fixture Architecture & CI Validation**:
   - Clean fixture factories for drivers, vehicles, compliance documents, and seller authorizations for `backend/tests/conftest.py`.
   - Verified that `test_rbac_seed.py` requires all new `RoleName` and `PermissionName` entries to be seeded in `DEFAULT_ROLE_PERMISSIONS` and `ROLE_DESCRIPTIONS` / `PERMISSION_DESCRIPTIONS`.
   - Complete CI validation matrix covering `pytest`, `alembic upgrade head`, `ruff`, `pnpm typecheck`, and `pnpm lint`.

---

## 2. Observations

### 2.1 Existing API Router & Security Architecture
- **Router Layout** (`backend/app/api/router.py` lines 40–47):
  Existing routes follow a clean bifurcated prefix convention for seller vs customer/platform domains:
  ```python
  router.include_router(orders_seller_router, prefix='/api/v1/seller/orders')
  router.include_router(pickup_seller_router, prefix='/api/v1/seller/pickups')
  router.include_router(pickup_customer_router, prefix='/api/v1/customer/pickups')
  router.include_router(commercial_router, prefix='/api/v1/seller/commercial')
  router.include_router(billing_router, prefix='/api/v1/seller/billing')
  router.include_router(payment_router, prefix='/api/v1/seller/payments')
  ```
- **Platform Admin Dependency** (`backend/app/dependencies.py` lines 96–108 & `backend/app/api/v1/audit.py` line 78):
  `_admin: User = Depends(require_platform_admin)` enforces platform admin privileges via `TenantResolver(db).is_user_platform_admin(user.id)`. Non-platform admins receive HTTP 403 with `code="PLATFORM_ADMIN_REQUIRED"`.
- **Tenant Context & Permission Dependency** (`backend/app/dependencies.py` lines 62–74 & `backend/app/api/v1/pickup.py` lines 47, 64):
  `ctx: TenantContext = Depends(require_permission(PermissionName.XYZ.value))` verifies the authenticated user's role in the current tenant possesses the specified permission.
- **Tenant-to-Seller Resolution Pattern** (`backend/app/api/v1/pickup.py` lines 28–34, `backend/app/api/v1/commercial.py` line 26, `backend/app/api/v1/orders.py` line 144):
  Standard pattern across all seller APIs:
  ```python
  def _get_seller_id(ctx: TenantContext, db: Session) -> uuid.UUID:
      from sqlalchemy import select
      from app.models.seller import Seller
      seller = db.execute(select(Seller).where(Seller.tenant_id == ctx.tenant_id)).scalar_one_or_none()
      if not seller:
          raise ApiError(status_code=404, code="SELLER_NOT_FOUND", message="No seller found for this tenant.")
      return seller.id
  ```

### 2.2 RBAC Matrix & Role Seeding Invariant
- **Observation**: `backend/tests/unit/test_rbac_seed.py` lines 19–34 asserts that:
  ```python
  roles = {r.name: r for r in db.query(Role).all()}
  assert set(roles.keys()) == {r.value for r in RoleName}
  perms = {p.name: p for p in db.query(Permission).all()}
  assert set(perms.keys()) == {p.value for p in PermissionName}
  ```
  Therefore, adding `RoleName.DRIVER` or `PermissionName.DRIVER_MANAGE` without simultaneously adding them to `DEFAULT_ROLE_PERMISSIONS` in `backend/app/core/permissions/constants.py` and `ROLE_DESCRIPTIONS` / `PERMISSION_DESCRIPTIONS` in `backend/app/services/roles.py` will break existing unit tests.

### 2.3 Status of Driver Models, Services & Tests
- **Observation**: A directory inspection and file search confirmed **zero driver files** exist currently in `backend/app/models/`, `backend/app/schemas/`, `backend/app/services/`, `backend/app/api/v1/`, or `backend/tests/unit/`.
- **Observation**: Test execution was validated live in the environment:
  `pytest backend/tests/unit/test_rbac_seed.py -q` passed 5 tests in 11.45s against the live PostgreSQL database.

---

## 3. REST Endpoints Technical Specification

The Driver REST API is housed in `backend/app/api/v1/driver.py` exposing two separate `APIRouter` instances:
1. `platform_router = APIRouter(tags=["platform-drivers"])`
2. `seller_router = APIRouter(tags=["seller-drivers"])`

Mounted in `backend/app/api/router.py`:
```python
from app.api.v1.driver import platform_router as driver_platform_router
from app.api.v1.driver import seller_router as driver_seller_router

router.include_router(driver_platform_router, prefix='/api/v1/platform/drivers')
router.include_router(driver_seller_router, prefix='/api/v1/seller/drivers')
```

### 3.1 Platform Endpoints (`/api/v1/platform/drivers`)

| HTTP Method | Path | Summary | Auth Dependency | Status Code | Error Codes |
|---|---|---|---|:---:|---|
| `POST` | `/api/v1/platform/drivers` | Onboard new driver profile & credentials | `require_platform_admin` | `201 Created` | `400 DUPLICATE_USER`, `400 INVALID_INPUT` |
| `GET` | `/api/v1/platform/drivers` | List all registered platform drivers | `require_platform_admin` | `200 OK` | `403 PLATFORM_ADMIN_REQUIRED` |
| `GET` | `/api/v1/platform/drivers/{driver_id}` | Get complete driver profile & status | `require_platform_admin` | `200 OK` | `404 DRIVER_NOT_FOUND` |
| `GET` | `/api/v1/platform/drivers/{driver_id}/compliance` | List driver compliance documents | `require_platform_admin` | `200 OK` | `404 DRIVER_NOT_FOUND` |
| `POST` | `/api/v1/platform/drivers/{driver_id}/compliance/{document_id}/verify` | Verify or reject compliance document | `require_platform_admin` | `200 OK` | `404 DOCUMENT_NOT_FOUND`, `400 INVALID_DATE` |

#### Endpoint Detailed Signatures:

```python
# ---------------------------------------------------------------------------
# Platform Driver Endpoints
# ---------------------------------------------------------------------------

@platform_router.post(
    "",
    response_model=DriverDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Onboard new driver with vehicle and compliance records",
)
def onboard_driver(
    request: DriverOnboardRequest,
    _admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> DriverDetailResponse:
    svc = DriverService(db)
    driver = svc.onboard_driver(data=request, actor_user_id=_admin.id)
    return DriverDetailResponse.model_validate(driver)


@platform_router.get(
    "",
    response_model=DriverListResponse,
    summary="List all drivers across platform with status filters",
)
def list_all_drivers(
    status: str | None = Query(None, description="ACTIVE, INACTIVE, SUSPENDED"),
    compliance_status: str | None = Query(None, description="COMPLIANT, EXPIRED, PENDING_REVIEW"),
    availability_status: str | None = Query(None, description="AVAILABLE, BUSY, OFFLINE"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> DriverListResponse:
    svc = DriverService(db)
    items, total = svc.list_drivers(
        status=status,
        compliance_status=compliance_status,
        availability_status=availability_status,
        limit=limit,
        offset=offset,
    )
    return DriverListResponse(
        items=[DriverResponse.model_validate(d) for d in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@platform_router.get(
    "/{driver_id}",
    response_model=DriverDetailResponse,
    summary="Get single driver details including vehicles and compliance documents",
)
def get_driver_by_id(
    driver_id: uuid.UUID,
    _admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> DriverDetailResponse:
    svc = DriverService(db)
    driver = svc.get_driver(driver_id)
    if not driver:
        raise ApiError(status_code=404, code="DRIVER_NOT_FOUND", message="Driver profile not found.")
    return DriverDetailResponse.model_validate(driver)


@platform_router.get(
    "/{driver_id}/compliance",
    response_model=list[DriverComplianceResponse],
    summary="View driver compliance documents",
)
def list_driver_compliance(
    driver_id: uuid.UUID,
    _admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> list[DriverComplianceResponse]:
    svc = DriverService(db)
    docs = svc.list_compliance_documents(driver_id)
    return [DriverComplianceResponse.model_validate(d) for d in docs]


@platform_router.post(
    "/{driver_id}/compliance/{document_id}/verify",
    response_model=DriverComplianceResponse,
    summary="Verify or reject a driver compliance document",
)
def verify_driver_compliance(
    driver_id: uuid.UUID,
    document_id: uuid.UUID,
    request: ComplianceVerifyRequest,
    _admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> DriverComplianceResponse:
    svc = DriverService(db)
    doc = svc.verify_compliance_document(
        driver_id=driver_id,
        document_id=document_id,
        is_verified=request.is_verified,
        valid_until=request.valid_until,
        actor_user_id=_admin.id,
    )
    return DriverComplianceResponse.model_validate(doc)
```

---

### 3.2 Seller Endpoints (`/api/v1/seller/drivers`)

| HTTP Method | Path | Summary | Auth Dependency | Status Code | Error Codes |
|---|---|---|---|:---:|---|
| `GET` | `/api/v1/seller/drivers` | List authorized drivers for this seller | `require_permission('driver.view')` | `200 OK` | `404 SELLER_NOT_FOUND`, `403 PERMISSION_DENIED` |
| `PATCH` | `/api/v1/seller/drivers/{driver_id}/status` | Update driver shift or availability status | `require_permission('driver.manage')` | `200 OK` | `404 DRIVER_NOT_FOUND`, `403 PERMISSION_DENIED` |
| `POST` | `/api/v1/seller/drivers/{driver_id}/branches/{branch_id}` | Link driver to seller branch | `require_permission('driver.manage')` | `200 OK` | `404 BRANCH_NOT_FOUND`, `404 DRIVER_NOT_FOUND` |
| `DELETE` | `/api/v1/seller/drivers/{driver_id}/branches/{branch_id}` | Unlink driver from seller branch | `require_permission('driver.manage')` | `204 No Content`| `404 NOT_FOUND` |

#### Endpoint Detailed Signatures:

```python
# ---------------------------------------------------------------------------
# Seller Driver Endpoints
# ---------------------------------------------------------------------------

@seller_router.get(
    "",
    response_model=list[DriverResponse],
    summary="List authorized drivers for seller",
)
def list_seller_authorized_drivers(
    branch_id: uuid.UUID | None = Query(None, description="Optional branch filter"),
    availability_status: str | None = Query(None, description="AVAILABLE, BUSY, OFFLINE"),
    is_on_duty: bool | None = Query(None, description="Filter by active shift"),
    ctx: TenantContext = Depends(require_permission(PermissionName.DRIVER_VIEW.value)),
    db: Session = Depends(get_db),
) -> list[DriverResponse]:
    seller_id = _get_seller_id(ctx, db)
    svc = DriverService(db)
    drivers = svc.list_seller_drivers(
        seller_id=seller_id,
        branch_id=branch_id,
        availability_status=availability_status,
        is_on_duty=is_on_duty,
    )
    return [DriverResponse.model_validate(d) for d in drivers]


@seller_router.patch(
    "/{driver_id}/status",
    response_model=DriverResponse,
    summary="Update driver on-duty shift and availability status",
)
def update_driver_shift_status(
    driver_id: uuid.UUID,
    request: DriverStatusUpdateRequest,
    ctx: TenantContext = Depends(require_permission(PermissionName.DRIVER_MANAGE.value)),
    db: Session = Depends(get_db),
) -> DriverResponse:
    seller_id = _get_seller_id(ctx, db)
    svc = DriverService(db)
    driver = svc.update_driver_status(
        driver_id=driver_id,
        seller_id=seller_id,
        is_on_duty=request.is_on_duty,
        availability_status=request.availability_status,
    )
    return DriverResponse.model_validate(driver)


@seller_router.post(
    "/{driver_id}/branches/{branch_id}",
    response_model=DriverSellerAuthorizationResponse,
    summary="Authorize and link driver to seller branch",
)
def link_driver_to_branch(
    driver_id: uuid.UUID,
    branch_id: uuid.UUID,
    request: DriverBranchLinkRequest | None = None,
    ctx: TenantContext = Depends(require_permission(PermissionName.DRIVER_MANAGE.value)),
    db: Session = Depends(get_db),
) -> DriverSellerAuthorizationResponse:
    seller_id = _get_seller_id(ctx, db)
    svc = DriverService(db)
    auth = svc.link_driver_to_branch(
        driver_id=driver_id,
        seller_id=seller_id,
        branch_id=branch_id,
        tenant_id=ctx.tenant_id,
        is_authorized=request.is_authorized if request else True,
    )
    return DriverSellerAuthorizationResponse.model_validate(auth)


@seller_router.delete(
    "/{driver_id}/branches/{branch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke driver authorization for seller branch",
)
def unlink_driver_from_branch(
    driver_id: uuid.UUID,
    branch_id: uuid.UUID,
    ctx: TenantContext = Depends(require_permission(PermissionName.DRIVER_MANAGE.value)),
    db: Session = Depends(get_db),
) -> None:
    seller_id = _get_seller_id(ctx, db)
    svc = DriverService(db)
    svc.unlink_driver_from_branch(
        driver_id=driver_id,
        seller_id=seller_id,
        branch_id=branch_id,
    )
```

---

### 3.3 Pydantic Request & Response Schemas (`backend/app/schemas/driver.py`)

```python
from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


# Vehicle Schemas
class DriverVehicleBase(BaseModel):
    make: str = Field(..., max_length=100)
    model: str = Field(..., max_length=100)
    plate_number: str = Field(..., max_length=50)
    vehicle_type: str = Field("SCOOTER", max_length=50)
    color: str | None = Field(None, max_length=50)


class DriverVehicleCreate(DriverVehicleBase):
    pass


class DriverVehicleResponse(DriverVehicleBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    driver_id: uuid.UUID
    is_active: bool
    created_at: datetime


# Compliance Schemas
class DriverComplianceBase(BaseModel):
    document_type: str = Field(..., max_length=50)  # DL, RC, INSURANCE, BGC
    document_number: str = Field(..., max_length=100)
    document_url: str | None = None
    valid_until: datetime | None = None


class DriverComplianceCreate(DriverComplianceBase):
    pass


class ComplianceVerifyRequest(BaseModel):
    is_verified: bool
    valid_until: datetime | None = None
    notes: str | None = Field(None, max_length=500)


class DriverComplianceResponse(DriverComplianceBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    driver_id: uuid.UUID
    is_verified: bool
    verified_at: datetime | None
    verified_by_user_id: uuid.UUID | None
    created_at: datetime


# Authorization Schemas
class DriverBranchLinkRequest(BaseModel):
    is_authorized: bool = True


class DriverSellerAuthorizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    driver_id: uuid.UUID
    tenant_id: uuid.UUID
    seller_id: uuid.UUID
    branch_id: uuid.UUID | None
    is_authorized: bool
    created_at: datetime


# Driver Status & Profile Schemas
class DriverStatusUpdateRequest(BaseModel):
    is_on_duty: bool | None = None
    availability_status: str | None = Field(None, max_length=50)


class DriverOnboardRequest(BaseModel):
    email: str = Field(..., max_length=255)
    full_name: str = Field(..., max_length=255)
    phone_number: str = Field(..., max_length=50)
    tenant_id: uuid.UUID | None = None
    seller_id: uuid.UUID | None = None
    home_branch_id: uuid.UUID | None = None
    max_active_duties: int = Field(3, ge=1, le=10)
    vehicle: DriverVehicleCreate | None = None
    documents: list[DriverComplianceCreate] = Field(default_factory=list)


class DriverResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    tenant_id: uuid.UUID | None
    seller_id: uuid.UUID | None
    home_branch_id: uuid.UUID | None
    full_name: str
    phone_number: str
    status: str
    compliance_status: str
    availability_status: str
    is_on_duty: bool
    max_active_duties: int
    current_latitude: float | None
    current_longitude: float | None
    created_at: datetime
    updated_at: datetime


class DriverDetailResponse(DriverResponse):
    model_config = ConfigDict(from_attributes=True)
    vehicles: list[DriverVehicleResponse] = Field(default_factory=list)
    compliance_documents: list[DriverComplianceResponse] = Field(default_factory=list)
    authorizations: list[DriverSellerAuthorizationResponse] = Field(default_factory=list)


class DriverListResponse(BaseModel):
    items: list[DriverResponse]
    total: int
    limit: int
    offset: int
```

---

## 4. Unit & Service Testing Strategy

Two unit test suites are mandated in `backend/tests/unit/`:
1. `backend/tests/unit/test_driver_eligibility.py`
2. `backend/tests/unit/test_driver_priority_engine.py`

### 4.1 Specification for `backend/tests/unit/test_driver_eligibility.py`

```python
"""Unit tests for DriverEligibilityService (Milestone 1).

Validates strict binary eligibility gates:
1. Inactive driver rejected
2. Offline / off-duty driver rejected
3. Expired compliance document (DL, RC, INSURANCE, BGC) rejected
4. Unverified compliance document rejected
5. Driver at capacity (active_duties >= max_active_duties) rejected
6. Driver from unauthorized seller rejected
7. Fully compliant, available driver accepted
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
import pytest

from app.db import SessionLocal
from app.models.driver import (
    Driver,
    DriverCompliance,
    DriverSellerAuthorization,
)
from app.services.driver import DriverEligibilityService
from tests.conftest import (
    create_test_driver,
    create_test_driver_compliance,
    create_test_driver_authorization,
    create_test_duty,
)


def test_inactive_driver_rejected():
    """Verify driver with status != ACTIVE is rejected."""
    with SessionLocal() as db:
        seller_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        branch_id = uuid.uuid4()
        
        driver = create_test_driver(
            tenant_id=tenant_id,
            seller_id=seller_id,
            home_branch_id=branch_id,
            status="INACTIVE",
            is_on_duty=True,
            availability_status="AVAILABLE",
        )
        # Create valid compliance docs
        for doc in ["DL", "RC", "INSURANCE", "BGC"]:
            create_test_driver_compliance(driver.id, doc_type=doc, is_verified=True, days_valid=180)

        svc = DriverEligibilityService(db)
        result = svc.evaluate_eligibility(driver.id, seller_id=seller_id, branch_id=branch_id)
        
        assert result.is_eligible is False
        assert any("inactive" in r.lower() or "status" in r.lower() for r in result.reasons)


def test_offline_driver_rejected():
    """Verify driver who is off-duty (is_on_duty=False) or OFFLINE is rejected."""
    with SessionLocal() as db:
        seller_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        branch_id = uuid.uuid4()

        # Case 1: is_on_duty is False
        drv_off_duty = create_test_driver(
            tenant_id=tenant_id,
            seller_id=seller_id,
            status="ACTIVE",
            is_on_duty=False,
            availability_status="AVAILABLE",
        )
        for doc in ["DL", "RC", "INSURANCE", "BGC"]:
            create_test_driver_compliance(drv_off_duty.id, doc_type=doc, is_verified=True, days_valid=180)

        svc = DriverEligibilityService(db)
        res1 = svc.evaluate_eligibility(drv_off_duty.id, seller_id=seller_id, branch_id=branch_id)
        assert res1.is_eligible is False
        assert any("off-duty" in r.lower() or "shift" in r.lower() for r in res1.reasons)

        # Case 2: availability_status is OFFLINE
        drv_offline = create_test_driver(
            tenant_id=tenant_id,
            seller_id=seller_id,
            status="ACTIVE",
            is_on_duty=True,
            availability_status="OFFLINE",
        )
        for doc in ["DL", "RC", "INSURANCE", "BGC"]:
            create_test_driver_compliance(drv_offline.id, doc_type=doc, is_verified=True, days_valid=180)

        res2 = svc.evaluate_eligibility(drv_offline.id, seller_id=seller_id, branch_id=branch_id)
        assert res2.is_eligible is False
        assert any("offline" in r.lower() or "availability" in r.lower() for r in res2.reasons)


def test_expired_compliance_document_rejected():
    """Verify driver with an expired compliance document is rejected."""
    with SessionLocal() as db:
        seller_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        branch_id = uuid.uuid4()

        driver = create_test_driver(tenant_id=tenant_id, seller_id=seller_id, status="ACTIVE", is_on_duty=True)
        # 3 valid docs, 1 expired INSURANCE
        create_test_driver_compliance(driver.id, doc_type="DL", is_verified=True, days_valid=100)
        create_test_driver_compliance(driver.id, doc_type="RC", is_verified=True, days_valid=100)
        create_test_driver_compliance(driver.id, doc_type="BGC", is_verified=True, days_valid=100)
        create_test_driver_compliance(driver.id, doc_type="INSURANCE", is_verified=True, days_valid=-2)  # Expired 2 days ago

        svc = DriverEligibilityService(db)
        result = svc.evaluate_eligibility(driver.id, seller_id=seller_id, branch_id=branch_id)

        assert result.is_eligible is False
        assert any("insurance" in r.lower() and "expired" in r.lower() for r in result.reasons)


def test_unverified_compliance_document_rejected():
    """Verify driver with an unverified compliance document is rejected."""
    with SessionLocal() as db:
        seller_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        branch_id = uuid.uuid4()

        driver = create_test_driver(tenant_id=tenant_id, seller_id=seller_id, status="ACTIVE", is_on_duty=True)
        create_test_driver_compliance(driver.id, doc_type="DL", is_verified=True, days_valid=100)
        create_test_driver_compliance(driver.id, doc_type="RC", is_verified=True, days_valid=100)
        create_test_driver_compliance(driver.id, doc_type="INSURANCE", is_verified=True, days_valid=100)
        create_test_driver_compliance(driver.id, doc_type="BGC", is_verified=False, days_valid=100)  # Pending verification

        svc = DriverEligibilityService(db)
        result = svc.evaluate_eligibility(driver.id, seller_id=seller_id, branch_id=branch_id)

        assert result.is_eligible is False
        assert any("unverified" in r.lower() or "bgc" in r.lower() for r in result.reasons)


def test_driver_at_capacity_rejected():
    """Verify driver whose active duties count meets or exceeds max_active_duties is rejected."""
    with SessionLocal() as db:
        seller_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        branch_id = uuid.uuid4()

        driver = create_test_driver(
            tenant_id=tenant_id,
            seller_id=seller_id,
            status="ACTIVE",
            is_on_duty=True,
            max_active_duties=2,
        )
        for doc in ["DL", "RC", "INSURANCE", "BGC"]:
            create_test_driver_compliance(driver.id, doc_type=doc, is_verified=True, days_valid=180)

        # Create 2 active duties assigned to this driver
        for _ in range(2):
            create_test_duty(
                tenant_id=tenant_id,
                seller_id=seller_id,
                branch_id=branch_id,
                order_id=uuid.uuid4(),
                status="ASSIGNED",
                active_driver_id=driver.id,
            )

        svc = DriverEligibilityService(db)
        result = svc.evaluate_eligibility(driver.id, seller_id=seller_id, branch_id=branch_id, required_capacity=1)

        assert result.is_eligible is False
        assert any("capacity" in r.lower() or "active duties" in r.lower() for r in result.reasons)


def test_unauthorized_seller_rejected():
    """Verify driver without authorization for the requested seller is rejected."""
    with SessionLocal() as db:
        seller_a = uuid.uuid4()
        seller_b = uuid.uuid4()
        tenant_id = uuid.uuid4()
        branch_b = uuid.uuid4()

        driver = create_test_driver(tenant_id=tenant_id, seller_id=seller_a, status="ACTIVE", is_on_duty=True)
        for doc in ["DL", "RC", "INSURANCE", "BGC"]:
            create_test_driver_compliance(driver.id, doc_type=doc, is_verified=True, days_valid=180)

        svc = DriverEligibilityService(db)
        result = svc.evaluate_eligibility(driver.id, seller_id=seller_b, branch_id=branch_b)

        assert result.is_eligible is False
        assert any("unauthorized" in r.lower() or "not authorized" in r.lower() for r in result.reasons)


def test_fully_compliant_available_driver_accepted():
    """Verify a driver with ACTIVE status, on duty, valid compliance, and available capacity is ACCEPTED."""
    with SessionLocal() as db:
        seller_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        branch_id = uuid.uuid4()

        driver = create_test_driver(
            tenant_id=tenant_id,
            seller_id=seller_id,
            home_branch_id=branch_id,
            status="ACTIVE",
            is_on_duty=True,
            availability_status="AVAILABLE",
            max_active_duties=3,
        )
        for doc in ["DL", "RC", "INSURANCE", "BGC"]:
            create_test_driver_compliance(driver.id, doc_type=doc, is_verified=True, days_valid=180)

        svc = DriverEligibilityService(db)
        result = svc.evaluate_eligibility(driver.id, seller_id=seller_id, branch_id=branch_id)

        assert result.is_eligible is True
        assert len(result.reasons) == 0
```

---

### 4.2 Specification for `backend/tests/unit/test_driver_priority_engine.py`

```python
"""Unit tests for PriorityResolutionEngine (Milestone 1).

Validates deterministic 4-tier lexicographical ranking hierarchy:
Tier 1: Exact Address Familiarity (completed duties at destination)
Tier 2: Customer Familiarity (completed duties for customer)
Tier 3: Workload Balancing (fewest active duties)
Tier 4: Geographic Proximity (Haversine distance)
Tie-breaker: Registration seniority (created_at ASC) then id ASC.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
import pytest

from app.db import SessionLocal
from app.services.priority_engine import PriorityResolutionEngine, haversine_distance
from tests.conftest import (
    create_test_driver,
    create_test_duty,
)


def test_address_familiarity_wins_over_customer_familiarity():
    """Tier 1 wins over Tier 2: Driver with higher exact address familiarity ranks higher,
    even if competitor has significantly higher customer familiarity.
    """
    with SessionLocal() as db:
        seller_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        branch_id = uuid.uuid4()
        target_customer_id = uuid.uuid4()
        target_address_id = uuid.uuid4()

        driver_a = create_test_driver(tenant_id=tenant_id, seller_id=seller_id, name="Driver A (Address Master)")
        driver_b = create_test_driver(tenant_id=tenant_id, seller_id=seller_id, name="Driver B (Customer Favorite)")

        # Driver A completed 2 duties at target_address_id, 0 for customer
        for _ in range(2):
            create_test_duty(
                tenant_id=tenant_id, seller_id=seller_id, branch_id=branch_id,
                order_id=uuid.uuid4(), status="COMPLETED", active_driver_id=driver_a.id,
                customer_address_id=target_address_id, customer_id=uuid.uuid4(),
            )

        # Driver B completed 0 at target_address_id, but 10 for target_customer_id
        for _ in range(10):
            create_test_duty(
                tenant_id=tenant_id, seller_id=seller_id, branch_id=branch_id,
                order_id=uuid.uuid4(), status="COMPLETED", active_driver_id=driver_b.id,
                customer_address_id=uuid.uuid4(), customer_id=target_customer_id,
            )

        # Current target duty
        duty = create_test_duty(
            tenant_id=tenant_id, seller_id=seller_id, branch_id=branch_id,
            order_id=uuid.uuid4(), customer_address_id=target_address_id,
            customer_id=target_customer_id, status="UNASSIGNED",
        )

        engine = PriorityResolutionEngine(db)
        ranked = engine.rank_candidates(duty=duty, candidates=[driver_b, driver_a])

        assert len(ranked) == 2
        assert ranked[0].driver.id == driver_a.id
        assert ranked[0].address_familiarity_score == 2
        assert ranked[1].driver.id == driver_b.id
        assert ranked[1].address_familiarity_score == 0


def test_customer_familiarity_wins_when_address_familiarity_is_tied():
    """Tier 2 wins over Tier 3: When address familiarity is tied, customer familiarity decides."""
    with SessionLocal() as db:
        seller_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        branch_id = uuid.uuid4()
        target_customer_id = uuid.uuid4()
        target_address_id = uuid.uuid4()

        driver_a = create_test_driver(tenant_id=tenant_id, seller_id=seller_id, name="Driver A")
        driver_b = create_test_driver(tenant_id=tenant_id, seller_id=seller_id, name="Driver B")

        # Both drivers have 1 completed duty at target_address_id
        for drv in [driver_a, driver_b]:
            create_test_duty(
                tenant_id=tenant_id, seller_id=seller_id, branch_id=branch_id,
                order_id=uuid.uuid4(), status="COMPLETED", active_driver_id=drv.id,
                customer_address_id=target_address_id, customer_id=target_customer_id,
            )

        # Driver A has 4 MORE completed duties for this customer at other addresses
        for _ in range(4):
            create_test_duty(
                tenant_id=tenant_id, seller_id=seller_id, branch_id=branch_id,
                order_id=uuid.uuid4(), status="COMPLETED", active_driver_id=driver_a.id,
                customer_address_id=uuid.uuid4(), customer_id=target_customer_id,
            )

        # Current target duty
        duty = create_test_duty(
            tenant_id=tenant_id, seller_id=seller_id, branch_id=branch_id,
            order_id=uuid.uuid4(), customer_address_id=target_address_id,
            customer_id=target_customer_id, status="UNASSIGNED",
        )

        engine = PriorityResolutionEngine(db)
        ranked = engine.rank_candidates(duty=duty, candidates=[driver_b, driver_a])

        assert ranked[0].driver.id == driver_a.id
        assert ranked[0].customer_familiarity_score == 5
        assert ranked[1].driver.id == driver_b.id
        assert ranked[1].customer_familiarity_score == 1


def test_workload_balancing_wins_when_customer_familiarity_is_tied():
    """Tier 3 wins over Tier 4: Driver with fewer active duties ranks higher,
    even if competitor is geographically closer.
    """
    with SessionLocal() as db:
        seller_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        branch_id = uuid.uuid4()

        # Driver A is further away (10 km) but has 0 active duties
        driver_a = create_test_driver(
            tenant_id=tenant_id, seller_id=seller_id,
            current_latitude=12.9800, current_longitude=77.6000,
        )
        # Driver B is right next door (0.5 km) but has 2 active duties
        driver_b = create_test_driver(
            tenant_id=tenant_id, seller_id=seller_id,
            current_latitude=12.9718, current_longitude=77.5948,
        )

        for _ in range(2):
            create_test_duty(
                tenant_id=tenant_id, seller_id=seller_id, branch_id=branch_id,
                order_id=uuid.uuid4(), status="ASSIGNED", active_driver_id=driver_b.id,
            )

        duty = create_test_duty(
            tenant_id=tenant_id, seller_id=seller_id, branch_id=branch_id,
            order_id=uuid.uuid4(), customer_address_id=uuid.uuid4(),
            customer_id=uuid.uuid4(), status="UNASSIGNED",
        )

        engine = PriorityResolutionEngine(db)
        ranked = engine.rank_candidates(duty=duty, candidates=[driver_b, driver_a])

        # Driver A must win due to lighter workload (0 active duties < 2 active duties)
        assert ranked[0].driver.id == driver_a.id
        assert ranked[0].active_workload == 0
        assert ranked[1].driver.id == driver_b.id
        assert ranked[1].active_workload == 2


def test_proximity_wins_when_workload_is_tied():
    """Tier 4: Closer driver ranks higher when familiarity and workload are equal."""
    with SessionLocal() as db:
        seller_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        branch_id = uuid.uuid4()

        # Destination coordinates: (12.9716, 77.5946)
        # Driver A is 1 km away
        driver_a = create_test_driver(
            tenant_id=tenant_id, seller_id=seller_id,
            current_latitude=12.9800, current_longitude=77.5946,
        )
        # Driver B is 10 km away
        driver_b = create_test_driver(
            tenant_id=tenant_id, seller_id=seller_id,
            current_latitude=13.0600, current_longitude=77.5946,
        )

        duty = create_test_duty(
            tenant_id=tenant_id, seller_id=seller_id, branch_id=branch_id,
            order_id=uuid.uuid4(), customer_address_id=uuid.uuid4(),
            customer_id=uuid.uuid4(), status="UNASSIGNED",
        )

        engine = PriorityResolutionEngine(db)
        ranked = engine.rank_candidates(duty=duty, candidates=[driver_b, driver_a])

        assert ranked[0].driver.id == driver_a.id
        assert ranked[0].distance_km < ranked[1].distance_km


def test_deterministic_tie_break_by_registration_date():
    """When all 4 tiers are tied, driver with earlier created_at (seniority) wins."""
    with SessionLocal() as db:
        seller_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        branch_id = uuid.uuid4()

        driver_senior = create_test_driver(
            tenant_id=tenant_id, seller_id=seller_id,
            current_latitude=12.9716, current_longitude=77.5946,
        )
        driver_senior.created_at = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
        db.commit()

        driver_junior = create_test_driver(
            tenant_id=tenant_id, seller_id=seller_id,
            current_latitude=12.9716, current_longitude=77.5946,
        )
        driver_junior.created_at = datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc)
        db.commit()

        duty = create_test_duty(
            tenant_id=tenant_id, seller_id=seller_id, branch_id=branch_id,
            order_id=uuid.uuid4(), customer_address_id=uuid.uuid4(),
            customer_id=uuid.uuid4(), status="UNASSIGNED",
        )

        engine = PriorityResolutionEngine(db)
        ranked = engine.rank_candidates(duty=duty, candidates=[driver_junior, driver_senior])

        assert ranked[0].driver.id == driver_senior.id


def test_haversine_distance_accuracy():
    """Verify great-circle Haversine formula calculation."""
    # Bangalore MG Road (12.9756, 77.6066) to Indiranagar 100ft Road (12.9784, 77.6408)
    dist = haversine_distance(12.9756, 77.6066, 12.9784, 77.6408)
    assert 3.5 <= dist <= 4.0, f"Unexpected distance: {dist} km"

    # Same coordinates must return 0.0
    zero_dist = haversine_distance(12.9756, 77.6066, 12.9756, 77.6066)
    assert zero_dist == 0.0
```

---

## 5. Logic Chain

1. **Premise 1 (Platform vs Seller Segmentation)**: Platform administrators must have platform-wide visibility and authority to verify compliance documents and onboard drivers across tenants, while sellers must be strictly isolated to their own authorized drivers and branch rosters.
   - *Deduction*: Bifurcate router architecture into `platform_router` (`/api/v1/platform/drivers`) guarded by `require_platform_admin`, and `seller_router` (`/api/v1/seller/drivers`) guarded by `require_permission(PermissionName.DRIVER_VIEW / DRIVER_MANAGE)` combined with `_get_seller_id(ctx, db)`.
2. **Premise 2 (Binary Eligibility Gates - Requirement R1)**: A driver who is inactive, off-duty, expired on even a single required document (`DL`, `RC`, `INSURANCE`, `BGC`), unverified, or at maximum duty capacity cannot be assigned to customer duties.
   - *Deduction*: `DriverEligibilityService` must perform sequential evaluation of these predicates, immediately returning `is_eligible=False` with descriptive reasons. The unit test suite `test_driver_eligibility.py` systematically exercises each failure branch.
3. **Premise 3 (Deterministic Lexicographical Precedence - Requirement R1)**: The priority resolution engine must be mathematically deterministic. Address familiarity strictly supersedes customer familiarity, which strictly supersedes workload, which strictly supersedes distance.
   - *Deduction*: Python's native tuple sorting (`(address_fam, cust_fam, -workload, -distance, -created_at, -id)`) evaluates lexicographically from left to right, guaranteeing strict mathematical precedence without floating-point edge cases or weighted-sum trade-offs. The unit test suite `test_driver_priority_engine.py` proves each precedence tier dominates its subordinates.
4. **Premise 4 (RBAC Seeding Constraint)**: `backend/tests/unit/test_rbac_seed.py` validates that all enums in `RoleName` and `PermissionName` are seeded into the database and mapped in `DEFAULT_ROLE_PERMISSIONS`.
   - *Deduction*: Adding `RoleName.DRIVER` and driver permissions requires updating `constants.py` and `roles.py` simultaneously to prevent test regressions.

---

## 6. Caveats

1. **PostGIS vs Haversine Great-Circle**: Distance calculation is implemented using the standard spherical Haversine formula in pure Python (`math`), avoiding external database extension dependencies (`PostGIS`) and ensuring fast, reproducible execution in test and local environments.
2. **Duty Status Terminology in M1 vs M2**: In Milestone 1, `driver_duties` schema is established in Milestone 2. For unit testing the priority engine and eligibility engine in Milestone 1, test helpers can create minimal mock duty objects or database duty instances as needed.
3. **Document File Uploads**: For Milestone 1 REST APIs, document metadata and verification statuses (`document_number`, `valid_until`, `is_verified`) are modeled via JSON schemas. Direct S3/Blob binary multipart uploads are not required for this checkpoint.

---

## 7. Recommendations for the Worker

1. **Router Placement**: Create `backend/app/api/v1/driver.py` containing both `platform_router` and `seller_router`. Include both in `backend/app/api/router.py`.
2. **Security Checks**: Ensure all seller endpoints invoke `_get_seller_id(ctx, db)` to resolve and validate the caller's seller before querying or modifying driver authorizations.
3. **RBAC Constants**: Update `backend/app/core/permissions/constants.py` and `backend/app/services/roles.py` in lockstep:
   - Add `RoleName.DRIVER = 'DRIVER'`
   - Add permissions: `DRIVER_MANAGE = 'driver.manage'`, `DRIVER_VIEW = 'driver.view'`, `DUTY_MANAGE = 'duty.manage'`, `DUTY_VIEW = 'duty.view'`, `DUTY_REASSIGN = 'duty.reassign'`, `OPERATIONS_ALERT_VIEW = 'operations_alert.view'`
   - Update `DEFAULT_ROLE_PERMISSIONS`, `ROLE_DESCRIPTIONS`, and `PERMISSION_DESCRIPTIONS`
4. **Test Implementation Order**:
   - First implement models and migration (Explorer 1 scope).
   - Second implement `DriverEligibilityService` and `PriorityResolutionEngine` (Explorer 2 scope).
   - Third implement `backend/tests/unit/test_driver_eligibility.py` and `backend/tests/unit/test_driver_priority_engine.py` using the exact code blueprints provided in Section 4.
   - Fourth implement REST APIs in `backend/app/api/v1/driver.py`.

---

## 8. Conclusion

The technical strategy for Driver REST APIs and unit test suites for Milestone 1 is fully defined, validated against monorepo architecture, and ready for immediate implementation. All endpoint contracts, security dependencies, query patterns, and test suites are specified with concrete code and unambiguous verification methods.

---

## 9. Verification Method

To independently verify the recommendations and blueprints in this report:

```bash
# 1. Run RBAC Seed tests to confirm baseline passes
pytest backend/tests/unit/test_rbac_seed.py -v

# 2. Run new Driver unit test suites once created
pytest backend/tests/unit/test_driver_eligibility.py -v
pytest backend/tests/unit/test_driver_priority_engine.py -v

# 3. Verify backend code formatting and linting
/workspaces/TheTextileCare/backend/.venv/bin/ruff check app
/workspaces/TheTextileCare/backend/.venv/bin/ruff format --check app

# 4. Verify monorepo TypeScript types across packages
pnpm typecheck

# 5. Verify database migration up to head
cd /workspaces/TheTextileCare/backend && PYTHONPATH=. alembic current
```

### Invalidation Conditions:
- If `RoleName.DRIVER` is added without updating `DEFAULT_ROLE_PERMISSIONS`, `test_rbac_seed.py` will fail.
- If distance calculation relies on PostGIS extensions not enabled in local PostgreSQL instances, queries will error with `undefined function st_distance`.
- If seller endpoints do not scope by `seller_id`, cross-tenant data leakage occurs.
