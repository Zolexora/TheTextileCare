"""Unit tests for Phase 7 Multi-Tenant Repositories."""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

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
from app.repositories.billing import BillingRepository
from app.repositories.commercial import CommercialRepository
from app.repositories.payment import PaymentRepository
from app.repositories.pickup import PickupRepository
from app.repositories.settlement import SettlementRepository


@pytest.fixture
def test_setup():
    """Sets up two tenants, sellers, branches, and customers for multi-tenant isolation testing."""
    with SessionLocal() as db:
        t1 = Tenant(name="Tenant Alpha", slug=f"t-alpha-{uuid.uuid4().hex[:6]}")
        t2 = Tenant(name="Tenant Beta", slug=f"t-beta-{uuid.uuid4().hex[:6]}")
        db.add_all([t1, t2])
        db.flush()

        s1 = Seller(tenant_id=t1.id, business_name="Seller Alpha", slug=f"s-alpha-{uuid.uuid4().hex[:6]}")
        s2 = Seller(tenant_id=t2.id, business_name="Seller Beta", slug=f"s-beta-{uuid.uuid4().hex[:6]}")
        db.add_all([s1, s2])
        db.flush()

        b1 = Branch(tenant_id=t1.id, seller_id=s1.id, name="Branch A1", code=f"BA1-{uuid.uuid4().hex[:4]}")
        b2 = Branch(tenant_id=t2.id, seller_id=s2.id, name="Branch B1", code=f"BB1-{uuid.uuid4().hex[:4]}")
        db.add_all([b1, b2])
        db.flush()

        u1 = User(auth_user_id=f"auth-{uuid.uuid4().hex[:6]}", email=f"u1-{uuid.uuid4().hex[:6]}@cust.com")
        u2 = User(auth_user_id=f"auth-{uuid.uuid4().hex[:6]}", email=f"u2-{uuid.uuid4().hex[:6]}@cust.com")
        db.add_all([u1, u2])
        db.flush()

        c1 = Customer(user_id=u1.id, email=u1.email, first_name="Cust", last_name="One")
        c2 = Customer(user_id=u2.id, email=u2.email, first_name="Cust", last_name="Two")
        db.add_all([c1, c2])
        db.flush()

        o1 = Order(
            tenant_id=t1.id,
            seller_id=s1.id,
            branch_id=b1.id,
            customer_id=c1.id,
            order_number=f"ORD-A-{uuid.uuid4().hex[:6]}",
            status=OrderStatus.PENDING.value,
            currency="USD",
            subtotal=Decimal("100.00"),
            grand_total=Decimal("100.00"),
            pricing_snapshot={},
            catalog_snapshot={},
            customer_snapshot={},
        )
        o2 = Order(
            tenant_id=t2.id,
            seller_id=s2.id,
            branch_id=b2.id,
            customer_id=c2.id,
            order_number=f"ORD-B-{uuid.uuid4().hex[:6]}",
            status=OrderStatus.PENDING.value,
            currency="USD",
            subtotal=Decimal("200.00"),
            grand_total=Decimal("200.00"),
            pricing_snapshot={},
            catalog_snapshot={},
            customer_snapshot={},
        )
        db.add_all([o1, o2])
        db.commit()

        return {
            "t1": t1, "t2": t2,
            "s1": s1, "s2": s2,
            "b1": b1, "b2": b2,
            "c1": c1, "c2": c2,
            "o1": o1, "o2": o2,
        }


class TestCommercialRepository:
    """Tests for CommercialRepository."""

    def test_create_and_multi_tenant_isolation(self, test_setup):
        data = test_setup
        with SessionLocal() as db:
            repo = CommercialRepository(db)
            cfg1 = repo.create(SellerCommercialConfiguration(
                tenant_id=data["t1"].id,
                seller_id=data["s1"].id,
                commercial_model=SellerCommercialModel.COMMISSION.value,
                commission_rate_percent=Decimal("10.00"),
                subscription_fee=Decimal("0.00"),
            ))
            db.commit()

            # Scoped fetch for correct tenant returns config
            res = repo.get_by_seller_id(tenant_id=data["t1"].id, seller_id=data["s1"].id)
            assert res is not None
            assert res.seller_id == data["s1"].id

            # Cross-tenant query must return None (isolation)
            cross_res = repo.get_by_seller_id(tenant_id=data["t2"].id, seller_id=data["s1"].id)
            assert cross_res is None

    def test_update_and_restriction_management(self, test_setup):
        data = test_setup
        with SessionLocal() as db:
            repo = CommercialRepository(db)
            repo.create(SellerCommercialConfiguration(
                tenant_id=data["t1"].id,
                seller_id=data["s1"].id,
                commercial_model=SellerCommercialModel.COMMISSION.value,
                commission_rate_percent=Decimal("10.00"),
            ))
            db.commit()

            # Cross-tenant update must return None
            fail_upd = repo.update(tenant_id=data["t2"].id, seller_id=data["s1"].id, commission_rate_percent=Decimal("15.00"))
            assert fail_upd is None

            # Valid tenant update
            succ_upd = repo.update(tenant_id=data["t1"].id, seller_id=data["s1"].id, commission_rate_percent=Decimal("15.00"))
            assert succ_upd is not None
            assert succ_upd.commission_rate_percent == Decimal("15.00")

            # Update restriction level
            repo.update_restriction_level(data["s1"].id, SellerRestrictionLevel.MARKETPLACE_RESTRICTED.value)
            db.commit()

            restricted = repo.list_restricted_sellers()
            assert len(restricted) == 1
            assert restricted[0].seller_id == data["s1"].id


