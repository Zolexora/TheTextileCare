"""Unit tests for Phase 7 Models, Schemas, and RBAC Permissions."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.permissions.constants import DEFAULT_ROLE_PERMISSIONS, PermissionName, RoleName
from app.db import SessionLocal
from app.models.billing import InvoiceStatus, SellerBillingInvoice, SellerSettlement, SettlementStatus
from app.models.commercial import (
    PaymentGatewayType,
    SellerCommercialConfiguration,
    SellerCommercialModel,
    SellerRestrictionLevel,
)
from app.models.customer import Customer
from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentStatus, Refund
from app.models.pickup import OrderPickup, PickupStatus
from app.models.seller import Branch, Seller
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.billing import (
    BillingInvoiceGenerateRequest,
    BillingInvoicePayRequest,
    BillingInvoiceResponse,
    LatePenaltyCalculationResponse,
)
from app.schemas.commercial import (
    CommercialConfigBase,
    CommercialConfigCreate,
    CommercialConfigResponse,
    CommercialConfigUpdate,
)
from app.schemas.order import OrderReselectRequest
from app.schemas.payment import (
    PaymentLedgerBreakdownResponse,
    PaymentResponse,
    RefundCreateRequest,
    RefundResponse,
)
from app.schemas.pickup import (
    PickupDetailsApproveRequest,
    PickupDetailsRejectRequest,
    PickupDetailsSubmitRequest,
    PickupResponse,
)
from app.schemas.settlement import (
    SettlementEligibleBatchPreviewResponse,
    SettlementGenerateRequest,
    SettlementProcessRequest,
    SettlementResponse,
)
from app.services.roles import PERMISSION_DESCRIPTIONS, ROLE_DESCRIPTIONS, RoleService


class TestCommercialModelsAndSchemas:
    """Tests for Commercial models and Pydantic schemas."""

    def test_commercial_config_commission_model_valid(self):
        config = CommercialConfigBase(
            commercial_model=SellerCommercialModel.COMMISSION,
            commission_rate_percent=Decimal("12.50"),
            subscription_fee=Decimal("0.00"),
        )
        assert config.commercial_model == SellerCommercialModel.COMMISSION
        assert config.commission_rate_percent == Decimal("12.50")
        assert config.subscription_fee == Decimal("0.00")

    def test_commercial_config_subscription_model_valid(self):
        config = CommercialConfigBase(
            commercial_model=SellerCommercialModel.SUBSCRIPTION,
            commission_rate_percent=Decimal("0.00"),
            subscription_fee=Decimal("99.99"),
        )
        assert config.commercial_model == SellerCommercialModel.SUBSCRIPTION
        assert config.commission_rate_percent == Decimal("0.00")
        assert config.subscription_fee == Decimal("99.99")

    def test_commercial_config_mutual_exclusivity_invalid_commission(self):
        # Commission model with subscription fee > 0 should raise ValueError
        with pytest.raises(ValidationError) as exc_info:
            CommercialConfigBase(
                commercial_model=SellerCommercialModel.COMMISSION,
                commission_rate_percent=Decimal("10.00"),
                subscription_fee=Decimal("50.00"),
            )
        assert "subscription_fee to be exactly 0.00" in str(exc_info.value)

    def test_commercial_config_mutual_exclusivity_invalid_subscription(self):
        # Subscription model with commission rate > 0 should raise ValueError
        with pytest.raises(ValidationError) as exc_info:
            CommercialConfigBase(
                commercial_model=SellerCommercialModel.SUBSCRIPTION,
                commission_rate_percent=Decimal("5.00"),
                subscription_fee=Decimal("100.00"),
            )
        assert "commission_rate_percent to be exactly 0.00" in str(exc_info.value)

    def test_commercial_config_update_validation(self):
        update = CommercialConfigUpdate(
            commercial_model=SellerCommercialModel.COMMISSION,
            commission_rate_percent=Decimal("15.00"),
        )
        assert update.commission_rate_percent == Decimal("15.00")

        with pytest.raises(ValidationError):
            CommercialConfigUpdate(
                commercial_model=SellerCommercialModel.COMMISSION,
                subscription_fee=Decimal("10.00"),
            )

    def test_commercial_config_sqlalchemy_model(self):
        tenant_id = uuid.uuid4()
        seller_id = uuid.uuid4()
        with SessionLocal() as db:
            tenant = Tenant(id=tenant_id, name="Commercial Test Tenant", slug="comm-test")
            seller = Seller(id=seller_id, tenant_id=tenant_id, business_name="Comm Seller", slug="comm-seller")
            db.add_all([tenant, seller])
            db.flush()

            cfg = SellerCommercialConfiguration(
                tenant_id=tenant_id,
                seller_id=seller_id,
                commercial_model=SellerCommercialModel.COMMISSION.value,
                commission_rate_percent=Decimal("8.00"),
                subscription_fee=Decimal("0.00"),
                marketplace_gateway=PaymentGatewayType.TTC_GATEWAY.value,
                white_label_gateway=PaymentGatewayType.SELLER_GATEWAY.value,
                payment_required_before_pickup=True,
                outstanding_receivable_allowed=False,
                overdue_grace_days=7,
                daily_penalty_rate=Decimal("0.0010"),
            )
            db.add(cfg)
            db.commit()
            db.refresh(cfg)

            assert cfg.id is not None
            assert cfg.payment_gateway_type == PaymentGatewayType.TTC_GATEWAY.value
            assert cfg.restriction_level == SellerRestrictionLevel.NONE.value
            assert cfg.daily_penalty_rate == Decimal("0.0010")


class TestPickupModelsAndSchemas:
    """Tests for Pickup models and Pydantic schemas."""

    def test_pickup_status_enum_values(self):
        assert PickupStatus.SCHEDULED.value == "SCHEDULED"
        assert PickupStatus.DETAILS_SUBMITTED.value == "DETAILS_SUBMITTED"
        assert PickupStatus.APPROVED.value == "APPROVED"
        assert PickupStatus.REJECTED.value == "REJECTED"
        assert PickupStatus.COMPLETED.value == "COMPLETED"

    def test_pickup_requests_and_response_schemas(self):
        submit_req = PickupDetailsSubmitRequest(
            actual_details={"items": [{"name": "Suit", "count": 2}], "weight_kg": 1.5},
            driver_notes="Picked up on time",
        )
        assert submit_req.actual_details["weight_kg"] == 1.5
        assert submit_req.driver_notes == "Picked up on time"

        approve_req = PickupDetailsApproveRequest(customer_notes="Looks correct")
        assert approve_req.customer_notes == "Looks correct"

        reject_req = PickupDetailsRejectRequest(reason="Item count mismatch")
        assert reject_req.reason == "Item count mismatch"

    def test_pickup_model_and_relationships(self):
        tenant_id = uuid.uuid4()
        seller_id = uuid.uuid4()
        branch_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        order_id = uuid.uuid4()

        with SessionLocal() as db:
            tenant = Tenant(id=tenant_id, name="Pickup Tenant", slug="pickup-tenant")
            seller = Seller(id=seller_id, tenant_id=tenant_id, business_name="Pickup Seller", slug="pickup-seller")
            branch = Branch(id=branch_id, tenant_id=tenant_id, seller_id=seller_id, name="Main Branch", code="MB-01")
            user = User(id=uuid.uuid4(), auth_user_id=f"auth-{uuid.uuid4().hex[:6]}", email=f"pickup-{uuid.uuid4().hex[:6]}@cust.com")
            db.add(user)
            db.flush()
            customer = Customer(id=customer_id, user_id=user.id, email=user.email, first_name="John", last_name="Doe")
            order = Order(
                id=order_id,
                tenant_id=tenant_id,
                seller_id=seller_id,
                branch_id=branch_id,
                customer_id=customer_id,
                order_number="ORD-PICKUP-001",
                status=OrderStatus.PENDING.value,
                currency="USD",
                subtotal=Decimal("50.00"),
                grand_total=Decimal("50.00"),
                pricing_snapshot={},
                catalog_snapshot={},
                customer_snapshot={},
            )
            pickup = OrderPickup(
                tenant_id=tenant_id,
                seller_id=seller_id,
                order_id=order_id,
                status=PickupStatus.SCHEDULED.value,
            )
            db.add_all([tenant, seller, branch, customer, order, pickup])
            db.commit()
            db.refresh(order)
            db.refresh(pickup)

            assert order.pickup is not None
            assert order.pickup.id == pickup.id
            assert pickup.order.id == order.id
            assert pickup.status == PickupStatus.SCHEDULED.value


class TestPaymentAndRefundModelsAndSchemas:
    """Tests for Payment and Refund models and schemas."""

    def test_payment_status_enum(self):
        assert PaymentStatus.PENDING.value == "PENDING"
        assert PaymentStatus.SUCCEEDED.value == "SUCCEEDED"
        assert PaymentStatus.FAILED.value == "FAILED"
        assert PaymentStatus.OUTSTANDING.value == "OUTSTANDING"
        assert PaymentStatus.REFUNDED.value == "REFUNDED"
        assert PaymentStatus.PARTIALLY_REFUNDED.value == "PARTIALLY_REFUNDED"

    def test_payment_ledger_separation_and_refund_schemas(self):
        now = datetime.now(timezone.utc)
        payment_resp = PaymentResponse(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            order_id=uuid.uuid4(),
            seller_id=uuid.uuid4(),
            customer_id=uuid.uuid4(),
            gateway_type=PaymentGatewayType.TTC_GATEWAY,
            status=PaymentStatus.SUCCEEDED,
            currency="USD",
            amount=Decimal("100.00"),
            gateway_fee=Decimal("2.90"),
            gateway_tax=Decimal("0.52"),
            ttc_commission=Decimal("10.00"),
            ttc_commission_tax=Decimal("1.80"),
            refunded_amount=Decimal("0.00"),
            retained_amount=Decimal("100.00"),
            settled=False,
            paid_at=now,
            created_at=now,
            updated_at=now,
        )
        assert payment_resp.amount == Decimal("100.00")
        assert payment_resp.gateway_fee == Decimal("2.90")
        assert payment_resp.ttc_commission == Decimal("10.00")

        refund_req = RefundCreateRequest(
            amount=Decimal("30.00"),
            reason="Damaged item during cleaning",
        )
        assert refund_req.amount == Decimal("30.00")

    def test_payment_and_refund_sqlalchemy_models(self):
        tenant_id = uuid.uuid4()
        seller_id = uuid.uuid4()
        branch_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        order_id = uuid.uuid4()

        with SessionLocal() as db:
            tenant = Tenant(id=tenant_id, name="Pay Tenant", slug="pay-tenant")
            seller = Seller(id=seller_id, tenant_id=tenant_id, business_name="Pay Seller", slug="pay-seller")
            branch = Branch(id=branch_id, tenant_id=tenant_id, seller_id=seller_id, name="Pay Branch", code="PB-01")
            user = User(id=uuid.uuid4(), auth_user_id=f"auth-{uuid.uuid4().hex[:6]}", email=f"pay-{uuid.uuid4().hex[:6]}@cust.com")
            db.add(user)
            db.flush()
            customer = Customer(id=customer_id, user_id=user.id, email=user.email, first_name="Jane", last_name="Doe")
            order = Order(
                id=order_id,
                tenant_id=tenant_id,
                seller_id=seller_id,
                branch_id=branch_id,
                customer_id=customer_id,
                order_number="ORD-PAY-001",
                status=OrderStatus.PENDING.value,
                currency="USD",
                subtotal=Decimal("80.00"),
                grand_total=Decimal("80.00"),
                pricing_snapshot={},
                catalog_snapshot={},
                customer_snapshot={},
            )
            payment = Payment(
                order_id=order_id,
                tenant_id=tenant_id,
                seller_id=seller_id,
                customer_id=customer_id,
                gateway_type=PaymentGatewayType.TTC_GATEWAY.value,
                status=PaymentStatus.SUCCEEDED.value,
                currency="USD",
                amount=Decimal("80.00"),
                gateway_fee=Decimal("2.40"),
                gateway_tax=Decimal("0.43"),
                ttc_commission=Decimal("8.00"),
                ttc_commission_tax=Decimal("1.44"),
                retained_amount=Decimal("80.00"),
                paid_at=func.now(),
            )
            refund = Refund(
                tenant_id=tenant_id,
                payment=payment,
                amount=Decimal("20.00"),
                reason="Partial return",
                commission_deduction=Decimal("2.00"),
            )
            db.add_all([tenant, seller, branch, customer, order, payment, refund])
            db.commit()
            db.refresh(order)
            db.refresh(payment)

            assert order.payment is not None
            assert order.payment.id == payment.id
            assert len(payment.refunds) == 1
            assert payment.refunds[0].amount == Decimal("20.00")
            assert payment.refunds[0].commission_deduction == Decimal("2.00")


class TestBillingAndSettlementModelsAndSchemas:
    """Tests for Billing Invoice and Settlement models and schemas."""

    def test_invoice_and_settlement_status_enums(self):
        assert InvoiceStatus.PENDING.value == "PENDING"
        assert InvoiceStatus.PAID.value == "PAID"
        assert InvoiceStatus.OVERDUE.value == "OVERDUE"
        assert InvoiceStatus.CANCELLED.value == "CANCELLED"

        assert SettlementStatus.SCHEDULED.value == "SCHEDULED"
        assert SettlementStatus.PROCESSING.value == "PROCESSING"
        assert SettlementStatus.SETTLED.value == "SETTLED"
        assert SettlementStatus.FAILED.value == "FAILED"

    def test_billing_invoice_month_validation(self):
        now = datetime.now(timezone.utc)
        inv = BillingInvoiceResponse(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            seller_id=uuid.uuid4(),
            invoice_month="2026-09",
            due_date=date(2026, 9, 15),
            status=InvoiceStatus.PENDING,
            currency="USD",
            subtotal=Decimal("150.00"),
            tax_total=Decimal("27.00"),
            penalty_total=Decimal("0.00"),
            total_amount=Decimal("177.00"),
            created_at=now,
            updated_at=now,
        )
        assert inv.invoice_month == "2026-09"

        with pytest.raises(ValidationError):
            BillingInvoiceResponse(
                id=uuid.uuid4(),
                tenant_id=uuid.uuid4(),
                seller_id=uuid.uuid4(),
                invoice_month="invalid-month",
                due_date=date(2026, 9, 15),
                status=InvoiceStatus.PENDING,
                currency="USD",
                subtotal=Decimal("150.00"),
                tax_total=Decimal("27.00"),
                penalty_total=Decimal("0.00"),
                total_amount=Decimal("177.00"),
                created_at=now,
                updated_at=now,
            )

    def test_settlement_response_schema(self):
        now = datetime.now(timezone.utc)
        settlement = SettlementResponse(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            seller_id=uuid.uuid4(),
            gateway_type=PaymentGatewayType.TTC_GATEWAY,
            status=SettlementStatus.SCHEDULED,
            currency="USD",
            amount=Decimal("450.00"),
            scheduled_for=date(2026, 9, 21),
            created_at=now,
            updated_at=now,
        )
        assert settlement.status == SettlementStatus.SCHEDULED
        assert settlement.amount == Decimal("450.00")

    def test_billing_and_settlement_sqlalchemy_models(self):
        tenant_id = uuid.uuid4()
        seller_id = uuid.uuid4()

        with SessionLocal() as db:
            tenant = Tenant(id=tenant_id, name="Billing Tenant", slug="bill-tenant")
            seller = Seller(id=seller_id, tenant_id=tenant_id, business_name="Bill Seller", slug="bill-seller")
            invoice = SellerBillingInvoice(
                tenant_id=tenant_id,
                seller_id=seller_id,
                invoice_month="2026-09",
                due_date=date(2026, 9, 15),
                status=InvoiceStatus.PENDING.value,
                currency="USD",
                subtotal=Decimal("200.00"),
                tax_total=Decimal("36.00"),
                penalty_total=Decimal("0.00"),
                total_amount=Decimal("236.00"),
            )
            settlement = SellerSettlement(
                tenant_id=tenant_id,
                seller_id=seller_id,
                gateway_type=PaymentGatewayType.TTC_GATEWAY.value,
                status=SettlementStatus.SCHEDULED.value,
                currency="USD",
                amount=Decimal("500.00"),
                scheduled_for=date(2026, 9, 21),
            )
            db.add_all([tenant, seller, invoice, settlement])
            db.commit()
            db.refresh(invoice)
            db.refresh(settlement)

            assert invoice.id is not None
            assert invoice.invoice_month == "2026-09"
            assert settlement.id is not None
            assert settlement.status == SettlementStatus.SCHEDULED.value


class TestOrderReselectionAndRBAC:
    """Tests for Order reselection linkages and RBAC permissions."""

    def test_order_reselection_model_and_schema(self):
        tenant_id = uuid.uuid4()
        seller_a_id = uuid.uuid4()
        seller_b_id = uuid.uuid4()
        branch_a_id = uuid.uuid4()
        branch_b_id = uuid.uuid4()
        customer_id = uuid.uuid4()
        order_1_id = uuid.uuid4()
        order_2_id = uuid.uuid4()

        with SessionLocal() as db:
            tenant = Tenant(id=tenant_id, name="Reselect Tenant", slug="reselect-tenant")
            seller_a = Seller(id=seller_a_id, tenant_id=tenant_id, business_name="Seller A", slug="seller-a")
            seller_b = Seller(id=seller_b_id, tenant_id=tenant_id, business_name="Seller B", slug="seller-b")
            branch_a = Branch(id=branch_a_id, tenant_id=tenant_id, seller_id=seller_a_id, name="Branch A", code="BA-01")
            branch_b = Branch(id=branch_b_id, tenant_id=tenant_id, seller_id=seller_b_id, name="Branch B", code="BB-01")
            user = User(id=uuid.uuid4(), auth_user_id=f"auth-{uuid.uuid4().hex[:6]}", email=f"reselect-{uuid.uuid4().hex[:6]}@cust.com")
            db.add(user)
            db.flush()
            customer = Customer(id=customer_id, user_id=user.id, email=user.email, first_name="Sam", last_name="Smith")

            order_1 = Order(
                id=order_1_id,
                tenant_id=tenant_id,
                seller_id=seller_a_id,
                branch_id=branch_a_id,
                customer_id=customer_id,
                order_number="ORD-RES-001",
                status=OrderStatus.CANCELLED.value,
                cancellation_reason="SELLER_RESTRICTED",
                currency="USD",
                subtotal=Decimal("40.00"),
                grand_total=Decimal("40.00"),
                pricing_snapshot={},
                catalog_snapshot={},
                customer_snapshot={},
            )
            order_2 = Order(
                id=order_2_id,
                tenant_id=tenant_id,
                seller_id=seller_b_id,
                branch_id=branch_b_id,
                customer_id=customer_id,
                order_number="ORD-RES-002",
                status=OrderStatus.PENDING.value,
                reselected_from_order_id=order_1_id,
                currency="USD",
                subtotal=Decimal("40.00"),
                grand_total=Decimal("40.00"),
                pricing_snapshot={},
                catalog_snapshot={},
                customer_snapshot={},
            )
            db.add_all([tenant, seller_a, seller_b, branch_a, branch_b, customer, order_1, order_2])
            db.commit()
            db.refresh(order_2)

            assert order_2.reselected_from_order_id == order_1.id
            assert order_2.reselected_from_order.id == order_1.id

        reselect_req = OrderReselectRequest(
            new_seller_id=seller_b_id,
            new_branch_id=branch_b_id,
        )
        assert reselect_req.new_seller_id == seller_b_id
        assert reselect_req.new_branch_id == branch_b_id

    def test_rbac_phase7_permissions_registered(self):
        expected_perms = [
            PermissionName.COMMERCIAL_READ.value,
            PermissionName.COMMERCIAL_MANAGE.value,
            PermissionName.PAYMENT_READ.value,
            PermissionName.PAYMENT_PROCESS.value,
            PermissionName.BILLING_READ.value,
            PermissionName.BILLING_MANAGE.value,
            PermissionName.SETTLEMENT_READ.value,
            PermissionName.SETTLEMENT_PROCESS.value,
        ]
        for p in expected_perms:
            assert p in PERMISSION_DESCRIPTIONS

        assert RoleName.CUSTOMER.value in ROLE_DESCRIPTIONS
        assert RoleName.CUSTOMER.value in DEFAULT_ROLE_PERMISSIONS

        customer_perms = set(DEFAULT_ROLE_PERMISSIONS[RoleName.CUSTOMER.value])
        assert PermissionName.ORDER_READ.value in customer_perms
        assert PermissionName.ORDER_CANCEL.value in customer_perms
        assert PermissionName.PAYMENT_READ.value in customer_perms
        assert PermissionName.PAYMENT_PROCESS.value in customer_perms
        # Customer must NOT have commercial or billing access
        assert PermissionName.COMMERCIAL_MANAGE.value not in customer_perms
        assert PermissionName.BILLING_READ.value not in customer_perms
        assert PermissionName.SETTLEMENT_PROCESS.value not in customer_perms

        # Platform Admin must have all 8 permissions
        platform_admin_perms = set(DEFAULT_ROLE_PERMISSIONS[RoleName.PLATFORM_ADMIN.value])
        for p in expected_perms:
            assert p in platform_admin_perms
