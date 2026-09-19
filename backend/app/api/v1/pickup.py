"""Phase 7 — Pickup API endpoints.

Seller routes  : /api/v1/seller/pickups/*
Customer routes: /api/v1/customer/pickups/*
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions.constants import PermissionName
from app.dependencies import get_db, require_authenticated_user, require_permission
from app.core.tenant.context import TenantContext
from app.models.user import User
from app.schemas.pickup import (
    PickupDetailsApproveRequest,
    PickupDetailsRejectRequest,
    PickupDetailsSubmitRequest,
    PickupResponse,
)
from app.services.pickup import PickupService

# Separate routers for seller vs customer prefix
seller_router = APIRouter(tags=["pickups"])
customer_router = APIRouter(tags=["pickups"])


# ---------------------------------------------------------------------------
# Seller routes
# ---------------------------------------------------------------------------


@seller_router.post("/orders/{order_id}", response_model=PickupResponse, status_code=201)
def create_pickup(
    order_id: uuid.UUID,
    ctx: TenantContext = Depends(require_permission(PermissionName.ORDER_PROCESS.value)),
    db: Session = Depends(get_db),
) -> PickupResponse:
    """Create a SCHEDULED pickup record for an IN_PROGRESS order."""
    svc = PickupService(db)
    pickup = svc.create_pickup(
        order_id=order_id,
        seller_id=ctx.seller_id,
        tenant_id=ctx.tenant_id,
    )
    return PickupResponse.model_validate(pickup)


@seller_router.put("/{pickup_id}/submit", response_model=PickupResponse)
def submit_pickup_details(
    pickup_id: uuid.UUID,
    request: PickupDetailsSubmitRequest,
    ctx: TenantContext = Depends(require_permission(PermissionName.ORDER_PROCESS.value)),
    db: Session = Depends(get_db),
) -> PickupResponse:
    """Seller submits verified pickup details; transitions pickup to DETAILS_SUBMITTED."""
    svc = PickupService(db)
    pickup = svc.submit_pickup_details(
        pickup_id=pickup_id,
        seller_id=ctx.seller_id,
        tenant_id=ctx.tenant_id,
        actual_details=request.actual_details,
        driver_notes=request.driver_notes,
    )
    return PickupResponse.model_validate(pickup)


# ---------------------------------------------------------------------------
# Customer routes
# ---------------------------------------------------------------------------


@customer_router.post("/{pickup_id}/approve", response_model=PickupResponse)
def approve_pickup(
    pickup_id: uuid.UUID,
    order_id: uuid.UUID,
    request: PickupDetailsApproveRequest,
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> PickupResponse:
    """Customer approves submitted pickup details; triggers payment initiation."""
    svc = PickupService(db)
    pickup = svc.approve_pickup(
        pickup_id=pickup_id,
        customer_user_id=user.id,
        order_id=order_id,
        customer_notes=request.customer_notes,
    )
    return PickupResponse.model_validate(pickup)


@customer_router.post("/{pickup_id}/reject", response_model=PickupResponse)
def reject_pickup(
    pickup_id: uuid.UUID,
    order_id: uuid.UUID,
    request: PickupDetailsRejectRequest,
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> PickupResponse:
    """Customer rejects submitted pickup details."""
    svc = PickupService(db)
    pickup = svc.reject_pickup(
        pickup_id=pickup_id,
        customer_user_id=user.id,
        order_id=order_id,
        reason=request.reason,
    )
    return PickupResponse.model_validate(pickup)
