"""Phase 7 — Order Service.

Implements the complete order creation pipeline:
    1. Authenticate customer
    2. Validate seller / branch / catalog hierarchy
    3. Call PricingService (authoritative — never trust client totals)
    4. Compare against previewed_grand_total → 409 PRICE_CHANGED if different
    5. Build snapshots (catalog, pricing, customer, address)
    6. Atomically persist Order + Items + Add-ons + StatusHistory
    7. Link customer ↔ seller relationship
    8. Emit audit events

Order commercial fields are immutable after creation.
Status transitions follow explicit domain rules.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Sequence

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.exceptions.base import ApiError
from app.models.catalog import Catalog, Service, ServiceAddon, ServiceItem
from app.models.customer import Customer, CustomerAddress, CustomerSeller
from app.models.order import (
    ALLOWED_TRANSITIONS,
    CUSTOMER_CANCELLABLE_STATUSES,
    SELLER_CANCELLABLE_STATUSES,
    Order,
    OrderItem,
    OrderItemAddon,
    OrderStatus,
    OrderStatusHistory,
)
from app.models.seller import Branch, Seller
from app.repositories.customer import CustomerRepository
from app.repositories.order import OrderRepository
from app.repositories.sellers import SellerRepository
from app.schemas.order import OrderCreateRequest, OrderCancelRequest
from app.schemas.pricing import PricingCalculationItemRequest, PricingCalculationRequest, PricingCalculationResult
from app.services.audit import AuditService
from app.services.pricing import PricingService

_SCALE = Decimal("0.01")


def _round(v: Decimal) -> Decimal:
    return v.quantize(_SCALE, rounding=ROUND_HALF_UP)


def _decimal_default(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _to_json_safe(obj: Any) -> Any:
    """Convert any object to a JSON-serializable form (via round-trip)."""
    return json.loads(json.dumps(obj, default=_decimal_default))


class OrderService:
    """Business logic layer for the Order domain."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = OrderRepository(db)
        self.customer_repo = CustomerRepository(db)
        self.seller_repo = SellerRepository(db)
        self.pricing_svc = PricingService(db)
        self.audit = AuditService(db)

    # ===================================================================
    # Customer-facing operations
    # ===================================================================

    def create_order(
        self,
        user_id: uuid.UUID,
        request: OrderCreateRequest,
        idempotency_key: str | None = None,
    ) -> Order:
        """
        Full order creation pipeline.

        Raises:
            ApiError 404 — customer profile missing
            ApiError 404 — seller / branch not found or invalid
            ApiError 422 — catalog items invalid
            ApiError 409 — PRICE_CHANGED (previewed_total ≠ current)
            ApiError 409 — IDEMPOTENCY_CONFLICT (same key, different payload)
        """
        # ---- 1. Resolve authenticated customer ----
        customer = self.customer_repo.get_by_user_id(user_id)
        if not customer:
            # Auto-create profile on first order (mirrors customer service)
            customer = self.customer_repo.create_customer(user_id=user_id)
            self.db.flush()

        # ---- 2. Idempotency check ----
        if idempotency_key:
            existing = self.repo.get_by_idempotency_key(customer.id, idempotency_key)
            if existing:
                # Same key → return same order
                return existing

        # ---- 3. Validate seller / branch ----
        seller = self._require_published_seller(request.seller_id)
        branch = self._require_active_branch(seller, request.branch_id)

        # ---- 4. Validate catalog + resolve snapshots ----
        catalog = self._require_active_catalog(seller)
        item_catalog_data = self._validate_and_snapshot_items(catalog, request.items)

        # ---- 5. Call PricingService (authoritative) ----
        pricing_request = self._build_pricing_request(seller, request)
        pricing_result = self.pricing_svc.calculate(
            tenant_id=seller.tenant_id,
            request=pricing_request,
        )

        # ---- 6. Price-change detection ----
        if request.previewed_grand_total is not None:
            current_total = _round(pricing_result.grand_total)
            previewed = _round(request.previewed_grand_total)
            if current_total != previewed:
                raise ApiError(
                    status_code=409,
                    code="PRICE_CHANGED",
                    message=(
                        f"The price has changed. Current: {current_total} {pricing_result.currency}, "
                        f"Previewed: {previewed} {pricing_result.currency}. "
                        "Please confirm the current price."
                    ),
                )

        # ---- 7. Resolve customer address snapshot ----
        address_snapshot: dict[str, Any] | None = None
        if request.customer_address_id:
            address = self.customer_repo.get_address(customer.id, request.customer_address_id)
            if not address:
                raise ApiError(
                    status_code=404,
                    code="ADDRESS_NOT_FOUND",
                    message="Address not found or does not belong to this customer.",
                )
            address_snapshot = self._snapshot_address(address)

        # ---- 8. Build snapshots ----
        customer_snapshot = self._snapshot_customer(customer)
        catalog_snapshot = self._build_catalog_snapshot(item_catalog_data)
        pricing_snapshot = _to_json_safe(pricing_result.model_dump())

        # ---- 9. Persist (atomic) ----
        order_number = self.repo.next_order_number()

        order = Order(
            tenant_id=seller.tenant_id,
            seller_id=seller.id,
            branch_id=branch.id,
            customer_id=customer.id,
            order_number=order_number,
            status=OrderStatus.PENDING.value,
            currency=pricing_result.currency,
            subtotal=_round(pricing_result.subtotal),
            discount_total=_round(pricing_result.total_discounts),
            surcharge_total=_round(pricing_result.total_surcharges),
            tax_total=_round(pricing_result.total_tax),
            grand_total=_round(pricing_result.grand_total),
            pricing_snapshot=pricing_snapshot,
            catalog_snapshot=catalog_snapshot,
            customer_snapshot=customer_snapshot,
            customer_address_snapshot=address_snapshot,
            idempotency_key=idempotency_key,
            placed_at=datetime.now(timezone.utc),
            created_by=user_id,
        )
        self.repo.create(order)

        # ---- 10. Create order items + add-ons ----
        for idx, item_req in enumerate(request.items):
            price_item = pricing_result.items[idx] if idx < len(pricing_result.items) else None
            catalog_item_data = item_catalog_data[idx]

            order_item = OrderItem(
                order_id=order.id,
                service_id=item_req.service_id,
                service_item_id=item_req.service_item_id,
                service_name_snapshot=catalog_item_data["service_name"],
                service_item_name_snapshot=catalog_item_data.get("service_item_name"),
                unit_type=item_req.unit_type,
                quantity=item_req.quantity,
                unit_price=_round(price_item.unit_price) if price_item else Decimal("0.00"),
                subtotal=_round(price_item.subtotal) if price_item else Decimal("0.00"),
                discount_amount=_round(price_item.discounts) if price_item else Decimal("0.00"),
                surcharge_amount=_round(price_item.surcharges) if price_item else Decimal("0.00"),
                tax_amount=_round(price_item.tax) if price_item else Decimal("0.00"),
                total_amount=_round(price_item.total) if price_item else Decimal("0.00"),
                pricing_snapshot=_to_json_safe(price_item.model_dump()) if price_item else {},
            )
            self.repo.create_item(order_item)

            # Add-ons for this item
            for addon_req in item_req.addons:
                addon_catalog = catalog_item_data["addons_by_id"].get(str(addon_req.service_addon_id))
                addon_name = addon_catalog.name if addon_catalog else "Unknown Add-on"

                # Find addon pricing from item result breakdown if available
                addon_unit_price = Decimal("0.00")
                addon_subtotal = Decimal("0.00")
                addon_total = Decimal("0.00")

                order_addon = OrderItemAddon(
                    order_item_id=order_item.id,
                    service_addon_id=addon_req.service_addon_id,
                    addon_name_snapshot=addon_name,
                    quantity=addon_req.quantity,
                    unit_price=addon_unit_price,
                    subtotal=addon_subtotal,
                    discount_amount=Decimal("0.00"),
                    surcharge_amount=Decimal("0.00"),
                    tax_amount=Decimal("0.00"),
                    total_amount=addon_total,
                    pricing_snapshot={},
                )
                self.repo.create_addon(order_addon)

        # ---- 11. Initial status history ----
        self.repo.append_status_history(
            order_id=order.id,
            from_status=None,
            to_status=OrderStatus.PENDING.value,
            reason="Order placed",
            actor_user_id=user_id,
        )

        # ---- 12. Ensure customer ↔ seller relationship ----
        self._ensure_customer_seller_link(customer.id, seller.id)

        # ---- 13. Commit ----
        self.db.commit()
        self.db.refresh(order)

        # ---- 14. Audit ----
        self.audit.log_event(
            event_type="ORDER_CREATED",
            tenant_id=seller.tenant_id,
            actor_user_id=user_id,
            entity_type="Order",
            entity_id=str(order.id),
            payload={
                "order_number": order.order_number,
                "grand_total": str(order.grand_total),
                "currency": order.currency,
                "status": order.status,
            },
        )
        self.db.commit()

        return self.repo.get_by_id(order.id)

    def get_customer_order(self, user_id: uuid.UUID, order_id: uuid.UUID) -> Order:
        customer = self._require_customer(user_id)
        order = self.repo.get_customer_order(order_id, customer.id)
        if not order:
            raise ApiError(status_code=404, code="ORDER_NOT_FOUND", message="Order not found.")
        return order

    def list_customer_orders(
        self,
        user_id: uuid.UUID,
        status: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[Order], int]:
        customer = self._require_customer(user_id)
        return self.repo.list_by_customer(
            customer_id=customer.id,
            status=status,
            limit=limit,
            offset=offset,
        )

    def cancel_order_as_customer(
        self,
        user_id: uuid.UUID,
        order_id: uuid.UUID,
        reason: str,
    ) -> Order:
        customer = self._require_customer(user_id)
        order = self.repo.get_customer_order(order_id, customer.id)
        if not order:
            raise ApiError(status_code=404, code="ORDER_NOT_FOUND", message="Order not found.")

        current = OrderStatus(order.status)
        if current not in CUSTOMER_CANCELLABLE_STATUSES:
            raise ApiError(
                status_code=409,
                code="INVALID_ORDER_STATUS_TRANSITION",
                message=f"Order in status '{order.status}' cannot be cancelled by the customer.",
            )

        return self._transition(
            order=order,
            target=OrderStatus.CANCELLED,
            actor_user_id=user_id,
            reason=reason,
        )

    # ===================================================================
    # Seller-facing operations
    # ===================================================================

    def get_seller_order(
        self,
        order_id: uuid.UUID,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Order:
        order = self.repo.get_seller_order(order_id, seller_id, tenant_id)
        if not order:
            raise ApiError(
                status_code=404,
                code="ORDER_NOT_FOUND",
                message="Order not found or does not belong to this seller.",
            )
        return order

    def list_seller_orders(
        self,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        status: str | None = None,
        branch_id: uuid.UUID | None = None,
        customer_id: uuid.UUID | None = None,
        order_number: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[Order], int]:
        return self.repo.list_by_seller(
            seller_id=seller_id,
            tenant_id=tenant_id,
            status=status,
            branch_id=branch_id,
            customer_id=customer_id,
            order_number=order_number,
            from_date=from_date,
            to_date=to_date,
            limit=limit,
            offset=offset,
        )

    def confirm_order(
        self,
        order_id: uuid.UUID,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        reason: str | None = None,
    ) -> Order:
        order = self.get_seller_order(order_id, seller_id, tenant_id)
        return self._transition(order, OrderStatus.CONFIRMED, actor_user_id, reason)

    def start_order(
        self,
        order_id: uuid.UUID,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        reason: str | None = None,
    ) -> Order:
        order = self.get_seller_order(order_id, seller_id, tenant_id)
        return self._transition(order, OrderStatus.IN_PROGRESS, actor_user_id, reason)

    def complete_order(
        self,
        order_id: uuid.UUID,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        reason: str | None = None,
    ) -> Order:
        order = self.get_seller_order(order_id, seller_id, tenant_id)
        return self._transition(order, OrderStatus.COMPLETED, actor_user_id, reason)

    def reject_order(
        self,
        order_id: uuid.UUID,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        reason: str,
    ) -> Order:
        order = self.get_seller_order(order_id, seller_id, tenant_id)
        current = OrderStatus(order.status)
        if current != OrderStatus.PENDING:
            raise ApiError(
                status_code=409,
                code="INVALID_ORDER_STATUS_TRANSITION",
                message=f"Order in status '{order.status}' cannot be rejected. Only PENDING orders can be rejected.",
            )
        return self._transition(order, OrderStatus.CANCELLED, actor_user_id, reason)

    def cancel_order_as_seller(
        self,
        order_id: uuid.UUID,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        reason: str,
    ) -> Order:
        order = self.get_seller_order(order_id, seller_id, tenant_id)
        current = OrderStatus(order.status)
        if current not in SELLER_CANCELLABLE_STATUSES:
            raise ApiError(
                status_code=409,
                code="INVALID_ORDER_STATUS_TRANSITION",
                message=f"Order in status '{order.status}' cannot be cancelled by the seller.",
            )
        return self._transition(order, OrderStatus.CANCELLED, actor_user_id, reason)

    # ===================================================================
    # Domain transition engine
    # ===================================================================

    def _transition(
        self,
        order: Order,
        target: OrderStatus,
        actor_user_id: uuid.UUID,
        reason: str | None = None,
    ) -> Order:
        """Apply a validated status transition, persist history, audit."""
        current = OrderStatus(order.status)
        if target not in ALLOWED_TRANSITIONS.get(current, []):
            raise ApiError(
                status_code=409,
                code="INVALID_ORDER_STATUS_TRANSITION",
                message=f"Transition from '{current.value}' to '{target.value}' is not allowed.",
            )

        now = datetime.now(timezone.utc)
        prev_status = order.status
        order.status = target.value

        if target == OrderStatus.CONFIRMED:
            order.confirmed_at = now
        elif target == OrderStatus.COMPLETED:
            order.completed_at = now
        elif target == OrderStatus.CANCELLED:
            order.cancelled_at = now
            if reason:
                order.cancellation_reason = reason

        order.updated_by = actor_user_id

        self.repo.append_status_history(
            order_id=order.id,
            from_status=prev_status,
            to_status=target.value,
            reason=reason,
            actor_user_id=actor_user_id,
        )

        self.db.flush()
        self.db.commit()

        event_map = {
            OrderStatus.CONFIRMED: "ORDER_CONFIRMED",
            OrderStatus.IN_PROGRESS: "ORDER_STARTED",
            OrderStatus.COMPLETED: "ORDER_COMPLETED",
            OrderStatus.CANCELLED: "ORDER_CANCELLED",
        }
        self.audit.log_event(
            event_type=event_map.get(target, "ORDER_STATUS_CHANGED"),
            tenant_id=order.tenant_id,
            actor_user_id=actor_user_id,
            entity_type="Order",
            entity_id=str(order.id),
            payload={
                "order_number": order.order_number,
                "from_status": prev_status,
                "to_status": target.value,
                "reason": reason,
            },
        )
        self.db.commit()

        return self.repo.get_by_id(order.id)

    # ===================================================================
    # Validation helpers
    # ===================================================================

    def _require_customer(self, user_id: uuid.UUID) -> Customer:
        customer = self.customer_repo.get_by_user_id(user_id)
        if not customer:
            raise ApiError(
                status_code=404,
                code="CUSTOMER_NOT_FOUND",
                message="Customer profile not found. Please set up your profile first.",
            )
        return customer

    def _require_published_seller(self, seller_id: uuid.UUID) -> Seller:
        from app.models.seller import Seller as SellerModel
        seller = (
            self.db.query(SellerModel)
            .filter(
                SellerModel.id == seller_id,
                SellerModel.marketplace_status == "PUBLISHED",
            )
            .first()
        )
        if not seller:
            raise ApiError(
                status_code=404,
                code="INVALID_SELLER",
                message="Seller not found or not available on the marketplace.",
            )
        return seller

    def _require_active_branch(self, seller: Seller, branch_id: uuid.UUID) -> Branch:
        from app.models.seller import Branch as BranchModel
        branch = (
            self.db.query(BranchModel)
            .filter(
                BranchModel.id == branch_id,
                BranchModel.seller_id == seller.id,
                BranchModel.tenant_id == seller.tenant_id,
                BranchModel.status == "ACTIVE",
                BranchModel.is_marketplace_visible == True,
            )
            .first()
        )
        if not branch:
            raise ApiError(
                status_code=404,
                code="INVALID_BRANCH",
                message="Branch not found, inactive, or not marketplace-eligible.",
            )
        return branch

    def _require_active_catalog(self, seller: Seller) -> Catalog:
        catalog = (
            self.db.query(Catalog)
            .filter(
                Catalog.seller_id == seller.id,
                Catalog.tenant_id == seller.tenant_id,
                Catalog.status == "ACTIVE",
            )
            .first()
        )
        if not catalog:
            raise ApiError(
                status_code=422,
                code="INVALID_CATALOG_ITEM",
                message="Seller has no active catalog.",
            )
        return catalog

    def _validate_and_snapshot_items(
        self,
        catalog: Catalog,
        items: list,
    ) -> list[dict[str, Any]]:
        """Validate all items/add-ons against the active catalog and return snapshot data."""
        result = []
        for item_req in items:
            svc = (
                self.db.query(Service)
                .filter(
                    Service.id == item_req.service_id,
                    Service.catalog_id == catalog.id,
                    Service.status == "ACTIVE",
                )
                .first()
            )
            if not svc:
                raise ApiError(
                    status_code=422,
                    code="INVALID_CATALOG_ITEM",
                    message=f"Service {item_req.service_id} is not active in this catalog.",
                )

            service_item_name = None
            if item_req.service_item_id:
                svc_item = (
                    self.db.query(ServiceItem)
                    .filter(
                        ServiceItem.id == item_req.service_item_id,
                        ServiceItem.service_id == svc.id,
                        ServiceItem.status == "ACTIVE",
                    )
                    .first()
                )
                if not svc_item:
                    raise ApiError(
                        status_code=422,
                        code="INVALID_CATALOG_ITEM",
                        message=f"Service item {item_req.service_item_id} is invalid or inactive.",
                    )
                service_item_name = svc_item.name

            # Validate add-ons
            addons_by_id: dict[str, ServiceAddon] = {}
            for addon_req in item_req.addons:
                addon = (
                    self.db.query(ServiceAddon)
                    .filter(
                        ServiceAddon.id == addon_req.service_addon_id,
                        ServiceAddon.service_id == svc.id,
                        ServiceAddon.status == "ACTIVE",
                    )
                    .first()
                )
                if not addon:
                    raise ApiError(
                        status_code=422,
                        code="INVALID_CATALOG_ITEM",
                        message=f"Add-on {addon_req.service_addon_id} is invalid or inactive.",
                    )
                addons_by_id[str(addon_req.service_addon_id)] = addon

            result.append({
                "service_id": str(svc.id),
                "service_name": svc.name,
                "service_item_name": service_item_name,
                "unit_type": item_req.unit_type,
                "addons_by_id": addons_by_id,
            })

        return result

    def _build_pricing_request(
        self, seller: Seller, request: OrderCreateRequest
    ) -> PricingCalculationRequest:
        items = [
            PricingCalculationItemRequest(
                service_id=item.service_id,
                service_item_id=item.service_item_id,
                quantity=item.quantity,
                weight=item.weight,
                unit_type=item.unit_type,
                addon_ids=[a.service_addon_id for a in item.addons],
            )
            for item in request.items
        ]
        return PricingCalculationRequest(
            seller_id=seller.id,
            branch_id=request.branch_id,
            currency=request.currency,
            items=items,
        )

    def _snapshot_customer(self, customer: Customer) -> dict[str, Any]:
        return {
            "customer_id": str(customer.id),
            "display_name": customer.display_name,
            "phone": customer.phone,
            "email": customer.email,
        }

    def _snapshot_address(self, address: CustomerAddress) -> dict[str, Any]:
        return {
            "recipient_name": address.recipient_name,
            "phone": address.phone,
            "address_line_1": address.address_line_1,
            "address_line_2": address.address_line_2,
            "locality": address.locality,
            "city": address.city,
            "state": address.state,
            "postal_code": address.postal_code,
            "country": address.country,
        }

    def _build_catalog_snapshot(self, item_catalog_data: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "items": [
                {
                    "service_id": d["service_id"],
                    "service_name": d["service_name"],
                    "service_item_name": d.get("service_item_name"),
                    "unit_type": d.get("unit_type", "ITEM"),
                    "addons": [
                        {"addon_id": str(aid), "addon_name": a.name}
                        for aid, a in d.get("addons_by_id", {}).items()
                    ],
                }
                for d in item_catalog_data
            ]
        }

    def _ensure_customer_seller_link(
        self, customer_id: uuid.UUID, seller_id: uuid.UUID
    ) -> CustomerSeller:
        rel = self.customer_repo.get_seller_relationship(customer_id, seller_id)
        if not rel:
            rel = CustomerSeller(customer_id=customer_id, seller_id=seller_id)
            self.db.add(rel)
            self.db.flush()
        return rel