class TestPickupRepository:
    """Tests for PickupRepository."""

    def test_pickup_lifecycle_and_customer_approval(self, test_setup):
        data = test_setup
        with SessionLocal() as db:
            repo = PickupRepository(db)
            pickup = repo.create(OrderPickup(
                tenant_id=data["t1"].id,
                seller_id=data["s1"].id,
                order_id=data["o1"].id,
                status=PickupStatus.SCHEDULED.value,
            ))
            db.commit()

            # Cross-tenant lookup fails
            assert repo.get_by_order_id(data["o1"].id, tenant_id=data["t2"].id) is None

            # Correct tenant lookup succeeds
            found = repo.get_by_order_id(data["o1"].id, tenant_id=data["t1"].id)
            assert found is not None
            assert found.status == PickupStatus.SCHEDULED.value

            # Seller submits verified details
            submitted = repo.submit_actual_details(
                order_id=data["o1"].id,
                tenant_id=data["t1"].id,
                actual_details={"suits": 2, "shirts": 1},
            )
            assert submitted is not None
            assert submitted.status == PickupStatus.DETAILS_SUBMITTED.value
            assert submitted.details_submitted_at is not None

            # Cross-customer approval fails
            cross_approve = repo.approve_details(order_id=data["o1"].id, customer_id=data["c2"].id)
            assert cross_approve is None

            # Customer 1 approves details
            approved = repo.approve_details(order_id=data["o1"].id, customer_id=data["c1"].id)
            assert approved is not None
            assert approved.status == PickupStatus.APPROVED.value
            assert approved.approved_at is not None

            # Seller completes pickup
            completed = repo.complete_pickup(order_id=data["o1"].id, tenant_id=data["t1"].id)
            assert completed is not None
            assert completed.status == PickupStatus.COMPLETED.value


class TestPaymentRepository:
    """Tests for PaymentRepository."""

    def test_cooling_hold_and_settlement_batching(self, test_setup):
        data = test_setup
        now = datetime.now(timezone.utc)
        with SessionLocal() as db:
            repo = PaymentRepository(db)

            # Payment 1: paid 20 days ago (cooling cleared)
            p1 = repo.create(Payment(
                tenant_id=data["t1"].id,
                seller_id=data["s1"].id,
                customer_id=data["c1"].id,
                order_id=data["o1"].id,
                gateway_type="TTC_GATEWAY",
                status=PaymentStatus.SUCCEEDED.value,
                currency="USD",
                amount=Decimal("100.00"),
                retained_amount=Decimal("100.00"),
                settled=False,
                paid_at=now - timedelta(days=20),
            ))

            # Payment 2: for Tenant 2 / Seller 2 (isolation check)
            p2 = repo.create(Payment(
                tenant_id=data["t2"].id,
                seller_id=data["s2"].id,
                customer_id=data["c2"].id,
                order_id=data["o2"].id,
                gateway_type="TTC_GATEWAY",
                status=PaymentStatus.SUCCEEDED.value,
                currency="USD",
                amount=Decimal("200.00"),
                retained_amount=Decimal("200.00"),
                settled=False,
                paid_at=now - timedelta(days=20),
            ))
            db.commit()

            # Target cooling cutoff = now - 15 days
            cooling_cutoff = now - timedelta(days=15)
            eligible_t1 = repo.get_eligible_cooling_payments(
                seller_id=data["s1"].id,
                tenant_id=data["t1"].id,
                cooling_cutoff=cooling_cutoff,
            )
            assert len(eligible_t1) == 1
            assert eligible_t1[0].id == p1.id

            # Batch mark settled
            dummy_settlement_id = uuid.uuid4()
            marked = repo.mark_settled([p1.id], settlement_id=dummy_settlement_id)
            assert marked == 1
            db.commit()

            # Now p1 is settled, so eligible query returns 0
            eligible_after = repo.get_eligible_cooling_payments(
                seller_id=data["s1"].id,
                tenant_id=data["t1"].id,
                cooling_cutoff=cooling_cutoff,
            )
            assert len(eligible_after) == 0

    def test_refund_and_retained_commission_update(self, test_setup):
        data = test_setup
        with SessionLocal() as db:
            repo = PaymentRepository(db)
            p = repo.create(Payment(
                tenant_id=data["t1"].id,
                seller_id=data["s1"].id,
                customer_id=data["c1"].id,
                order_id=data["o1"].id,
                gateway_type="TTC_GATEWAY",
                status=PaymentStatus.SUCCEEDED.value,
                currency="USD",
                amount=Decimal("100.00"),
                ttc_commission=Decimal("10.00"),
                ttc_commission_tax=Decimal("1.80"),
                retained_amount=Decimal("100.00"),
            ))
            db.commit()

            # Issue partial refund of $30 with $3 commission clawback
            refund = repo.create_refund(Refund(
                tenant_id=data["t1"].id,
                payment_id=p.id,
                amount=Decimal("30.00"),
                reason="Customer returned 1 item",
                commission_deduction=Decimal("3.00"),
            ))
            updated_p = repo.update_retained_commission(
                payment_id=p.id,
                refunded_amount=Decimal("30.00"),
                retained_amount=Decimal("70.00"),
                ttc_commission=Decimal("7.00"),
                ttc_commission_tax=Decimal("1.26"),
                status=PaymentStatus.PARTIALLY_REFUNDED.value,
            )
            db.commit()

            assert updated_p is not None
            assert updated_p.status == PaymentStatus.PARTIALLY_REFUNDED.value
            assert updated_p.retained_amount == Decimal("70.00")
            assert updated_p.ttc_commission == Decimal("7.00")

            refunds = repo.list_refunds_for_payment(p.id)
            assert len(refunds) == 1
            assert refunds[0].amount == Decimal("30.00")


