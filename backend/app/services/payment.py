"""Phase 7 — Payment Service.

Handles payment initiation, simulated processing, refunds, and settlement linkage.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.core.exceptions.base import ApiError
from app.models.commercial import PaymentGatewayType
from app.models.payment import Payment, PaymentStatus, Refund
from app.models.pickup import PickupStatus
from app.repositories.commercial import CommercialRepository
from app.repositories.payment import PaymentRepository
from app.repositories.pickup import PickupRepository

_TWO_DP = Decimal("0.01")
_GST = Decimal("0.18")


def _round(value: Decimal) -> Decimal:
    return value.quantize(_TWO_DP, rounding=ROUND_HALF_UP)


class PaymentService:
    """Business logic for payment initiation, processing, and refunds."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PaymentRepository(db)
        self.commercial_repo = CommercialRepository(db)
        self.pickup_repo = PickupRepository(db)

    # -------------------------------------------------------------------
    # Initiation
    # -------------------------------------------------------------------

    def initiate_payment(
        self,
        order_id: uuid.UUID,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        customer_id: uuid.UUID,
    ) -> Payment:
        """Create a PENDING payment for an order whose pickup has been APPROVED.

        Idempotent: returns existing payment if one already exists.
        """
        existing = self.repo.get_by_order_id(order_id, tenant_id=tenant_id)
        if existing:
            return existing

        # Validate pickup is APPROVED
        pickup = self.pickup_repo.get_by_order_id(order_id, tenant_id=tenant_id)
        if not pickup:
            raise ApiError(
                status_code=422,
                code="PICKUP_NOT_FOUND",
                message="No pickup record found for this order.",
            )
        if pickup.status != PickupStatus.APPROVED.value:
            raise ApiError(
                status_code=422,
                code="PICKUP_NOT_APPROVED",
                message=f"Payment can only be initiated after pickup is APPROVED. Current status: {pickup.status}",
            )

        # Get order for amount and currency
        from app.models.order import Order

        order = self.db.get(Order, order_id)
        if not order:
            raise ApiError(status_code=404, code="ORDER_NOT_FOUND", message="Order not found.")

        # Get gateway type from commercial config
        config = self.commercial_repo.get_by_seller_id(
            tenant_id=tenant_id, seller_id=seller_id
        )
        gateway_type = (
            config.marketplace_gateway
            if config
            else PaymentGatewayType.TTC_GATEWAY.value
        )

        payment = Payment(
            order_id=order_id,
            tenant_id=tenant_id,
            seller_id=seller_id,
            customer_id=customer_id,
            gateway_type=gateway_type,
            status=PaymentStatus.PENDING.value,
            currency=order.currency,
            amount=order.grand_total,
            retained_amount=order.grand_total,
        )
        payment = self.repo.create(payment)
        self.db.commit()
        self.db.refresh(payment)
        return payment

    # -------------------------------------------------------------------
    # Processing
    # -------------------------------------------------------------------

    def process_payment(
        self,
        payment_id: uuid.UUID,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        simulate_failure: bool = False,
    ) -> Payment:
        """Simulate payment processing.

        - TTC_GATEWAY success: SUCCEEDED + create settlement record
        - SELLER_GATEWAY success: SUCCEEDED (no settlement)
        - simulate_failure=True: FAILED (or OUTSTANDING if payment not required before pickup)
        """
        payment = self.repo.get_by_id(payment_id, tenant_id=tenant_id)
        if not payment:
            raise ApiError(
                status_code=404,
                code="PAYMENT_NOT_FOUND",
                message=f"Payment {payment_id} not found.",
            )
        if payment.seller_id != seller_id:
            raise ApiError(
                status_code=403,
                code="PAYMENT_ACCESS_DENIED",
                message="Payment does not belong to this seller.",
            )
        if payment.status not in (PaymentStatus.PENDING.value, PaymentStatus.OUTSTANDING.value):
            return payment  # Already processed — idempotent

        config = self.commercial_repo.get_by_seller_id(
            tenant_id=tenant_id, seller_id=seller_id
        )
        commission_rate = (
            Decimal(str(config.commission_rate_percent)) if config else Decimal("10.00")
        )
        payment_required = config.payment_required_before_pickup if config else True

        amount = Decimal(str(payment.amount))

        if simulate_failure:
            if not payment_required:
                new_status = PaymentStatus.OUTSTANDING.value
            else:
                new_status = PaymentStatus.FAILED.value
            payment.status = new_status
            self.db.flush()
            self.db.commit()
            self.db.refresh(payment)
            return payment

        # Simulate success
        gateway_fee = Decimal("0.00")
        gateway_tax = Decimal("0.00")

        retained = _round(amount - gateway_fee - gateway_tax)
        commission = _round(retained * commission_rate / Decimal("100"))
        commission_tax = _round(commission * _GST)

        payment.status = PaymentStatus.SUCCEEDED.value
        payment.gateway_fee = gateway_fee
        payment.gateway_tax = gateway_tax
        payment.ttc_commission = commission
        payment.ttc_commission_tax = commission_tax
        payment.retained_amount = retained
        payment.paid_at = datetime.now(timezone.utc)

        self.db.flush()

        # Create settlement for TTC_GATEWAY
        if payment.gateway_type == PaymentGatewayType.TTC_GATEWAY.value:
            from app.services.settlement import SettlementService

            settlement_svc = SettlementService(self.db)
            settlement = settlement_svc.schedule_settlement(
                seller_id=seller_id,
                tenant_id=tenant_id,
                payment_id=payment_id,
                amount=retained,
                currency=payment.currency,
            )
            payment.settlement_id = settlement.id

        # Record commission on invoice
        try:
            from app.services.billing import BillingService

            BillingService(self.db).record_commission_charge(
                payment_id=payment_id,
                seller_id=seller_id,
                tenant_id=tenant_id,
            )
        except Exception:
            # Billing recording failure must not block payment processing
            pass

        self.db.commit()
        self.db.refresh(payment)
        return payment

    # -------------------------------------------------------------------
    # Refunds
    # -------------------------------------------------------------------

    def create_refund(
        self,
        payment_id: uuid.UUID,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
        amount: Decimal,
        reason: str,
    ) -> Refund:
        """Issue a refund against a succeeded payment."""
        payment = self.repo.get_by_id(payment_id, tenant_id=tenant_id)
        if not payment:
            raise ApiError(
                status_code=404,
                code="PAYMENT_NOT_FOUND",
                message=f"Payment {payment_id} not found.",
            )
        if payment.seller_id != seller_id:
            raise ApiError(
                status_code=403,
                code="PAYMENT_ACCESS_DENIED",
                message="Payment does not belong to this seller.",
            )
        if payment.status not in (
            PaymentStatus.SUCCEEDED.value,
            PaymentStatus.PARTIALLY_REFUNDED.value,
        ):
            raise ApiError(
                status_code=422,
                code="PAYMENT_NOT_REFUNDABLE",
                message=f"Payment cannot be refunded in status: {payment.status}",
            )

        retained = Decimal(str(payment.retained_amount))
        if amount > retained:
            raise ApiError(
                status_code=422,
                code="REFUND_EXCEEDS_RETAINED",
                message=f"Refund amount {amount} exceeds retained amount {retained}.",
            )

        config = self.commercial_repo.get_by_seller_id(
            tenant_id=tenant_id, seller_id=seller_id
        )
        commission_rate = (
            Decimal(str(config.commission_rate_percent)) if config else Decimal("10.00")
        )

        # Recalculate after refund
        new_refunded = _round(Decimal(str(payment.refunded_amount)) + amount)
        new_retained = _round(Decimal(str(payment.amount)) - new_refunded)
        new_commission = _round(new_retained * commission_rate / Decimal("100"))
        new_commission_tax = _round(new_commission * _GST)
        commission_deduction = _round(
            Decimal(str(payment.ttc_commission)) - new_commission
        )

        new_status = (
            PaymentStatus.REFUNDED.value
            if new_retained <= Decimal("0.00")
            else PaymentStatus.PARTIALLY_REFUNDED.value
        )

        refund = Refund(
            tenant_id=tenant_id,
            payment_id=payment_id,
            amount=amount,
            reason=reason,
            commission_deduction=max(commission_deduction, Decimal("0.00")),
            gateway_fee_reversed=Decimal("0.00"),
            gateway_tax_reversed=Decimal("0.00"),
        )
        self.repo.create_refund(refund)

        self.repo.update_retained_commission(
            payment_id=payment_id,
            refunded_amount=new_refunded,
            retained_amount=new_retained,
            ttc_commission=new_commission,
            ttc_commission_tax=new_commission_tax,
            status=new_status,
        )

        self.db.commit()
        self.db.refresh(refund)
        return refund

    # -------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------

    def get_payment_for_order(
        self,
        order_id: uuid.UUID,
        seller_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Payment | None:
        """Return the payment for an order, scoped to seller/tenant."""
        payment = self.repo.get_by_order_id(order_id, tenant_id=tenant_id)
        if payment and payment.seller_id != seller_id:
            return None
        return payment
