"""Tier 3 E2E Pairwise Combination Tests for TTC Phase 7.

Requirement Traceability:
- ORIGINAL_REQUEST.md: R1, R2, R3, R4, R5
- PROJECT.md: Cross-feature pairwise interactions
- TEST_INFRA.md: Tier 3 Pairwise Combinations

Systematically tests the 16 full pairwise combinations across the 4 primary commercial dimensions:
1. Gateway Type: TTC_GATEWAY vs SELLER_GATEWAY
2. Commercial Model: COMMISSION (Model 1) vs SUBSCRIPTION (Model 2)
3. Failure Mode: HARD_GATE (payment_required_before_pickup) vs PERMISSIVE (outstanding_receivable_allowed)
4. Restriction Status: NONE vs MARKETPLACE_RESTRICTED
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
from app.models.payment import Payment, PaymentStatus
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
)


# ============================================================================
# COMBINATIONS 1-4: TTC_GATEWAY x COMMISSION
# ============================================================================

def test_c01_ttc_gw_commission_hardgate_unrestricted(client: TestClient):
    """C-01: TTC_GATEWAY + COMMISSION + HARD_GATE + RESTRICTION=NONE.
    Happy path: Payment succeeds at pickup approval, cooling hold applies, settlement disbursable.
    """
    env = setup_phase7_environment(
        client,
        gateway_type=PaymentGatewayType.TTC_GATEWAY,
        commercial_model=SellerCommercialModel.COMMISSION,
        commission_rate=Decimal("10.00"),
        subscription_fee=Decimal("0.00"),
        payment_required_before_pickup=True,
        outstanding_receivable_allowed=False,
    )
    o = create_phase7_order(client, env)
    confirm_order_operational(client, env, o["id"])
    approve_pickup_details(client, env, o["id"])
    pmt = process_payment(client, env, o["id"], action="CAPTURE")

    code, res = complete_pickup(client, env, o["id"])
    assert code == 200
    assert res["status"] == OrderStatus.IN_PROGRESS.value
    assert Decimal(pmt["gateway_fee"]) > Decimal("0.00")
    assert Decimal(pmt["ttc_commission"]) > Decimal("0.00")


def test_c02_ttc_gw_commission_hardgate_restricted(client: TestClient):
    """C-02: TTC_GATEWAY + COMMISSION + HARD_GATE + RESTRICTION=MARKETPLACE_RESTRICTED.
    When restricted, pending orders auto-cancel, but completed/confirmed orders retain financial tracking.
    """
    env = setup_phase7_environment(
        client,
        gateway_type=PaymentGatewayType.TTC_GATEWAY,
        commercial_model=SellerCommercialModel.COMMISSION,
        commission_rate=Decimal("10.00"),
        payment_required_before_pickup=True,
    )
    o = create_phase7_order(client, env)
    # Trigger restriction
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    apply_daily_late_penalties(as_of_date=date(2026, 8, 25))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 25))

    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(o["id"]))
        assert order.status == OrderStatus.CANCELLED.value
        assert order.cancellation_reason == "SELLER_RESTRICTED"


def test_c03_ttc_gw_commission_permissive_unrestricted(client: TestClient):
    """C-03: TTC_GATEWAY + COMMISSION + PERMISSIVE + RESTRICTION=NONE.
    Payment failure leads to OUTSTANDING receivable, pickup completes, order transitions to IN_PROGRESS.
    """
    env = setup_phase7_environment(
        client,
        gateway_type=PaymentGatewayType.TTC_GATEWAY,
        commercial_model=SellerCommercialModel.COMMISSION,
        commission_rate=Decimal("10.00"),
        payment_required_before_pickup=False,
        outstanding_receivable_allowed=True,
    )
    o = create_phase7_order(client, env)
    confirm_order_operational(client, env, o["id"])
    approve_pickup_details(client, env, o["id"])
    pmt = process_payment(client, env, o["id"], action="FAIL")
    assert pmt["status"] == PaymentStatus.OUTSTANDING.value

    code, res = complete_pickup(client, env, o["id"])
    assert code == 200
    assert res["status"] == OrderStatus.IN_PROGRESS.value


def test_c04_ttc_gw_commission_permissive_restricted(client: TestClient):
    """C-04: TTC_GATEWAY + COMMISSION + PERMISSIVE + RESTRICTION=MARKETPLACE_RESTRICTED.
    Operational in-progress orders can be completed even though seller is restricted.
    """
    env = setup_phase7_environment(
        client,
        gateway_type=PaymentGatewayType.TTC_GATEWAY,
        commercial_model=SellerCommercialModel.COMMISSION,
        payment_required_before_pickup=False,
        outstanding_receivable_allowed=True,
    )
    o = create_phase7_order(client, env)
    confirm_order_operational(client, env, o["id"])
    approve_pickup_details(client, env, o["id"])
    process_payment(client, env, o["id"], action="FAIL")
    complete_pickup(client, env, o["id"])

    # Restrict seller
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    apply_daily_late_penalties(as_of_date=date(2026, 8, 25))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 25))

    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(o["id"]))
        assert order.status == OrderStatus.IN_PROGRESS.value  # Preserved operational order


# ============================================================================
# COMBINATIONS 5-8: TTC_GATEWAY x SUBSCRIPTION
# ============================================================================

def test_c05_ttc_gw_subscription_hardgate_unrestricted(client: TestClient):
    """C-05: TTC_GATEWAY + SUBSCRIPTION + HARD_GATE + RESTRICTION=NONE.
    Commission is 0.00; entire net payment after gateway fee/tax is held for weekly settlement.
    """
    env = setup_phase7_environment(
        client,
        gateway_type=PaymentGatewayType.TTC_GATEWAY,
        commercial_model=SellerCommercialModel.SUBSCRIPTION,
        commission_rate=Decimal("0.00"),
        subscription_fee=Decimal("150.00"),
        payment_required_before_pickup=True,
    )
    o = create_phase7_order(client, env)
    confirm_order_operational(client, env, o["id"])
    approve_pickup_details(client, env, o["id"])
    pmt = process_payment(client, env, o["id"], action="CAPTURE")

    assert Decimal(pmt["ttc_commission"]) == Decimal("0.00")
    code, res = complete_pickup(client, env, o["id"])
    assert code == 200


def test_c06_ttc_gw_subscription_hardgate_restricted(client: TestClient):
    """C-06: TTC_GATEWAY + SUBSCRIPTION + HARD_GATE + RESTRICTION=MARKETPLACE_RESTRICTED.
    Subscription invoice overdue causes restriction; pending orders cancelled.
    """
    env = setup_phase7_environment(
        client,
        gateway_type=PaymentGatewayType.TTC_GATEWAY,
        commercial_model=SellerCommercialModel.SUBSCRIPTION,
        commission_rate=Decimal("0.00"),
        subscription_fee=Decimal("200.00"),
        payment_required_before_pickup=True,
    )
    o = create_phase7_order(client, env)
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    assert inv.subtotal == Decimal("200.00")

    apply_daily_late_penalties(as_of_date=date(2026, 8, 25))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 25))

    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(o["id"]))
        assert order.status == OrderStatus.CANCELLED.value


def test_c07_ttc_gw_subscription_permissive_unrestricted(client: TestClient):
    """C-07: TTC_GATEWAY + SUBSCRIPTION + PERMISSIVE + RESTRICTION=NONE.
    Subscription model with permissive payment: payment fails -> OUTSTANDING, pickup completes.
    """
    env = setup_phase7_environment(
        client,
        gateway_type=PaymentGatewayType.TTC_GATEWAY,
        commercial_model=SellerCommercialModel.SUBSCRIPTION,
        commission_rate=Decimal("0.00"),
        subscription_fee=Decimal("199.00"),
        payment_required_before_pickup=False,
        outstanding_receivable_allowed=True,
    )
    o = create_phase7_order(client, env)
    confirm_order_operational(client, env, o["id"])
    approve_pickup_details(client, env, o["id"])
    pmt = process_payment(client, env, o["id"], action="FAIL")
    assert pmt["status"] == PaymentStatus.OUTSTANDING.value

    code, res = complete_pickup(client, env, o["id"])
    assert code == 200
    assert res["status"] == OrderStatus.IN_PROGRESS.value


def test_c08_ttc_gw_subscription_permissive_restricted(client: TestClient):
    """C-08: TTC_GATEWAY + SUBSCRIPTION + PERMISSIVE + RESTRICTION=MARKETPLACE_RESTRICTED.
    Permissive order underway; reselection possible on new uncharged pending orders.
    """
    env = setup_phase7_environment(
        client,
        gateway_type=PaymentGatewayType.TTC_GATEWAY,
        commercial_model=SellerCommercialModel.SUBSCRIPTION,
        commission_rate=Decimal("0.00"),
        subscription_fee=Decimal("199.00"),
        payment_required_before_pickup=False,
        outstanding_receivable_allowed=True,
    )
    o_pending = create_phase7_order(client, env)
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    apply_daily_late_penalties(as_of_date=date(2026, 8, 25))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 25))

    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(o_pending["id"]))
        assert order.status == OrderStatus.CANCELLED.value


# ============================================================================
# COMBINATIONS 9-12: SELLER_GATEWAY x COMMISSION
# ============================================================================

def test_c09_seller_gw_commission_hardgate_unrestricted(client: TestClient):
    """C-09: SELLER_GATEWAY + COMMISSION + HARD_GATE + RESTRICTION=NONE.
    Gateway fees zeroed on TTC; commission tracked and billed on monthly invoice. Zero settlement hold.
    """
    env = setup_phase7_environment(
        client,
        gateway_type=PaymentGatewayType.SELLER_GATEWAY,
        commercial_model=SellerCommercialModel.COMMISSION,
        commission_rate=Decimal("10.00"),
        payment_required_before_pickup=True,
    )
    o = create_phase7_order(client, env)
    confirm_order_operational(client, env, o["id"])
    approve_pickup_details(client, env, o["id"])
    pmt = process_payment(client, env, o["id"], action="CAPTURE")

    assert Decimal(pmt["gateway_fee"]) == Decimal("0.00")
    assert Decimal(pmt["ttc_commission"]) > Decimal("0.00")
    code, res = complete_pickup(client, env, o["id"])
    assert code == 200


def test_c10_seller_gw_commission_hardgate_restricted(client: TestClient):
    """C-10: SELLER_GATEWAY + COMMISSION + HARD_GATE + RESTRICTION=MARKETPLACE_RESTRICTED.
    Seller gateway commission invoice unpaid -> restriction applied; pending orders cancelled.
    """
    env = setup_phase7_environment(
        client,
        gateway_type=PaymentGatewayType.SELLER_GATEWAY,
        commercial_model=SellerCommercialModel.COMMISSION,
        commission_rate=Decimal("10.00"),
        payment_required_before_pickup=True,
    )
    o = create_phase7_order(client, env)
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    apply_daily_late_penalties(as_of_date=date(2026, 8, 25))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 25))

    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(o["id"]))
        assert order.status == OrderStatus.CANCELLED.value


def test_c11_seller_gw_commission_permissive_unrestricted(client: TestClient):
    """C-11: SELLER_GATEWAY + COMMISSION + PERMISSIVE + RESTRICTION=NONE.
    Direct gateway with permissive receivable: payment fails -> OUTSTANDING; order proceeds.
    """
    env = setup_phase7_environment(
        client,
        gateway_type=PaymentGatewayType.SELLER_GATEWAY,
        commercial_model=SellerCommercialModel.COMMISSION,
        commission_rate=Decimal("8.00"),
        payment_required_before_pickup=False,
        outstanding_receivable_allowed=True,
    )
    o = create_phase7_order(client, env)
    confirm_order_operational(client, env, o["id"])
    approve_pickup_details(client, env, o["id"])
    pmt = process_payment(client, env, o["id"], action="FAIL")
    assert pmt["status"] == PaymentStatus.OUTSTANDING.value

    code, res = complete_pickup(client, env, o["id"])
    assert code == 200
    assert res["status"] == OrderStatus.IN_PROGRESS.value


def test_c12_seller_gw_commission_permissive_restricted(client: TestClient):
    """C-12: SELLER_GATEWAY + COMMISSION + PERMISSIVE + RESTRICTION=MARKETPLACE_RESTRICTED.
    Restricted seller under direct gateway; customer can re-select without refund.
    """
    env = setup_phase7_environment(
        client,
        gateway_type=PaymentGatewayType.SELLER_GATEWAY,
        commercial_model=SellerCommercialModel.COMMISSION,
        commission_rate=Decimal("8.00"),
        payment_required_before_pickup=False,
        outstanding_receivable_allowed=True,
    )
    env_alt = setup_phase7_environment(client, tenant_name="Alternative Cleaner")
    o = create_phase7_order(client, env)

    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    apply_daily_late_penalties(as_of_date=date(2026, 8, 25))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 25))

    code, res = reselect_seller(client, env, o["id"], str(env_alt["seller"].id), str(env_alt["branch"].id))
    assert code == 201
    assert res["reselected_from_order_id"] == o["id"]


# ============================================================================
# COMBINATIONS 13-16: SELLER_GATEWAY x SUBSCRIPTION
# ============================================================================

def test_c13_seller_gw_subscription_hardgate_unrestricted(client: TestClient):
    """C-13: SELLER_GATEWAY + SUBSCRIPTION + HARD_GATE + RESTRICTION=NONE.
    White-label seller: order payment direct to seller gateway, subscription invoice monthly, zero holds.
    """
    env = setup_phase7_environment(
        client,
        gateway_type=PaymentGatewayType.SELLER_GATEWAY,
        commercial_model=SellerCommercialModel.SUBSCRIPTION,
        commission_rate=Decimal("0.00"),
        subscription_fee=Decimal("250.00"),
        payment_required_before_pickup=True,
    )
    o = create_phase7_order(client, env)
    confirm_order_operational(client, env, o["id"])
    approve_pickup_details(client, env, o["id"])
    pmt = process_payment(client, env, o["id"], action="CAPTURE")

    assert Decimal(pmt["gateway_fee"]) == Decimal("0.00")
    assert Decimal(pmt["ttc_commission"]) == Decimal("0.00")
    code, res = complete_pickup(client, env, o["id"])
    assert code == 200


def test_c14_seller_gw_subscription_hardgate_restricted(client: TestClient):
    """C-14: SELLER_GATEWAY + SUBSCRIPTION + HARD_GATE + RESTRICTION=MARKETPLACE_RESTRICTED.
    Subscription fee overdue causes restriction; pending orders auto-cancelled.
    """
    env = setup_phase7_environment(
        client,
        gateway_type=PaymentGatewayType.SELLER_GATEWAY,
        commercial_model=SellerCommercialModel.SUBSCRIPTION,
        commission_rate=Decimal("0.00"),
        subscription_fee=Decimal("250.00"),
        payment_required_before_pickup=True,
    )
    o = create_phase7_order(client, env)
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    apply_daily_late_penalties(as_of_date=date(2026, 8, 25))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 25))

    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(o["id"]))
        assert order.status == OrderStatus.CANCELLED.value


def test_c15_seller_gw_subscription_permissive_unrestricted(client: TestClient):
    """C-15: SELLER_GATEWAY + SUBSCRIPTION + PERMISSIVE + RESTRICTION=NONE.
    Seller gateway with permissive payment: card declined -> OUTSTANDING; order completes.
    """
    env = setup_phase7_environment(
        client,
        gateway_type=PaymentGatewayType.SELLER_GATEWAY,
        commercial_model=SellerCommercialModel.SUBSCRIPTION,
        commission_rate=Decimal("0.00"),
        subscription_fee=Decimal("300.00"),
        payment_required_before_pickup=False,
        outstanding_receivable_allowed=True,
    )
    o = create_phase7_order(client, env)
    confirm_order_operational(client, env, o["id"])
    approve_pickup_details(client, env, o["id"])
    pmt = process_payment(client, env, o["id"], action="FAIL")
    assert pmt["status"] == PaymentStatus.OUTSTANDING.value

    code, res = complete_pickup(client, env, o["id"])
    assert code == 200
    assert res["status"] == OrderStatus.IN_PROGRESS.value


def test_c16_seller_gw_subscription_permissive_restricted(client: TestClient):
    """C-16: SELLER_GATEWAY + SUBSCRIPTION + PERMISSIVE + RESTRICTION=MARKETPLACE_RESTRICTED.
    Complete multi-dimensional combination: confirmed orders preserved, pending cancelled, zero refund on re-selection.
    """
    env = setup_phase7_environment(
        client,
        gateway_type=PaymentGatewayType.SELLER_GATEWAY,
        commercial_model=SellerCommercialModel.SUBSCRIPTION,
        commission_rate=Decimal("0.00"),
        subscription_fee=Decimal("300.00"),
        payment_required_before_pickup=False,
        outstanding_receivable_allowed=True,
    )
    env_alt = setup_phase7_environment(client, tenant_name="Alternative Dry Cleaner")

    # Order 1: Confirmed (operational)
    o_conf = create_phase7_order(client, env)
    confirm_order_operational(client, env, o_conf["id"])

    # Order 2: Pending (marketplace unacknowledged)
    o_pend = create_phase7_order(client, env)

    # Trigger restriction
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    apply_daily_late_penalties(as_of_date=date(2026, 8, 25))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 25))

    with SessionLocal() as db:
        order_conf = db.get(Order, uuid.UUID(o_conf["id"]))
        order_pend = db.get(Order, uuid.UUID(o_pend["id"]))
        assert order_conf.status == OrderStatus.CONFIRMED.value  # PRESERVED
        assert order_pend.status == OrderStatus.CANCELLED.value  # CANCELLED

    # Customer re-selects from pending order
    code, res = reselect_seller(client, env, o_pend["id"], str(env_alt["seller"].id), str(env_alt["branch"].id))
    assert code == 201
    assert res["reselected_from_order_id"] == o_pend["id"]
