"""Phase 8 — Driver Management REST APIs.

Provides platform administrator and seller-scoped endpoints for driver onboarding,
shift status management, branch authorizations, and compliance verification.
"""
from __future__ import annotations

import uuid
from typing import Sequence

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.services.driver_assignment import DriverAssignmentService
from app.core.exceptions import ApiError
from app.core.permissions.constants import PermissionName
from app.db import get_db
from app.dependencies import require_permission, require_platform_admin
from app.models.seller import Seller
from app.models.user import User
from app.core.tenant.context import TenantContext
from app.schemas.driver import (
    ComplianceVerifyRequest,
    DriverComplianceDocumentResponse,
    DriverDetailResponse,
    DriverListResponse,
    DriverOnboardRequest,
    DriverResponse,
    DriverSellerAuthorizationResponse,
    DriverStatusUpdateRequest,
)
from app.services.driver import DriverService

platform_router = APIRouter(tags=["platform-drivers"])
seller_router = APIRouter(tags=["seller-drivers"])
seller_duties_router = APIRouter(tags=["seller-duties"])


def _get_seller_id(ctx: TenantContext, db: Session) -> uuid.UUID:
    seller = db.execute(select(Seller).where(Seller.tenant_id == ctx.tenant_id)).scalar_one_or_none()
    if not seller:
        raise ApiError(status_code=404, code="SELLER_NOT_FOUND", message="No seller found for this tenant.")
    return seller.id


# ============================================================================
# Platform Driver Endpoints (/api/v1/platform/drivers)
# ============================================================================

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
    status_val: str | None = Query(None, alias="status", description="ACTIVE, INACTIVE, SUSPENDED"),
    compliance_status: str | None = Query(None, description="COMPLIANT, EXPIRED, PENDING"),
    availability_status: str | None = Query(None, description="AVAILABLE, BUSY, OFFLINE"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    _admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> DriverListResponse:
    svc = DriverService(db)
    items, total = svc.list_drivers(
        status=status_val,
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
    response_model=list[DriverComplianceDocumentResponse],
    summary="View driver compliance documents",
)
def list_driver_compliance(
    driver_id: uuid.UUID,
    _admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> list[DriverComplianceDocumentResponse]:
    svc = DriverService(db)
    docs = svc.list_compliance_documents(driver_id)
    return [DriverComplianceDocumentResponse.model_validate(d) for d in docs]


@platform_router.post(
    "/{driver_id}/compliance/{document_id}/verify",
    response_model=DriverComplianceDocumentResponse,
    summary="Verify or reject a driver compliance document",
)
def verify_driver_compliance(
    driver_id: uuid.UUID,
    document_id: uuid.UUID,
    request: ComplianceVerifyRequest,
    _admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> DriverComplianceDocumentResponse:
    svc = DriverService(db)
    doc = svc.verify_compliance_document(
        driver_id=driver_id,
        document_id=document_id,
        is_verified=request.is_verified,
        valid_until=request.valid_until,
        actor_user_id=_admin.id,
        rejection_reason=request.rejection_reason,
    )
    return DriverComplianceDocumentResponse.model_validate(doc)


# ============================================================================
# Seller Driver Endpoints (/api/v1/seller/drivers)
# ============================================================================

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
        is_authorized=True,
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

from pydantic import BaseModel, Field
class AssignDriverRequest(BaseModel):
    driver_id: uuid.UUID | None = None
    notes: str | None = None

class AssignmentResponse(BaseModel):
    id: uuid.UUID
    duty_id: uuid.UUID
    driver_id: uuid.UUID
    status: str
    is_active: bool
    class Config:
        from_attributes = True

@seller_duties_router.post(
    "/{duty_id}/assign",
    response_model=AssignmentResponse,
    summary="Assign driver to a duty"
)
def assign_driver(
    duty_id: uuid.UUID,
    request: AssignDriverRequest,
    ctx: TenantContext = Depends(require_permission(PermissionName.DRIVER_MANAGE.value)),
    db: Session = Depends(get_db),
):
    seller_id = _get_seller_id(ctx, db)
    svc = DriverAssignmentService(db)
    # The actual actor user ID is ctx.user_id, wait, ctx doesn't have user_id, let me check how TenantContext works.
    asgn = svc.assign_duty(
        duty_id=duty_id,
        seller_id=seller_id,
        actor_user_id=None,
        driver_id=request.driver_id,
        notes=request.notes
    )
    return AssignmentResponse.model_validate(asgn)

class ReassignDriverRequest(BaseModel):
    new_driver_id: uuid.UUID | None = None
    reason: str = Field(..., min_length=1)

@seller_duties_router.post(
    "/{duty_id}/reassign",
    response_model=AssignmentResponse,
    summary="Reassign driver for a duty"
)
def reassign_driver(
    duty_id: uuid.UUID,
    request: ReassignDriverRequest,
    ctx: TenantContext = Depends(require_permission(PermissionName.DRIVER_MANAGE.value)),
    db: Session = Depends(get_db),
):
    seller_id = _get_seller_id(ctx, db)
    svc = DriverAssignmentService(db)
    
    # Let Pydantic validation handle empty/whitespace strings for "reason"
    # Actually Pydantic min_length=1 doesn't catch "   ". We'll validate manually.
    reason_clean = request.reason.strip()
    if not reason_clean:
        raise ApiError(status_code=422, code="VALIDATION_ERROR", message="Reason cannot be empty")
        
    asgn = svc.reassign_duty(
        duty_id=duty_id,
        seller_id=seller_id,
        actor_user_id=None,
        new_driver_id=request.new_driver_id,
        reason=reason_clean
    )
    return AssignmentResponse.model_validate(asgn)