class TestBillingRepository:
    """Tests for BillingRepository."""

    def test_monthly_invoice_and_overdue_penalty_calculation(self, test_setup):
        data = test_setup
        with SessionLocal() as db:
            repo = BillingRepository(db)
            inv = repo.create(SellerBillingInvoice(
                tenant_id=data["t1"].id,
                seller_id=data["s1"].id,
                invoice_month="2026-08",
                due_date=date(2026, 8, 15),
                status=InvoiceStatus.PENDING.value,
                currency="USD",
                subtotal=Decimal("100.00"),
                tax_total=Decimal("18.00"),
                penalty_total=Decimal("0.00"),
                total_amount=Decimal("118.00"),
            ))
            db.commit()

            # Idempotent lookup by month
            lookup = repo.get_by_seller_and_month(
                seller_id=data["s1"].id,
                tenant_id=data["t1"].id,
                invoice_month="2026-08",
            )
            assert lookup is not None
            assert lookup.id == inv.id

            # Cross-tenant query returns None
            assert repo.get_by_seller_and_month(
                seller_id=data["s1"].id,
                tenant_id=data["t2"].id,
                invoice_month="2026-08",
            ) is None

            # Overdue calculation as of 2026-08-25 (10 days past due)
            overdue_list = repo.get_overdue_invoices(as_of_date=date(2026, 8, 25))
            assert len(overdue_list) >= 1

            max_days = repo.get_max_overdue_days_for_seller(data["s1"].id, as_of_date=date(2026, 8, 25))
            assert max_days == 10

            # Update penalty
            penalty_amount = Decimal("1.18")
            repo.update_penalty(
                invoice_id=inv.id,
                penalty_total=penalty_amount,
                total_amount=Decimal("119.18"),
                status=InvoiceStatus.OVERDUE.value,
            )
            db.commit()

            updated = repo.get_by_id(inv.id)
            assert updated.status == InvoiceStatus.OVERDUE.value
            assert updated.penalty_total == Decimal("1.18")
            assert updated.total_amount == Decimal("119.18")


class TestSettlementRepository:
    """Tests for SettlementRepository."""

    def test_settlement_disbursement_lifecycle(self, test_setup):
        data = test_setup
        monday = date(2026, 9, 21)
        with SessionLocal() as db:
            repo = SettlementRepository(db)
            settlement = repo.create(SellerSettlement(
                tenant_id=data["t1"].id,
                seller_id=data["s1"].id,
                gateway_type=PaymentGatewayType.TTC_GATEWAY.value,
                status=SettlementStatus.SCHEDULED.value,
                currency="USD",
                amount=Decimal("750.00"),
                scheduled_for=monday,
            ))
            db.commit()

            # Query scheduled for target Monday
            scheduled = repo.get_scheduled_for_date(scheduled_for=monday, status=SettlementStatus.SCHEDULED.value)
            assert len(scheduled) >= 1
            assert any(s.id == settlement.id for s in scheduled)

            # Process payout
            ref_code = "BANK-PAYOUT-7890"
            updated = repo.update_status(
                settlement_id=settlement.id,
                status=SettlementStatus.SETTLED.value,
                reference_id=ref_code,
            )
            db.commit()

            assert updated is not None
            assert updated.status == SettlementStatus.SETTLED.value
            assert updated.reference_id == ref_code
            assert updated.processed_at is not None
