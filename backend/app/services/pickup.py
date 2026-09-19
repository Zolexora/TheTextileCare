"""Phase 7 — Pickup Service.

Manages the lifecycle of order pickups: create, submit details, approve, reject.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions.base import ApiError
from app.models.pickup import OrderPickup, PickupStatus
from app.repositories.pickup import PickupRepository


class PickupService:
    """Business logic for order pickup lifecycle management."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PickupRepository(db)

    def create_pickup(
        self,
        order_id: uuid.UUID,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> OrderPickup:
        """Create a SCHEDULED pickup for an IN_PROGRESS order. Idempotent."""
        existing = self.repo.get_by_order_id(order_id, tenant_id=tenant_id)
        if existing:
            return existing

        # Validate order status
        from app.models.order import Order, OrderStatus

        order = self.db.get(Order, order_id)
        if not order:
            raise ApiError(status_code=404, code="ORDER_NOT_FOUND", message="Order not found.")
        if order.seller_id != seller_id:
            raise ApiError(
                status_code=403,
                code="ORDER_ACCESS_DENIED",
                message="Order does not belong to this seller.",
            )
        if order.status != OrderStatus.IN_PROGRESS.value:
            raise ApiError(
                status_code=422,
                code="INVALID_ORDER_STATUS",
                message=f"Order must be IN_PROGRESS to create a pickup. Current: {order.status}",
            )

        pickup = OrderPickup(
            order_id=order_id,
            seller_id=seller_id,
            tenant_id=tenant_id,
            status=PickupStatus.SCHEDULED.value,
        )
        self.repo.create(pickup)
        self.db.commit()
        self.db.refresh(pickup)
        return pickup

    def submit_pickup_details(
        self,
        pickup_id: uuid.UUID,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actual_details: dict,
        driver_notes: str | None = None,
    ) -> OrderPickup:
        """Seller submits verified pickup details; transitions to DETAILS_SUBMITTED."""
        pickup = self.repo.get_by_id(pickup_id, tenant_id=tenant_id)
        if not pickup:
            raise ApiError(
                status_code=404,
                code="PICKUP_NOT_FOUND",
                message=f"Pickup {pickup_id} not found.",
            )
        if pickup.seller_id != seller_id:
            raise ApiError(
                status_code=403,
                code="PICKUP_ACCESS_DENIED",
                message="Pickup does not belong to this seller.",
            )
        if pickup.status != PickupStatus.SCHEDULED.value:
            raise ApiError(
                status_code=422,
                code="INVALID_PICKUP_STATUS",
                message=f"Pickup must be SCHEDULED to submit details. Current: {pickup.status}",
            )

        result = self.repo.submit_actual_details(
            order_id=pickup.order_id,
            tenant_id=tenant_id,
            actual_details=actual_details,
        )
        if driver_notes is not None and result:
            result.driver_notes = driver_notes
            self.db.flush()
        self.db.commit()
        self.db.refresh(result)
        return result

    def approve_pickup(
        self,
        pickup_id: uuid.UUID,
        customer_user_id: uuid.UUID,
        order_id: uuid.UUID,
        customer_notes: str | None = None,
    ) -> OrderPickup:
        """Customer approves submitted pickup details; transitions to APPROVED."""
        pickup = self.repo.get_by_id(pickup_id)
        if not pickup or pickup.order_id != order_id:
            raise ApiError(
                status_code=404,
                code="PICKUP_NOT_FOUND",
                message=f"Pickup {pickup_id} not found for order {order_id}.",
            )
        if pickup.status != PickupStatus.DETAILS_SUBMITTED.value:
            raise ApiError(
                status_code=422,
                code="INVALID_PICKUP_STATUS",
                message=f"Pickup must be DETAILS_SUBMITTED to approve. Current: {pickup.status}",
            )

        # Verify order belongs to customer
        from app.models.customer import Customer
        from app.models.order import Order

        customer = (
            self.db.query(Customer)
            .filter(Customer.user_id == customer_user_id)
            .first()
        )
        if not customer:
            raise ApiError(
                status_code=404,
                code="CUSTOMER_NOT_FOUND",
                message="Customer profile not found.",
            )

        result = self.repo.approve_details(
            order_id=order_id,
            customer_id=customer.id,
        )
        if not result:
            raise ApiError(
                status_code=403,
                code="PICKUP_ACCESS_DENIED",
                message="Pickup does not belong to this customer's order.",
            )
        if customer_notes is not None:
            result.customer_notes = customer_notes
            self.db.flush()
        self.db.commit()
        self.db.refresh(result)
        return result

    def reject_pickup(
        self,
        pickup_id: uuid.UUID,
        customer_user_id: uuid.UUID,
        order_id: uuid.UUID,
        reason: str,
    ) -> OrderPickup:
        """Customer rejects submitted pickup details; transitions to REJECTED."""
        pickup = self.repo.get_by_id(pickup_id)
        if not pickup or pickup.order_id != order_id:
            raise ApiError(
                status_code=404,
                code="PICKUP_NOT_FOUND",
                message=f"Pickup {pickup_id} not found for order {order_id}.",
            )
        if pickup.status != PickupStatus.DETAILS_SUBMITTED.value:
            raise ApiError(
                status_code=422,
                code="INVALID_PICKUP_STATUS",
                message=f"Pickup must be DETAILS_SUBMITTED to reject. Current: {pickup.status}",
            )

        from app.models.customer import Customer

        customer = (
            self.db.query(Customer)
            .filter(Customer.user_id == customer_user_id)
            .first()
        )
        if not customer:
            raise ApiError(
                status_code=404,
                code="CUSTOMER_NOT_FOUND",
                message="Customer profile not found.",
            )

        result = self.repo.reject_details(
            order_id=order_id,
            customer_id=customer.id,
            reason=reason,
        )
        if not result:
            raise ApiError(
                status_code=403,
                code="PICKUP_ACCESS_DENIED",
                message="Pickup does not belong to this customer's order.",
            )
        self.db.commit()
        self.db.refresh(result)
        return result
