"""Phase 7 — Order API endpoints.

Customer routes  : /api/v1/orders/*
Seller routes    : /api/v1/seller/orders/*

Design:
- Customer identity is derived from the authenticated user — never from
  request body customer_id.
- Seller identity is derived from the authenticated tenant context.
- All monetary values are calculated server-side; client totals are ignored.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Sequence

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.permissions.constants import PermissionName
from app.dependencies import (
    get_db,
    require_authenticated_user,
    require_permission,
)
from app.core.exceptions.base import ApiError
from app.core.tenant.context import TenantContext
from app.models.user import User
from app.models.seller import Seller
from app.repositories.sellers import SellerRepository
from app.schemas.order import (
    OrderCancelRequest,
    OrderCreateRequest,
    OrderListResponse,
    OrderListItem,
    OrderResponse,
    OrderStatusTransitionRequest,
)
from app.services.order import OrderService

# ---------------------------------------------------------------------------
# Customer order router
# ---------------------------------------------------------------------------
customer_router = APIRouter(tags=["orders"])


def _order_to_list_item(order) -> OrderListItem:
    return OrderListItem(
        id=order.id,
        order_number=order.order_number,
        status=order.status,
        currency=order.currency,
        grand_total=order.grand_total,
        seller_id=order.seller_id,
        branch_id=order.branch_id,
        customer_id=order.customer_id,
        placed_at=order.placed_at,
        created_at=order.created_at,
        items_count=len(order.items) if order.items else 0,
    )


@customer_router.post("", response_model=OrderResponse, status_code=201)
def create_order(
    request: OrderCreateRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """Create a new order from a marketplace request.

    The backend revalidates the catalog, recalculates pricing, and detects
    price changes. Client-submitted totals are ignored entirely.
    """
    svc = OrderService(db)
    order = svc.create_order(
        user_id=user.id,
        request=request,
        idempotency_key=idempotency_key,
    )
    return OrderResponse.model_validate(order)


@customer_router.get("", response_model=OrderListResponse)
def list_customer_orders(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> OrderListResponse:
    """List the authenticated customer's orders."""
    svc = OrderService(db)
    orders, total = svc.list_customer_orders(
        user_id=user.id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return OrderListResponse(
        items=[_order_to_list_item(o) for o in orders],
        total=total,
        limit=limit,
        offset=offset,
    )


@customer_router.get("/{order_id}", response_model=OrderResponse)
def get_customer_order(
    order_id: uuid.UUID,
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """Get a specific order detail for the authenticated customer."""
    svc = OrderService(db)
    order = svc.get_customer_order(user_id=user.id, order_id=order_id)
    return OrderResponse.model_validate(order)


@customer_router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_customer_order(
    order_id: uuid.UUID,
    body: OrderCancelRequest,
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """Cancel an order (customer-facing, limited to eligible statuses)."""
    svc = OrderService(db)
    order = svc.cancel_order_as_customer(
        user_id=user.id,
        order_id=order_id,
        reason=body.cancellation_reason,
    )
    return OrderResponse.model_validate(order)


# ---------------------------------------------------------------------------
# Seller order router
# ---------------------------------------------------------------------------
seller_router = APIRouter(tags=["seller-orders"])


def _get_seller(context: TenantContext, db: Session) -> Seller:
    repo = SellerRepository(db)
    seller = repo.get_by_tenant_id(context.tenant_id)
    if not seller:
        raise ApiError(
            status_code=404,
            code="SELLER_NOT_FOUND",
            message="No seller profile found for this tenant.",
        )
    return seller


@seller_router.get("", response_model=OrderListResponse)
def list_seller_orders(
    status: str | None = Query(default=None),
    branch_id: uuid.UUID | None = Query(default=None),
    customer_id: uuid.UUID | None = Query(default=None),
    order_number: str | None = Query(default=None),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    context: TenantContext = Depends(require_permission(PermissionName.ORDER_READ.value)),
    db: Session = Depends(get_db),
) -> OrderListResponse:
    """List orders belonging to the authenticated seller."""
    seller = _get_seller(context, db)
    svc = OrderService(db)
    orders, total = svc.list_seller_orders(
        seller_id=seller.id,
        tenant_id=context.tenant_id,
        status=status,
        branch_id=branch_id,
        customer_id=customer_id,
        order_number=order_number,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )
    return OrderListResponse(
        items=[_order_to_list_item(o) for o in orders],
        total=total,
        limit=limit,
        offset=offset,
    )


@seller_router.get("/{order_id}", response_model=OrderResponse)
def get_seller_order(
    order_id: uuid.UUID,
    context: TenantContext = Depends(require_permission(PermissionName.ORDER_READ.value)),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """Get full order detail for the authenticated seller."""
    seller = _get_seller(context, db)
    svc = OrderService(db)
    order = svc.get_seller_order(
        order_id=order_id,
        seller_id=seller.id,
        tenant_id=context.tenant_id,
    )
    return OrderResponse.model_validate(order)


@seller_router.post("/{order_id}/confirm", response_model=OrderResponse)
def confirm_seller_order(
    order_id: uuid.UUID,
    body: OrderStatusTransitionRequest = OrderStatusTransitionRequest(),
    context: TenantContext = Depends(require_permission(PermissionName.ORDER_CONFIRM.value)),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """Seller confirms a PENDING order → CONFIRMED."""
    seller = _get_seller(context, db)
    svc = OrderService(db)
    order = svc.confirm_order(
        order_id=order_id,
        seller_id=seller.id,
        tenant_id=context.tenant_id,
        actor_user_id=context.user_id,
        reason=body.reason,
    )
    return OrderResponse.model_validate(order)


@seller_router.post("/{order_id}/start", response_model=OrderResponse)
def start_seller_order(
    order_id: uuid.UUID,
    body: OrderStatusTransitionRequest = OrderStatusTransitionRequest(),
    context: TenantContext = Depends(require_permission(PermissionName.ORDER_PROCESS.value)),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """Seller starts processing a CONFIRMED order → IN_PROGRESS."""
    seller = _get_seller(context, db)
    svc = OrderService(db)
    order = svc.start_order(
        order_id=order_id,
        seller_id=seller.id,
        tenant_id=context.tenant_id,
        actor_user_id=context.user_id,
        reason=body.reason,
    )
    return OrderResponse.model_validate(order)


@seller_router.post("/{order_id}/complete", response_model=OrderResponse)
def complete_seller_order(
    order_id: uuid.UUID,
    body: OrderStatusTransitionRequest = OrderStatusTransitionRequest(),
    context: TenantContext = Depends(require_permission(PermissionName.ORDER_PROCESS.value)),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """Seller completes an IN_PROGRESS order → COMPLETED."""
    seller = _get_seller(context, db)
    svc = OrderService(db)
    order = svc.complete_order(
        order_id=order_id,
        seller_id=seller.id,
        tenant_id=context.tenant_id,
        actor_user_id=context.user_id,
        reason=body.reason,
    )
    return OrderResponse.model_validate(order)


@seller_router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_seller_order(
    order_id: uuid.UUID,
    body: OrderCancelRequest,
    context: TenantContext = Depends(require_permission(PermissionName.ORDER_CANCEL.value)),
    db: Session = Depends(get_db),
) -> OrderResponse:
    """Seller cancels a PENDING or CONFIRMED order → CANCELLED."""
    seller = _get_seller(context, db)
    svc = OrderService(db)
    order = svc.cancel_order_as_seller(
        order_id=order_id,
        seller_id=seller.id,
        tenant_id=context.tenant_id,
        actor_user_id=context.user_id,
        reason=body.cancellation_reason,
    )
    return OrderResponse.model_validate(order)
