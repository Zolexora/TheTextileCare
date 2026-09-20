"""Phase 7 — Payment API endpoints.

Seller routes: /api/v1/seller/payments/*
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.exceptions.base import ApiError
from app.core.permissions.constants import PermissionName
from app.dependencies import get_db, require_authenticated_user, require_permission
from app.core.tenant.context import TenantContext
from app.models.user import User
from app.repositories.customer import CustomerRepository
from app.schemas.payment import (
    PaymentInitiateRequest,
    PaymentProcessRequest,
    PaymentResponse,
    RefundCreateRequest,
    RefundResponse,
)
from app.services.payment import PaymentService

router = APIRouter(tags=["payments"])

def _get_seller_id(ctx: TenantContext, db: Session) -> uuid.UUID:
    from sqlalchemy import select
    from app.models.seller import Seller
    seller = db.execute(select(Seller).where(Seller.tenant_id == ctx.tenant_id)).scalar_one_or_none()
    if not seller:
        raise ApiError(status_code=404, code="SELLER_NOT_FOUND", message="No seller found for this tenant.")
    return seller.id



@router.post("/orders/{order_id}/initiate", response_model=PaymentResponse, status_code=201)
def initiate_payment(
    order_id: uuid.UUID,
    request: PaymentInitiateRequest,
    ctx: TenantContext = Depends(require_permission(PermissionName.PAYMENT_PROCESS.value)),
    db: Session = Depends(get_db),
) -> PaymentResponse:
    """Initiate a payment for an order whose pickup has been APPROVED."""
    from app.models.order import Order

    order = db.get(Order, order_id)
    if not order:
        raise ApiError(status_code=404, code="ORDER_NOT_FOUND", message="Order not found.")

    svc = PaymentService(db)
    payment = svc.initiate_payment(
        order_id=order_id,
        seller_id=_get_seller_id(ctx, db),
        tenant_id=ctx.tenant_id,
        customer_id=order.customer_id,
    )
    return PaymentResponse.model_validate(payment)


@router.post("/{payment_id}/process", response_model=PaymentResponse)
def process_payment(
    payment_id: uuid.UUID,
    request: PaymentProcessRequest,
    ctx: TenantContext = Depends(require_permission(PermissionName.PAYMENT_PROCESS.value)),
    db: Session = Depends(get_db),
) -> PaymentResponse:
    """Process a pending payment (simulated — no real gateway call)."""
    svc = PaymentService(db)
    payment = svc.process_payment(
        payment_id=payment_id,
        seller_id=_get_seller_id(ctx, db),
        tenant_id=ctx.tenant_id,
        simulate_failure=request.simulate_failure,
    )
    return PaymentResponse.model_validate(payment)


@router.post("/{payment_id}/refund", response_model=RefundResponse, status_code=201)
def create_refund(
    payment_id: uuid.UUID,
    request: RefundCreateRequest,
    ctx: TenantContext = Depends(require_permission(PermissionName.PAYMENT_PROCESS.value)),
    db: Session = Depends(get_db),
) -> RefundResponse:
    """Issue a partial or full refund against a succeeded payment."""
    svc = PaymentService(db)
    refund = svc.create_refund(
        payment_id=payment_id,
        seller_id=_get_seller_id(ctx, db),
        tenant_id=ctx.tenant_id,
        amount=request.amount,
        reason=request.reason,
    )
    return RefundResponse.model_validate(refund)


@router.get("/orders/{order_id}/payment", response_model=PaymentResponse | None)
def get_payment_for_order(
    order_id: uuid.UUID,
    ctx: TenantContext = Depends(require_permission(PermissionName.PAYMENT_READ.value)),
    db: Session = Depends(get_db),
) -> PaymentResponse | None:
    """Get the payment record for a specific order."""
    svc = PaymentService(db)
    payment = svc.get_payment_for_order(
        order_id=order_id,
        seller_id=_get_seller_id(ctx, db),
        tenant_id=ctx.tenant_id,
    )
    if payment is None:
        return None
    return PaymentResponse.model_validate(payment)
