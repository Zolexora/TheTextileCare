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

        # --- Automatic Recalculation Phase 8 ---
        from app.models.order import Order
        order = self.db.get(Order, pickup.order_id)
        
        needs_recalc = False
        for item in order.items:
            if item.price_policy_snapshot and item.price_policy_snapshot.get("recalculation_enabled"):
                needs_recalc = True
                break
                
        if needs_recalc:
            from app.schemas.pricing import PricingCalculationRequest, PricingCalculationItemRequest
            from app.services.pricing import PricingService
            pricing_svc = PricingService(self.db)
            
            # Reconstruct PricingCalculationRequest from actual_details
            # actual_details might be like {"items": [{"service_id": "...", "service_item_id": "...", "verified_quantity": 5}]}
            items = []
            actual_items_map = {}
            if actual_details and "items" in actual_details:
                for ad in actual_details["items"]:
                    key = (str(ad.get("service_id")), str(ad.get("service_item_id")))
                    actual_items_map[key] = ad
            
            for item in order.items:
                # Get updated quantity or fallback to original
                key = (str(item.service_id), str(item.service_item_id))
                updated_qty = item.quantity
                updated_weight = None
                if key in actual_items_map:
                    ad = actual_items_map[key]
                    if "verified_quantity" in ad:
                        updated_qty = ad["verified_quantity"]
                    if "measured_weight_kg" in ad:
                        updated_weight = ad["measured_weight_kg"]
                        
                items.append(PricingCalculationItemRequest(
                    service_id=item.service_id,
                    service_item_id=item.service_item_id,
                    quantity=updated_qty,
                    weight=updated_weight,
                    unit_type=item.unit_type,
                    addon_ids=[a.service_addon_id for a in item.addons]
                ))
                
            pricing_request = PricingCalculationRequest(
                seller_id=order.seller_id,
                branch_id=order.branch_id,
                currency=order.currency,
                items=items,
            )
            
            pricing_result = pricing_svc.calculate(tenant_id=tenant_id, request=pricing_request)
            
            # Update order totals
            from decimal import Decimal, ROUND_HALF_UP
            def _round(v: Decimal) -> Decimal:
                return v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                
            order.subtotal = _round(pricing_result.subtotal)
            order.discount_total = _round(pricing_result.total_discounts)
            order.surcharge_total = _round(pricing_result.total_surcharges)
            order.tax_total = _round(pricing_result.total_tax)
            order.grand_total = _round(pricing_result.grand_total)
            
            import json
            def _decimal_default(obj):
                import uuid
                if isinstance(obj, Decimal): return str(obj)
                if isinstance(obj, uuid.UUID): return str(obj)
                raise TypeError
            order.pricing_snapshot = json.loads(json.dumps(pricing_result.model_dump(), default=_decimal_default))
            
            for idx, item in enumerate(order.items):
                if idx < len(pricing_result.items):
                    price_item = pricing_result.items[idx]
                    item.quantity = price_item.quantity
                    item.unit_price = _round(price_item.unit_price)
                    item.subtotal = _round(price_item.subtotal)
                    item.discount_amount = _round(price_item.discounts)
                    item.surcharge_amount = _round(price_item.surcharges)
                    item.tax_amount = _round(price_item.tax)
                    item.total_amount = _round(price_item.total)
                    item.pricing_snapshot = json.loads(json.dumps(price_item.model_dump(), default=_decimal_default))


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

        from app.models.order import Order
        order = self.db.get(Order, order_id)
        if order:
            from datetime import datetime, timezone
            order.price_locked_at = datetime.now(timezone.utc)


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

        # --- Customer Price Rejection Policy ---
        from app.models.order import Order
        order = self.db.get(Order, order_id)
        
        policy = "CANCEL" # Default
        if order:
            for item in order.items:
                if item.price_policy_snapshot and item.price_policy_snapshot.get("price_rejection_policy") == "PRICE_DISPUTE":
                    policy = "PRICE_DISPUTE"
                    break
        
        if policy == "CANCEL":
            from app.services.order import OrderService
            order_svc = OrderService(self.db)
            try:
                # Cancel the order
                from app.models.order import OrderStatus
                order_svc._transition(order, OrderStatus.CANCELLED, customer_user_id, f"Customer rejected pickup details: {reason}")
            except Exception:
                pass
            result.status = "CANCELLED"
        elif policy == "PRICE_DISPUTE":
            result.status = "PRICE_DISPUTE"


        if not result:
            raise ApiError(
                status_code=403,
                code="PICKUP_ACCESS_DENIED",
                message="Pickup does not belong to this customer's order.",
            )
        self.db.commit()
        self.db.refresh(result)
        return result
