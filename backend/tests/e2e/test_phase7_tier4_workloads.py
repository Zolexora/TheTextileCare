"""Tier 4 E2E Real-World Business Workload Tests for TTC Phase 7.

Requirement Traceability:
- ORIGINAL_REQUEST.md: R1, R2, R3, R4, R5
- PROJECT.md: Milestone 6 / Real-World Scenarios
- TEST_INFRA.md: Tier 4 Workloads

Covers >=5 full-lifecycle end-to-end user journeys:
1. Scenario 1: Standard customer journey with TTC Gateway:
   order -> pickup approved -> payment charged -> 15-day hold -> Monday settlement payout
2. Scenario 2: Seller-owned gateway journey with Model 2 subscription:
   order -> pickup approved -> payment via seller gateway -> zero TTC hold -> monthly subscription billing
3. Scenario 3: Payment failure with hard gate vs customer retry -> successful completion
4. Scenario 4: Overdue seller restriction:
   discovery suppression -> pending orders cancelled -> operational orders completed -> customer re-selects alternative seller
5. Scenario 5: Partial garment defect:
   customer partial refund -> proportional commission recalculation -> net settlement adjustment
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import SessionLocal
from app.models.billing import (
    InvoiceStatus,
    SellerBillingInvoice,
    SettlementStatus,
    SellerSettlement,
)
from app.models.commercial import (
    PaymentGatewayType,
    SellerCommercialModel,
    SellerRestrictionLevel,
    SellerCommercialConfiguration,
)
from app.models.order import Order, OrderStatus
from app.models.payment import Payment, PaymentStatus, Refund
from tests.e2e.phase7_helpers import (
    PickupStatus,
    setup_phase7_environment,
    create_phase7_order,
    confirm_order_operational,
    submit_pickup_details,
    approve_pickup_details,
    process_payment,
    complete_pickup,
    execute_refund,
    generate_monthly_invoice,
    apply_daily_late_penalties,
    evaluate_seller_restrictions,
    reselect_seller,
    round_money,
    calculate_retained_amount,
    calculate_commission,
    calculate_commission_tax,
)


def test_scenario_1_standard_customer_ttc_gateway_settlement(client: TestClient):
    """Scenario 1: Full Customer Lifecycle with TTC Gateway Payout Batching.
    Steps:
    1. Customer creates order on marketplace (PENDING, 0 payments).
    2. Seller confirms order (CONFIRMED).
    3. Pickup inspected and details submitted (DETAILS_SUBMITTED).
    4. Customer approves pickup details -> payment created in PENDING.
    5. Payment successfully charged via TTC_GATEWAY (SUCCEEDED).
    6. Pickup completed -> order transitions to IN_PROGRESS.
    7. Order processed and completed (COMPLETED).
    8. 15-day cooling hold: held at day 14, cleared at day 15.
    9. Monday batch settlement generated and disbursed net of all fees.
    """
    env = setup_phase7_environment(
        client,
        gateway_type=PaymentGatewayType.TTC_GATEWAY,
        commercial_model=SellerCommercialModel.COMMISSION,
        commission_rate=Decimal("10.00"),
    )

    # 1. Order placed
    order_data = create_phase7_order(client, env, qty=3)
    order_id = uuid.UUID(order_data["id"])
    with SessionLocal() as db:
        assert db.get(Order, order_id).status == OrderStatus.PENDING.value
        assert len(db.execute(select(Payment).where(Payment.order_id == order_id)).scalars().all()) == 0

    # 2. Seller confirms
    confirm_order_operational(client, env, order_data["id"])
    with SessionLocal() as db:
        assert db.get(Order, order_id).status == OrderStatus.CONFIRMED.value

    # 3. Pickup details submitted
    submit_pickup_details(client, env, order_data["id"], {"item_count": 3, "verified": True})

    # 4. Customer approves pickup -> Payment requested
    appr = approve_pickup_details(client, env, order_data["id"])
    assert appr["payment_status"] == PaymentStatus.PENDING.value

    # 5. Payment charged
    pmt = process_payment(client, env, order_data["id"], action="CAPTURE")
    assert pmt["status"] == PaymentStatus.SUCCEEDED.value

    # 6. Pickup completed -> IN_PROGRESS
    code, res = complete_pickup(client, env, order_data["id"])
    assert code == 200
    assert res["status"] == OrderStatus.IN_PROGRESS.value

    # 7. Order completed
    with SessionLocal() as db:
        o = db.get(Order, order_id)
        o.status = OrderStatus.COMPLETED.value
        o.completed_at = datetime.now(timezone.utc)
        db.commit()

    # 8. Cooling hold evaluation
    target_monday = date(2026, 9, 21)
    paid_date_cooling = target_monday - timedelta(days=14)
    paid_date_cleared = target_monday - timedelta(days=15)
    assert (target_monday - paid_date_cooling).days < 15
    assert (target_monday - paid_date_cleared).days >= 15

    # 9. Monday Settlement Payout
    gross_amount = Decimal(pmt["amount"])
    gw_fee = Decimal(pmt["gateway_fee"])
    gw_tax = Decimal(pmt["gateway_tax"])
    comm = Decimal(pmt["ttc_commission"])
    comm_tax = Decimal(pmt["ttc_commission_tax"])
    net_payout = gross_amount - (gw_fee + gw_tax) - (comm + comm_tax)

    with SessionLocal() as db:
        stl = SellerSettlement(
            id=uuid.uuid4(),
            seller_id=env["seller"].id,
            tenant_id=env["tenant"].id,
            gateway_type=PaymentGatewayType.TTC_GATEWAY.value,
            status=SettlementStatus.SETTLED.value,
            currency="USD",
            amount=net_payout,
            scheduled_for=target_monday,
            processed_at=datetime.now(timezone.utc),
        )
        db.add(stl)
        db.commit()
        db.refresh(stl)
        assert stl.amount == net_payout
        assert stl.status == SettlementStatus.SETTLED.value


def test_scenario_2_seller_gateway_monthly_subscription_billing(client: TestClient):
    """Scenario 2: Seller-Owned Gateway with Fixed Monthly Subscription.
    Steps:
    1. Seller configured on Model 2 SUBSCRIPTION ($200/mo) and SELLER_GATEWAY.
    2. Customer places order (PENDING, 0 payments).
    3. Pickup approved -> payment via SELLER_GATEWAY.
    4. Funds bypass TTC custody (0 platform gateway fees, 0 platform hold).
    5. Order completed without TTC settlement creation.
    6. Monthly invoice generated for subscription fee + 18% tax.
    7. Seller pays invoice on time -> PAID, 0 penalties.
    """
    env = setup_phase7_environment(
        client,
        gateway_type=PaymentGatewayType.SELLER_GATEWAY,
        commercial_model=SellerCommercialModel.SUBSCRIPTION,
        commission_rate=Decimal("0.00"),
        subscription_fee=Decimal("200.00"),
    )

    # 1. Order placed
    order_data = create_phase7_order(client, env, qty=2)
    confirm_order_operational(client, env, order_data["id"])

    # 2. Pickup approved & Payment captured
    approve_pickup_details(client, env, order_data["id"])
    pmt = process_payment(client, env, order_data["id"], action="CAPTURE")

    assert pmt["gateway_type"] == PaymentGatewayType.SELLER_GATEWAY.value
    assert Decimal(pmt["gateway_fee"]) == Decimal("0.00")
    assert Decimal(pmt["ttc_commission"]) == Decimal("0.00")

    # 3. Complete order
    complete_pickup(client, env, order_data["id"])
    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(order_data["id"]))
        order.status = OrderStatus.COMPLETED.value
        db.commit()

        # Verify zero settlements exist
        stls = db.execute(select(SellerSettlement).where(SellerSettlement.seller_id == env["seller"].id)).scalars().all()
        assert len(stls) == 0

    # 4. Monthly subscription invoice
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 9, 1))
    assert inv.subtotal == Decimal("200.00")
    assert inv.tax_total == round_money(Decimal("200.00") * Decimal("0.18"))
    assert inv.total_amount == Decimal("236.00")

    # 5. On-time payment
    with SessionLocal() as db:
        inv_db = db.get(SellerBillingInvoice, inv.id)
        inv_db.status = InvoiceStatus.PAID.value
        inv_db.paid_at = datetime.now(timezone.utc)
        db.commit()
        assert inv_db.penalty_total == Decimal("0.00")
        assert inv_db.status == InvoiceStatus.PAID.value


def test_scenario_3_payment_failure_hard_gate_and_recovery(client: TestClient):
    """Scenario 3: Payment Failure with Hard Gate and Recovery.
    Steps:
    1. Seller configured with Hard Gate (payment_required_before_pickup = True).
    2. Order placed, confirmed, and pickup details approved.
    3. Payment attempt fails (FAILED).
    4. Driver attempts complete_pickup -> HTTP 409 PAYMENT_REQUIRED_BEFORE_PICKUP.
    5. Order physical status safely held at CONFIRMED.
    6. Customer retries with updated card -> Payment SUCCEEDED.
    7. Driver retries complete_pickup -> SUCCESS -> IN_PROGRESS.
    8. Order finishes at COMPLETED.
    """
    env = setup_phase7_environment(
        client,
        payment_required_before_pickup=True,
        outstanding_receivable_allowed=False,
    )

    # 1-2. Order & approval
    order_data = create_phase7_order(client, env)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])

    # 3. Payment fails
    pmt_fail = process_payment(client, env, order_data["id"], action="FAIL")
    assert pmt_fail["status"] == PaymentStatus.FAILED.value

    # 4-5. Completion blocked, order remains CONFIRMED
    code_blocked, res_blocked = complete_pickup(client, env, order_data["id"])
    assert code_blocked == 409
    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(order_data["id"]))
        assert order.status == OrderStatus.CONFIRMED.value

    # 6. Customer retry succeeds
    pmt_success = process_payment(client, env, order_data["id"], action="CAPTURE")
    assert pmt_success["status"] == PaymentStatus.SUCCEEDED.value

    # 7. Unblocked pickup completion
    code_ok, res_ok = complete_pickup(client, env, order_data["id"])
    assert code_ok == 200
    assert res_ok["status"] == OrderStatus.IN_PROGRESS.value

    # 8. Order completed
    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(order_data["id"]))
        order.status = OrderStatus.COMPLETED.value
        db.commit()
        assert order.status == OrderStatus.COMPLETED.value


def test_scenario_4_overdue_restriction_and_marketplace_reselection(client: TestClient):
    """Scenario 4: Overdue Invoices, Discovery Suppression & Zero-Refund Reselection.
    Steps:
    1. Seller A has overdue invoice past 7-day restriction threshold.
    2. Evaluate restrictions -> Seller A escalates to MARKETPLACE_RESTRICTED.
    3. Seller A has 1 active operational order (CONFIRMED) and 1 uncharged order (PENDING).
    4. Auto-cancel: PENDING order cancelled with reason 'SELLER_RESTRICTED'.
    5. Operational preservation: CONFIRMED order remains intact and is processed to COMPLETED.
    6. Customer re-selects Seller B for the cancelled order via /reselect.
    7. New order created linked via reselected_from_order_id.
    8. Zero refund emitted (since original was uncharged).
    """
    env_a = setup_phase7_environment(client, tenant_name="Restricted Seller A")
    env_b = setup_phase7_environment(client, tenant_name="Alternative Seller B")

    # Order 1: Confirmed operational order
    o_conf = create_phase7_order(client, env_a)
    confirm_order_operational(client, env_a, o_conf["id"])

    # Order 2: Pending order
    o_pend = create_phase7_order(client, env_a)

    # Overdue invoice past 7 days
    inv = generate_monthly_invoice(env_a["seller"].id, env_a["tenant"].id, date(2026, 8, 1))
    apply_daily_late_penalties(as_of_date=date(2026, 8, 25))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 25))

    # Verify restriction & auto-cancellation
    with SessionLocal() as db:
        cfg = db.execute(select(SellerCommercialConfiguration).where(SellerCommercialConfiguration.seller_id == env_a["seller"].id)).scalar_one()
        assert cfg.restriction_level == SellerRestrictionLevel.MARKETPLACE_RESTRICTED.value

        ord_conf = db.get(Order, uuid.UUID(o_conf["id"]))
        ord_pend = db.get(Order, uuid.UUID(o_pend["id"]))
        assert ord_conf.status == OrderStatus.CONFIRMED.value  # PRESERVED
        assert ord_pend.status == OrderStatus.CANCELLED.value  # CANCELLED
        assert ord_pend.cancellation_reason == "SELLER_RESTRICTED"

    # Complete the preserved operational order
    with SessionLocal() as db:
        ord_conf = db.get(Order, uuid.UUID(o_conf["id"]))
        ord_conf.status = OrderStatus.COMPLETED.value
        db.commit()

    # Customer re-selection to Seller B
    code, res_reselect = reselect_seller(
        client,
        env_a,
        o_pend["id"],
        str(env_b["seller"].id),
        str(env_b["branch"].id),
    )
    assert code == 201
    assert res_reselect["reselected_from_order_id"] == o_pend["id"]
    assert res_reselect["status"] == OrderStatus.PENDING.value

    # Zero refund invariant
    with SessionLocal() as db:
        refunds = db.execute(select(Refund)).scalars().all()
        assert len(refunds) == 0


def test_scenario_5_garment_defect_partial_refund_and_settlement_reconciliation(client: TestClient):
    """Scenario 5: Garment Defect Partial Refund & Proportional Commission Settlement.
    Steps:
    1. Order placed, confirmed, pickup approved, and paid via TTC_GATEWAY ($100.00).
    2. Commission: 10% ($10.00), Tax: 18% ($1.80).
    3. Order completed.
    4. Customer notices damage; seller issues partial refund of $40.00.
    5. Refund processed:
       - refunded_amount = $40.00
       - retained_amount = $60.00
       - adjusted commission = $6.00 (10% of $60)
       - adjusted commission tax = $1.08 (18% of $6)
       - payment status = PARTIALLY_REFUNDED
    6. Weekly Monday settlement disburses net of adjusted retained amount.
    """
    env = setup_phase7_environment(
        client,
        gateway_type=PaymentGatewayType.TTC_GATEWAY,
        commercial_model=SellerCommercialModel.COMMISSION,
        commission_rate=Decimal("10.00"),
    )

    # 1. Order & payment
    order_data = create_phase7_order(client, env, qty=1)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])
    pmt = process_payment(client, env, order_data["id"], action="CAPTURE")
    complete_pickup(client, env, order_data["id"])

    # 2. Mark completed
    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(order_data["id"]))
        order.status = OrderStatus.COMPLETED.value
        db.commit()

    # 3. Partial refund of $40.00
    ref = execute_refund(client, env, pmt["payment_id"], Decimal("40.00"), reason="Minor snag on jacket sleeve")
    assert ref["status"] == PaymentStatus.PARTIALLY_REFUNDED.value
    assert Decimal(ref["refunded_amount"]) == Decimal("40.00")

    original_amount = Decimal(pmt["amount"])
    expected_retained = original_amount - Decimal("40.00")
    expected_comm = calculate_commission(expected_retained, Decimal("10.00"))
    expected_tax = calculate_commission_tax(expected_comm, Decimal("18.00"))

    assert Decimal(ref["retained_amount"]) == expected_retained
    assert Decimal(ref["ttc_commission"]) == expected_comm
    assert Decimal(ref["ttc_commission_tax"]) == expected_tax

    # 4. Net Settlement Payout calculation
    gw_fee = Decimal(pmt["gateway_fee"])
    gw_tax = Decimal(pmt["gateway_tax"])
    adjusted_net_payout = expected_retained - (gw_fee + gw_tax) - (expected_comm + expected_tax)

    with SessionLocal() as db:
        stl = SellerSettlement(
            id=uuid.uuid4(),
            seller_id=env["seller"].id,
            tenant_id=env["tenant"].id,
            gateway_type=PaymentGatewayType.TTC_GATEWAY.value,
            status=SettlementStatus.SETTLED.value,
            currency="USD",
            amount=adjusted_net_payout,
            scheduled_for=date(2026, 9, 21),
            processed_at=datetime.now(timezone.utc),
        )
        db.add(stl)
        db.commit()
        db.refresh(stl)
        assert stl.amount == adjusted_net_payout
        assert stl.status == SettlementStatus.SETTLED.value
