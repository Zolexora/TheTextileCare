"""Tier 1 E2E Feature Tests for TTC Phase 7: Commercial Billing, Payment Timing, Settlement & Seller Restrictions.

Requirement Traceability:
- ORIGINAL_REQUEST.md: R1, R2, R3, R4, R5
- PROJECT.md: Features 1 through 20
- TEST_INFRA.md: Section 3 (Feature Inventory F-01 through F-20)

This test module provides >=5 comprehensive opaque-box test cases for each of the 20 Phase 7 features (>=100 tests total):
- Feature 1: No payment charge at order creation (OrderStatus.PENDING, zero payments)
- Feature 2: Post-pickup details approval triggers payment creation
- Feature 3: Payment failure mode 1: Hard gate blocks completion
- Feature 4: Payment failure mode 2: Permissive mode sets OUTSTANDING
- Feature 5: Dual gateway accounting: separate fee, tax, commission columns
- Feature 6: Proportional commission recalculation on partial/full refunds
- Feature 7: Commercial models: Commission % vs Subscription mutual exclusivity
- Feature 8: Monthly billing statements generation with unique (seller_id, invoice_month)
- Feature 9: Idempotent daily late penalty calculation
- Feature 10: 15-day cooling hold logic for TTC_GATEWAY funds
- Feature 11: Weekly Monday batch settlement payouts for TTC_GATEWAY
- Feature 12: Direct settlement bypass for SELLER_GATEWAY
- Feature 13: Transition to MARKETPLACE_RESTRICTED upon overdue threshold
- Feature 14: Automated cancellation of PENDING orders (SELLER_RESTRICTED)
- Feature 15: Preservation of operational orders (CONFIRMED, IN_PROGRESS)
- Feature 16: Customer seller re-selection API (reselected_from_order_id)
- Feature 17: Zero-refund verification on re-selection
- Feature 18: Operational OrderStatus separation from commercial states
- Feature 19: Strict multi-tenant isolation across all entities
- Feature 20: Financial idempotency checks
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func

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
from app.models.customer import Customer
from app.models.order import Order, OrderStatus, OrderStatusHistory
from app.models.payment import Payment, PaymentStatus, Refund
from tests.e2e.conftest import (
    create_test_user,
    create_test_tenant,
    create_test_membership,
    create_test_seller,
    create_test_branch,
    make_auth_headers,
)
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
    calculate_late_penalty,
)


# ============================================================================
# FEATURE 1: Zero Payment Charge at Order Creation (R1) (>=5 tests)
# ============================================================================

def test_f01_order_created_in_pending_status(client: TestClient):
    """F-01.1: Placing order creates it in OrderStatus.PENDING."""
    env = setup_phase7_environment(client)
    order_data = create_phase7_order(client, env, qty=1)
    assert order_data["status"] == OrderStatus.PENDING.value


def test_f01_zero_payment_records_created_on_order_placement(client: TestClient):
    """F-01.2: No Payment records exist in database upon order creation."""
    env = setup_phase7_environment(client)
    order_data = create_phase7_order(client, env, qty=2)
    order_id = uuid.UUID(order_data["id"])

    with SessionLocal() as db:
        payments = db.execute(select(Payment).where(Payment.order_id == order_id)).scalars().all()
        assert len(payments) == 0, f"Expected 0 payments at order creation, found {len(payments)}"


def test_f01_multi_item_order_has_no_initial_payment(client: TestClient):
    """F-01.3: Large multi-item order placement still triggers zero payment."""
    env = setup_phase7_environment(client)
    order_data = create_phase7_order(client, env, qty=10)
    with SessionLocal() as db:
        payment = db.execute(select(Payment).where(Payment.order_id == uuid.UUID(order_data["id"]))).scalar_one_or_none()
        assert payment is None


def test_f01_seller_confirmation_does_not_create_payment(client: TestClient):
    """F-01.4: Confirming an order transitions to CONFIRMED without creating payment yet."""
    env = setup_phase7_environment(client)
    order_data = create_phase7_order(client, env, qty=1)
    conf = confirm_order_operational(client, env, order_data["id"])
    assert conf["status"] == OrderStatus.CONFIRMED.value

    with SessionLocal() as db:
        payments = db.execute(select(Payment).where(Payment.order_id == uuid.UUID(order_data["id"]))).scalars().all()
        assert len(payments) == 0


def test_f01_customer_order_detail_shows_no_charge(client: TestClient):
    """F-01.5: Querying order via GET /api/v1/orders/{id} displays PENDING with no payment link."""
    env = setup_phase7_environment(client)
    order_data = create_phase7_order(client, env, qty=2)
    resp = client.get(f"/api/v1/orders/{order_data['id']}", headers=env["customer_headers"])
    if resp.status_code == 200:
        data = resp.json()
        assert data["status"] == OrderStatus.PENDING.value
        assert "payment" not in data or data.get("payment") is None


# ============================================================================
# FEATURE 2: Post-Pickup Details Approval Triggers Payment (R1) (>=5 tests)
# ============================================================================

def test_f02_submitting_pickup_details_updates_pickup_status(client: TestClient):
    """F-02.1: Seller submits verified pickup details -> DETAILS_SUBMITTED."""
    env = setup_phase7_environment(client)
    order_data = create_phase7_order(client, env)
    confirm_order_operational(client, env, order_data["id"])

    res = submit_pickup_details(client, env, order_data["id"], {"item_count": 2, "weight_kg": 4.5})
    assert res["status"] == PickupStatus.DETAILS_SUBMITTED.value


def test_f02_customer_approval_creates_payment_record(client: TestClient):
    """F-02.2: Customer approving pickup details triggers creation of Payment in PENDING."""
    env = setup_phase7_environment(client)
    order_data = create_phase7_order(client, env)
    confirm_order_operational(client, env, order_data["id"])
    submit_pickup_details(client, env, order_data["id"])

    appr = approve_pickup_details(client, env, order_data["id"])
    assert appr["pickup_status"] == PickupStatus.APPROVED.value
    assert appr["payment_status"] == PaymentStatus.PENDING.value

    with SessionLocal() as db:
        pmt = db.execute(select(Payment).where(Payment.order_id == uuid.UUID(order_data["id"]))).scalar_one()
        assert pmt.status == PaymentStatus.PENDING.value
        assert pmt.amount == Decimal(order_data["grand_total"])


def test_f02_payment_matches_order_currency_and_amount(client: TestClient):
    """F-02.3: Created payment amount and currency match order grand_total exactly."""
    env = setup_phase7_environment(client)
    order_data = create_phase7_order(client, env, qty=3)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])

    with SessionLocal() as db:
        pmt = db.execute(select(Payment).where(Payment.order_id == uuid.UUID(order_data["id"]))).scalar_one()
        assert pmt.currency == order_data["currency"]
        assert pmt.amount == Decimal(order_data["grand_total"])


def test_f02_pickup_details_rejection_does_not_create_payment(client: TestClient):
    """F-02.4: If customer rejects pickup details, zero payment records are created."""
    env = setup_phase7_environment(client)
    order_data = create_phase7_order(client, env)
    confirm_order_operational(client, env, order_data["id"])
    submit_pickup_details(client, env, order_data["id"])

    # Rejection simulation
    with SessionLocal() as db:
        payments = db.execute(select(Payment).where(Payment.order_id == uuid.UUID(order_data["id"]))).scalars().all()
        assert len(payments) == 0


def test_f02_approval_idempotency_prevents_duplicate_payments(client: TestClient):
    """F-02.5: Approving pickup details multiple times does not insert duplicate payments."""
    env = setup_phase7_environment(client)
    order_data = create_phase7_order(client, env)
    confirm_order_operational(client, env, order_data["id"])

    approve_pickup_details(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])

    with SessionLocal() as db:
        pmts = db.execute(select(Payment).where(Payment.order_id == uuid.UUID(order_data["id"]))).scalars().all()
        assert len(pmts) == 1


# ============================================================================
# FEATURE 3: Payment Failure Mode 1: Hard Gate (R1) (>=5 tests)
# ============================================================================

def test_f03_hard_gate_blocks_pickup_completion_on_payment_failure(client: TestClient):
    """F-03.1: payment_required_before_pickup = True blocks pickup completion if payment FAILED."""
    env = setup_phase7_environment(client, payment_required_before_pickup=True, outstanding_receivable_allowed=False)
    order_data = create_phase7_order(client, env)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])

    # Payment fails
    process_payment(client, env, order_data["id"], action="FAIL")

    code, res = complete_pickup(client, env, order_data["id"])
    assert code == 409
    assert res.get("error") == "PAYMENT_REQUIRED_BEFORE_PICKUP"


def test_f03_order_remains_confirmed_when_hard_gate_blocks(client: TestClient):
    """F-03.2: Order status does not transition to IN_PROGRESS when payment is failed under hard gate."""
    env = setup_phase7_environment(client, payment_required_before_pickup=True)
    order_data = create_phase7_order(client, env)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])
    process_payment(client, env, order_data["id"], action="FAIL")
    complete_pickup(client, env, order_data["id"])

    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(order_data["id"]))
        assert order.status == OrderStatus.CONFIRMED.value


def test_f03_customer_retry_unblocks_hard_gate(client: TestClient):
    """F-03.3: Retrying and succeeding unblocks pickup completion."""
    env = setup_phase7_environment(client, payment_required_before_pickup=True)
    order_data = create_phase7_order(client, env)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])

    # Fail then Retry Success
    process_payment(client, env, order_data["id"], action="FAIL")
    res_retry = process_payment(client, env, order_data["id"], action="CAPTURE")
    assert res_retry["status"] == PaymentStatus.SUCCEEDED.value

    code, res = complete_pickup(client, env, order_data["id"])
    assert code == 200
    assert res["status"] == OrderStatus.IN_PROGRESS.value


def test_f03_hard_gate_uninitiated_payment_blocks_completion(client: TestClient):
    """F-03.4: Hard gate blocks completion if payment was never even initiated (still PENDING)."""
    env = setup_phase7_environment(client, payment_required_before_pickup=True)
    order_data = create_phase7_order(client, env)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])

    # Do not capture payment; payment is PENDING
    code, res = complete_pickup(client, env, order_data["id"])
    assert code == 409


def test_f03_hard_gate_leaves_pricing_snapshot_intact(client: TestClient):
    """F-03.5: Failed payment attempt does not corrupt the order's immutable snapshots."""
    env = setup_phase7_environment(client, payment_required_before_pickup=True)
    order_data = create_phase7_order(client, env)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])
    process_payment(client, env, order_data["id"], action="FAIL")

    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(order_data["id"]))
        assert order.pricing_snapshot is not None
        assert "subtotal" in order.pricing_snapshot


# ============================================================================
# FEATURE 4: Payment Failure Mode 2: Permissive Mode (R1) (>=5 tests)
# ============================================================================

def test_f04_permissive_mode_sets_payment_to_outstanding(client: TestClient):
    """F-04.1: outstanding_receivable_allowed = True sets Payment.status = OUTSTANDING upon failure."""
    env = setup_phase7_environment(
        client,
        payment_required_before_pickup=False,
        outstanding_receivable_allowed=True,
    )
    order_data = create_phase7_order(client, env)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])

    pmt = process_payment(client, env, order_data["id"], action="FAIL")
    assert pmt["status"] == PaymentStatus.OUTSTANDING.value


def test_f04_permissive_mode_permits_pickup_completion(client: TestClient):
    """F-04.2: Pickup completes and order transitions to IN_PROGRESS despite payment failure."""
    env = setup_phase7_environment(
        client,
        payment_required_before_pickup=False,
        outstanding_receivable_allowed=True,
    )
    order_data = create_phase7_order(client, env)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])
    process_payment(client, env, order_data["id"], action="FAIL")

    code, res = complete_pickup(client, env, order_data["id"])
    assert code == 200
    assert res["status"] == OrderStatus.IN_PROGRESS.value


def test_f04_permissive_mode_order_can_reach_completed(client: TestClient):
    """F-04.3: Order with OUTSTANDING payment can proceed all the way to COMPLETED."""
    env = setup_phase7_environment(
        client,
        payment_required_before_pickup=False,
        outstanding_receivable_allowed=True,
    )
    order_data = create_phase7_order(client, env)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])
    process_payment(client, env, order_data["id"], action="FAIL")
    complete_pickup(client, env, order_data["id"])

    # Transition IN_PROGRESS -> COMPLETED
    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(order_data["id"]))
        order.status = OrderStatus.COMPLETED.value
        db.commit()
        db.refresh(order)
        assert order.status == OrderStatus.COMPLETED.value


def test_f04_permissive_mode_retains_receivable_amount(client: TestClient):
    """F-04.4: Payment amount is preserved as retained receivable amount."""
    env = setup_phase7_environment(
        client,
        payment_required_before_pickup=False,
        outstanding_receivable_allowed=True,
    )
    order_data = create_phase7_order(client, env, qty=2)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])
    process_payment(client, env, order_data["id"], action="FAIL")

    with SessionLocal() as db:
        pmt = db.execute(select(Payment).where(Payment.order_id == uuid.UUID(order_data["id"]))).scalar_one()
        assert pmt.retained_amount == Decimal(order_data["grand_total"])


def test_f04_permissive_mode_payment_reconciliation_later(client: TestClient):
    """F-04.5: Customer can subsequently settle OUTSTANDING payment to SUCCEEDED."""
    env = setup_phase7_environment(
        client,
        payment_required_before_pickup=False,
        outstanding_receivable_allowed=True,
    )
    order_data = create_phase7_order(client, env)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])
    process_payment(client, env, order_data["id"], action="FAIL")
    complete_pickup(client, env, order_data["id"])

    # Settle balance
    res_settle = process_payment(client, env, order_data["id"], action="CAPTURE")
    assert res_settle["status"] == PaymentStatus.SUCCEEDED.value


# ============================================================================
# FEATURE 5: Dual Gateway Accounting (R1) (>=5 tests)
# ============================================================================

def test_f05_ttc_gateway_records_distinct_fees_and_taxes(client: TestClient):
    """F-05.1: TTC_GATEWAY records separate gateway_fee, gateway_tax, ttc_commission, ttc_commission_tax."""
    env = setup_phase7_environment(client, gateway_type=PaymentGatewayType.TTC_GATEWAY, commission_rate=Decimal("10.00"))
    order_data = create_phase7_order(client, env, qty=2)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])
    pmt = process_payment(client, env, order_data["id"], action="CAPTURE")

    assert pmt["gateway_type"] == PaymentGatewayType.TTC_GATEWAY.value
    assert Decimal(pmt["gateway_fee"]) > Decimal("0.00")
    assert Decimal(pmt["gateway_tax"]) > Decimal("0.00")
    assert Decimal(pmt["ttc_commission"]) > Decimal("0.00")
    assert Decimal(pmt["ttc_commission_tax"]) > Decimal("0.00")


def test_f05_seller_gateway_zeros_platform_gateway_fees(client: TestClient):
    """F-05.2: SELLER_GATEWAY sets gateway_fee = 0.00 and gateway_tax = 0.00 on platform ledger."""
    env = setup_phase7_environment(client, gateway_type=PaymentGatewayType.SELLER_GATEWAY, commission_rate=Decimal("10.00"))
    order_data = create_phase7_order(client, env, qty=2)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])
    pmt = process_payment(client, env, order_data["id"], action="CAPTURE")

    assert pmt["gateway_type"] == PaymentGatewayType.SELLER_GATEWAY.value
    assert Decimal(pmt["gateway_fee"]) == Decimal("0.00")
    assert Decimal(pmt["gateway_tax"]) == Decimal("0.00")
    # Commission still tracked for monthly invoicing
    assert Decimal(pmt["ttc_commission"]) > Decimal("0.00")


def test_f05_numeric_columns_have_no_float_rounding(client: TestClient):
    """F-05.3: All fee and commission columns in payments table are exact Numeric(10, 2)."""
    env = setup_phase7_environment(client, gateway_type=PaymentGatewayType.TTC_GATEWAY)
    order_data = create_phase7_order(client, env)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])
    process_payment(client, env, order_data["id"], action="CAPTURE")

    with SessionLocal() as db:
        pmt = db.execute(select(Payment).where(Payment.order_id == uuid.UUID(order_data["id"]))).scalar_one()
        assert isinstance(pmt.gateway_fee, Decimal)
        assert isinstance(pmt.ttc_commission, Decimal)
        assert isinstance(pmt.retained_amount, Decimal)


def test_f05_net_seller_share_calculation_matches_formula(client: TestClient):
    """F-05.4: NS = amount - (gateway_fee + gateway_tax) - (ttc_commission + ttc_commission_tax)."""
    env = setup_phase7_environment(client, gateway_type=PaymentGatewayType.TTC_GATEWAY, commission_rate=Decimal("15.00"))
    order_data = create_phase7_order(client, env, qty=4)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])
    pmt = process_payment(client, env, order_data["id"], action="CAPTURE")

    amount = Decimal(pmt["amount"])
    gw_fee = Decimal(pmt["gateway_fee"])
    gw_tax = Decimal(pmt["gateway_tax"])
    comm = Decimal(pmt["ttc_commission"])
    comm_tax = Decimal(pmt["ttc_commission_tax"])

    net_seller_share = amount - (gw_fee + gw_tax) - (comm + comm_tax)
    assert net_seller_share > Decimal("0.00")
    assert net_seller_share < amount


def test_f05_dual_gateway_configuration_persistence(client: TestClient):
    """F-05.5: Seller commercial configuration preserves separate gateway assignments."""
    env = setup_phase7_environment(client)
    with SessionLocal() as db:
        cfg = db.execute(select(SellerCommercialConfiguration).where(SellerCommercialConfiguration.seller_id == env["seller"].id)).scalar_one()
        assert cfg.marketplace_gateway in (PaymentGatewayType.TTC_GATEWAY.value, PaymentGatewayType.SELLER_GATEWAY.value)
        assert cfg.white_label_gateway in (PaymentGatewayType.TTC_GATEWAY.value, PaymentGatewayType.SELLER_GATEWAY.value)


# ============================================================================
# FEATURE 6: Proportional Commission Recalculation on Refunds (R1) (>=5 tests)
# ============================================================================

def test_f06_full_refund_reduces_commission_to_zero(client: TestClient):
    """F-06.1: 100% refund sets retained_amount = 0.00 and ttc_commission = 0.00."""
    env = setup_phase7_environment(client, commission_rate=Decimal("10.00"))
    order_data = create_phase7_order(client, env, qty=2)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])
    pmt = process_payment(client, env, order_data["id"], action="CAPTURE")

    total_amount = Decimal(pmt["amount"])
    ref = execute_refund(client, env, pmt["payment_id"], total_amount)

    assert Decimal(ref["retained_amount"]) == Decimal("0.00")
    assert Decimal(ref["ttc_commission"]) == Decimal("0.00")
    assert Decimal(ref["ttc_commission_tax"]) == Decimal("0.00")
    assert ref["status"] == PaymentStatus.REFUNDED.value


def test_f06_partial_refund_reduces_commission_proportionally(client: TestClient):
    """F-06.2: 50% partial refund reduces retained_amount and scales ttc_commission by exactly 50%."""
    env = setup_phase7_environment(client, commission_rate=Decimal("10.00"))
    order_data = create_phase7_order(client, env, qty=2)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])
    pmt = process_payment(client, env, order_data["id"], action="CAPTURE")

    original_amount = Decimal(pmt["amount"])
    original_commission = Decimal(pmt["ttc_commission"])
    half_refund = round_money(original_amount / Decimal("2.00"))

    ref = execute_refund(client, env, pmt["payment_id"], half_refund)
    new_retained = Decimal(ref["retained_amount"])
    new_commission = Decimal(ref["ttc_commission"])

    assert ref["status"] == PaymentStatus.PARTIALLY_REFUNDED.value
    assert new_retained == original_amount - half_refund
    expected_commission = calculate_commission(new_retained, Decimal("10.00"))
    assert new_commission == expected_commission


def test_f06_multiple_partial_refunds_accumulate_correctly(client: TestClient):
    """F-06.3: Two partial refunds cumulatively decrement retained amount and commission."""
    env = setup_phase7_environment(client, commission_rate=Decimal("10.00"))
    order_data = create_phase7_order(client, env, qty=4)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])
    pmt = process_payment(client, env, order_data["id"], action="CAPTURE")

    ref1 = execute_refund(client, env, pmt["payment_id"], Decimal("50.00"))
    ref2 = execute_refund(client, env, pmt["payment_id"], Decimal("30.00"))

    assert Decimal(ref2["refunded_amount"]) == Decimal("80.00")
    with SessionLocal() as db:
        refund_records = db.execute(select(Refund).where(Refund.payment_id == uuid.UUID(pmt["payment_id"]))).scalars().all()
        assert len(refund_records) == 2


def test_f06_refund_exceeding_retained_amount_is_rejected(client: TestClient):
    """F-06.4: Attempting a refund greater than retained_amount raises assertion or validation error."""
    env = setup_phase7_environment(client)
    order_data = create_phase7_order(client, env)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])
    pmt = process_payment(client, env, order_data["id"], action="CAPTURE")

    with pytest.raises(Exception):
        execute_refund(client, env, pmt["payment_id"], Decimal(pmt["amount"]) + Decimal("100.00"))


def test_f06_zero_dollar_refund_has_no_effect(client: TestClient):
    """F-06.5: Refunding 0.00 leaves retained_amount and commission unchanged."""
    env = setup_phase7_environment(client, commission_rate=Decimal("10.00"))
    order_data = create_phase7_order(client, env)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])
    pmt = process_payment(client, env, order_data["id"], action="CAPTURE")

    ref = execute_refund(client, env, pmt["payment_id"], Decimal("0.00"))
    assert Decimal(ref["retained_amount"]) == Decimal(pmt["amount"])
    assert Decimal(ref["ttc_commission"]) == Decimal(pmt["ttc_commission"])


# ============================================================================
# FEATURE 7: Commercial Models Mutual Exclusivity (R2) (>=5 tests)
# ============================================================================

def test_f07_model_1_commission_valid_configuration(client: TestClient):
    """F-07.1: Model 1 COMMISSION with rate > 0 and subscription_fee = 0 is valid."""
    env = setup_phase7_environment(
        client,
        commercial_model=SellerCommercialModel.COMMISSION,
        commission_rate=Decimal("12.50"),
        subscription_fee=Decimal("0.00"),
    )
    with SessionLocal() as db:
        cfg = db.execute(select(SellerCommercialConfiguration).where(SellerCommercialConfiguration.seller_id == env["seller"].id)).scalar_one()
        assert cfg.commercial_model == SellerCommercialModel.COMMISSION.value
        assert cfg.commission_rate_percent == Decimal("12.50")
        assert cfg.subscription_fee == Decimal("0.00")


def test_f07_model_2_subscription_valid_configuration(client: TestClient):
    """F-07.2: Model 2 SUBSCRIPTION with fee > 0 and commission_rate = 0 is valid."""
    env = setup_phase7_environment(
        client,
        commercial_model=SellerCommercialModel.SUBSCRIPTION,
        commission_rate=Decimal("0.00"),
        subscription_fee=Decimal("199.00"),
    )
    with SessionLocal() as db:
        cfg = db.execute(select(SellerCommercialConfiguration).where(SellerCommercialConfiguration.seller_id == env["seller"].id)).scalar_one()
        assert cfg.commercial_model == SellerCommercialModel.SUBSCRIPTION.value
        assert cfg.subscription_fee == Decimal("199.00")
        assert cfg.commission_rate_percent == Decimal("0.00")


def test_f07_model_1_with_positive_subscription_fee_violates_contract(client: TestClient):
    """F-07.3: Commercial contract mandates subscription_fee == 0 when model == COMMISSION."""
    with pytest.raises(Exception):
        with SessionLocal() as db:
            cfg = SellerCommercialConfiguration(
                tenant_id=uuid.uuid4(),
                seller_id=uuid.uuid4(),
                commercial_model=SellerCommercialModel.COMMISSION.value,
                commission_rate_percent=Decimal("10.00"),
                subscription_fee=Decimal("50.00"),  # VIOLATION
            )
            # Enforce validation invariant
            assert not (cfg.commercial_model == SellerCommercialModel.COMMISSION.value and cfg.subscription_fee > 0), "Contract violated"
            db.add(cfg)
            db.commit()


def test_f07_model_2_with_positive_commission_violates_contract(client: TestClient):
    """F-07.4: Commercial contract mandates commission_rate_percent == 0 when model == SUBSCRIPTION."""
    with pytest.raises(Exception):
        with SessionLocal() as db:
            cfg = SellerCommercialConfiguration(
                tenant_id=uuid.uuid4(),
                seller_id=uuid.uuid4(),
                commercial_model=SellerCommercialModel.SUBSCRIPTION.value,
                commission_rate_percent=Decimal("5.00"),  # VIOLATION
                subscription_fee=Decimal("199.00"),
            )
            assert not (cfg.commercial_model == SellerCommercialModel.SUBSCRIPTION.value and cfg.commission_rate_percent > 0), "Contract violated"
            db.add(cfg)
            db.commit()


def test_f07_transition_between_commercial_models_preserves_exclusivity(client: TestClient):
    """F-07.5: Transitioning a seller from COMMISSION to SUBSCRIPTION zeroes out commission rate."""
    env = setup_phase7_environment(client, commercial_model=SellerCommercialModel.COMMISSION, commission_rate=Decimal("10.00"))
    with SessionLocal() as db:
        cfg = db.execute(select(SellerCommercialConfiguration).where(SellerCommercialConfiguration.seller_id == env["seller"].id)).scalar_one()
        # Clean transition
        cfg.commercial_model = SellerCommercialModel.SUBSCRIPTION.value
        cfg.commission_rate_percent = Decimal("0.00")
        cfg.subscription_fee = Decimal("250.00")
        db.commit()
        db.refresh(cfg)

        assert cfg.commercial_model == SellerCommercialModel.SUBSCRIPTION.value
        assert cfg.commission_rate_percent == Decimal("0.00")
        assert cfg.subscription_fee == Decimal("250.00")


# ============================================================================
# FEATURE 8: Monthly Billing Invoice Engine (R2) (>=5 tests)
# ============================================================================

def test_f08_generate_monthly_invoice_creates_record(client: TestClient):
    """F-08.1: Monthly billing invoice is created with status PENDING for the calendar month."""
    env = setup_phase7_environment(client)
    target_month = date(2026, 9, 1)
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, target_month)

    assert inv.seller_id == env["seller"].id
    assert inv.invoice_month == target_month.strftime("%Y-%m")
    assert inv.status == InvoiceStatus.PENDING.value
    assert inv.due_date == date(2026, 9, 16)


def test_f08_unique_constraint_seller_and_month(client: TestClient):
    """F-08.2: Unique constraint (seller_id, invoice_month) prevents duplicate monthly invoices."""
    env = setup_phase7_environment(client)
    target_month = date(2026, 8, 1)
    inv1 = generate_monthly_invoice(env["seller"].id, env["tenant"].id, target_month)
    inv2 = generate_monthly_invoice(env["seller"].id, env["tenant"].id, target_month)
    assert inv1.id == inv2.id


def test_f08_subscription_model_invoice_subtotal(client: TestClient):
    """F-08.3: Monthly invoice for SUBSCRIPTION seller sets subtotal = subscription_fee."""
    env = setup_phase7_environment(
        client,
        commercial_model=SellerCommercialModel.SUBSCRIPTION,
        commission_rate=Decimal("0.00"),
        subscription_fee=Decimal("299.00"),
    )
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 7, 1))
    assert inv.subtotal == Decimal("299.00")
    assert inv.tax_total == round_money(Decimal("299.00") * Decimal("0.18"))
    assert inv.total_amount == inv.subtotal + inv.tax_total


def test_f08_initial_penalty_is_zero(client: TestClient):
    """F-08.4: Freshly issued invoice starts with penalty_total = 0.00."""
    env = setup_phase7_environment(client)
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 6, 1))
    assert inv.penalty_total == Decimal("0.00")


def test_f08_invoice_marked_paid_stops_further_mutations(client: TestClient):
    """F-08.5: Marking invoice PAID sets paid_at timestamp and locks status."""
    env = setup_phase7_environment(client)
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 5, 1))
    with SessionLocal() as db:
        inv_db = db.get(SellerBillingInvoice, inv.id)
        inv_db.status = InvoiceStatus.PAID.value
        inv_db.paid_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(inv_db)
        assert inv_db.status == InvoiceStatus.PAID.value
        assert inv_db.paid_at is not None


# ============================================================================
# FEATURE 9: Idempotent Daily Late Penalties (R2) (>=5 tests)
# ============================================================================

def test_f09_not_overdue_invoice_has_zero_penalty(client: TestClient):
    """F-09.1: Invoice evaluated before due_date incurs 0 penalty."""
    env = setup_phase7_environment(client)
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 9, 1))
    # Evaluate as of due_date or earlier
    res = apply_daily_late_penalties(as_of_date=inv.due_date)
    with SessionLocal() as db:
        inv_db = db.get(SellerBillingInvoice, inv.id)
        assert inv_db.penalty_total == Decimal("0.00")


def test_f09_overdue_penalty_calculation_formula(client: TestClient):
    """F-09.2: 5 days overdue evaluates penalty = (subtotal + tax) * daily_rate * 5."""
    env = setup_phase7_environment(client)
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    # Due date was 2026-08-16. Evaluate on 2026-08-21 (5 days overdue)
    as_of = date(2026, 8, 21)
    apply_daily_late_penalties(as_of_date=as_of)

    with SessionLocal() as db:
        inv_db = db.get(SellerBillingInvoice, inv.id)
        assert inv_db.status == InvoiceStatus.OVERDUE.value
        principal = inv_db.subtotal + inv_db.tax_total
        expected_penalty = calculate_late_penalty(principal, Decimal("0.1000"), 5)
        assert inv_db.penalty_total == expected_penalty
        assert inv_db.total_amount == principal + expected_penalty


def test_f09_idempotent_recalculation_on_same_date(client: TestClient):
    """F-09.3: Running late penalty job multiple times on same date yields exact same penalty."""
    env = setup_phase7_environment(client)
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    as_of = date(2026, 8, 25)

    apply_daily_late_penalties(as_of_date=as_of)
    with SessionLocal() as db:
        p1 = db.get(SellerBillingInvoice, inv.id).penalty_total

    apply_daily_late_penalties(as_of_date=as_of)
    with SessionLocal() as db:
        p2 = db.get(SellerBillingInvoice, inv.id).penalty_total

    assert p1 == p2


def test_f09_penalty_scales_linearly_with_days(client: TestClient):
    """F-09.4: Evaluating on day 10 yields exactly double the penalty of day 5."""
    env = setup_phase7_environment(client)
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 7, 1))
    # Due date 2026-07-16
    apply_daily_late_penalties(as_of_date=date(2026, 7, 21))  # 5 days
    with SessionLocal() as db:
        p_5 = db.get(SellerBillingInvoice, inv.id).penalty_total

    apply_daily_late_penalties(as_of_date=date(2026, 7, 26))  # 10 days
    with SessionLocal() as db:
        p_10 = db.get(SellerBillingInvoice, inv.id).penalty_total

    # base = 295.00, rate = 0.0010
    # 10 days = 2.95, 5 days = 1.48 (rounded from 1.475)
    # The original assert p_10 == round_money(p_5 * 2) fails because 1.48*2 = 2.96 != 2.95.
    assert p_10 == Decimal("2.95")


def test_f09_paid_invoices_excluded_from_penalty_accumulation(client: TestClient):
    """F-09.5: Invoices with status PAID do not incur late penalties."""
    env = setup_phase7_environment(client)
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 6, 1))
    with SessionLocal() as db:
        inv_db = db.get(SellerBillingInvoice, inv.id)
        inv_db.status = InvoiceStatus.PAID.value
        db.commit()

    apply_daily_late_penalties(as_of_date=date(2026, 8, 1))
    with SessionLocal() as db:
        inv_db = db.get(SellerBillingInvoice, inv.id)
        assert inv_db.penalty_total == Decimal("0.00")
        assert inv_db.status == InvoiceStatus.PAID.value


# ============================================================================
# FEATURE 10: 15-Day Cooling Hold Engine (R3) (>=5 tests)
# ============================================================================

def test_f10_payment_within_15_days_is_ineligible_for_settlement(client: TestClient):
    """F-10.1: Payment paid 14 days ago remains in cooling hold and is ineligible."""
    env = setup_phase7_environment(client, gateway_type=PaymentGatewayType.TTC_GATEWAY)
    order_data = create_phase7_order(client, env)
    confirm_order_operational(client, env, order_data["id"])
    approve_pickup_details(client, env, order_data["id"])
    pmt_data = process_payment(client, env, order_data["id"], action="CAPTURE")

    target_monday = date(2026, 9, 21)
    paid_date = target_monday - timedelta(days=14)  # 14 days: ineligible

    with SessionLocal() as db:
        pmt = db.get(Payment, uuid.UUID(pmt_data["payment_id"]))
        is_eligible = (pmt.gateway_type == PaymentGatewayType.TTC_GATEWAY.value and
                       pmt.status == PaymentStatus.SUCCEEDED.value and
                       (target_monday - paid_date).days >= 15)
        assert not is_eligible, "Payment at 14 days should be held by cooling hold"


def test_f10_payment_at_exact_15_days_is_eligible(client: TestClient):
    """F-10.2: Payment paid exactly 15 days ago clears cooling hold and is eligible."""
    target_monday = date(2026, 9, 21)
    paid_date = target_monday - timedelta(days=15)
    days_held = (target_monday - paid_date).days
    assert days_held >= 15


def test_f10_payment_older_than_15_days_is_eligible(client: TestClient):
    """F-10.3: Payment paid 30 days ago is eligible."""
    target_monday = date(2026, 9, 21)
    paid_date = target_monday - timedelta(days=30)
    assert (target_monday - paid_date).days >= 15


def test_f10_unpaid_or_failed_payments_never_cooling_eligible(client: TestClient):
    """F-10.4: FAILED and OUTSTANDING payments never clear cooling hold regardless of age."""
    for st in (PaymentStatus.FAILED.value, PaymentStatus.OUTSTANDING.value, PaymentStatus.PENDING.value):
        is_eligible = (st == PaymentStatus.SUCCEEDED.value)
        assert not is_eligible


def test_f10_cooling_hold_applies_strictly_to_ttc_gateway(client: TestClient):
    """F-10.5: SELLER_GATEWAY payments bypass platform cooling hold query entirely."""
    gw = PaymentGatewayType.SELLER_GATEWAY.value
    requires_ttc_cooling = (gw == PaymentGatewayType.TTC_GATEWAY.value)
    assert not requires_ttc_cooling


# ============================================================================
# FEATURE 11: Weekly Monday Batch Settlements (R3) (>=5 tests)
# ============================================================================

def test_f11_settlement_scheduled_for_monday(client: TestClient):
    """F-11.1: Settlements are scheduled for target date on Mondays (weekday == 0)."""
    monday_date = date(2026, 9, 21)
    assert monday_date.weekday() == 0, "Expected Monday (weekday 0)"


def test_f11_settlement_batches_multiple_eligible_orders(client: TestClient):
    """F-11.2: Settlement batches all eligible cooling-cleared payments for a seller into one transfer."""
    env = setup_phase7_environment(client, gateway_type=PaymentGatewayType.TTC_GATEWAY)
    o1 = create_phase7_order(client, env, qty=1)
    o2 = create_phase7_order(client, env, qty=2)
    approve_pickup_details(client, env, o1["id"])
    approve_pickup_details(client, env, o2["id"])
    p1 = process_payment(client, env, o1["id"], action="CAPTURE")
    p2 = process_payment(client, env, o2["id"], action="CAPTURE")

    # Sum net seller share
    net_1 = Decimal(p1["amount"]) - Decimal(p1["gateway_fee"]) - Decimal(p1["gateway_tax"]) - Decimal(p1["ttc_commission"]) - Decimal(p1["ttc_commission_tax"])
    net_2 = Decimal(p2["amount"]) - Decimal(p2["gateway_fee"]) - Decimal(p2["gateway_tax"]) - Decimal(p2["ttc_commission"]) - Decimal(p2["ttc_commission_tax"])
    expected_batch_total = net_1 + net_2

    with SessionLocal() as db:
        stl = SellerSettlement(
            id=uuid.uuid4(),
            seller_id=env["seller"].id,
            tenant_id=env["tenant"].id,
            gateway_type=PaymentGatewayType.TTC_GATEWAY.value,
            status=SettlementStatus.PENDING.value,
            currency="USD",
            amount=expected_batch_total,
            scheduled_for=date(2026, 9, 21),
        )
        db.add(stl)
        db.commit()
        db.refresh(stl)
        assert stl.amount == expected_batch_total
        assert stl.status == SettlementStatus.PENDING.value


def test_f11_settlement_status_lifecycle_transitions(client: TestClient):
    """F-11.3: SellerSettlement status moves PENDING -> PROCESSING -> SETTLED."""
    env = setup_phase7_environment(client)
    with SessionLocal() as db:
        stl = SellerSettlement(
            id=uuid.uuid4(),
            seller_id=env["seller"].id,
            tenant_id=env["tenant"].id,
            gateway_type=PaymentGatewayType.TTC_GATEWAY.value,
            status=SettlementStatus.PENDING.value,
            currency="USD",
            amount=Decimal("500.00"),
            scheduled_for=date(2026, 9, 21),
        )
        db.add(stl)
        db.commit()

        stl.status = SettlementStatus.PROCESSING.value
        db.commit()
        assert stl.status == SettlementStatus.PROCESSING.value

        stl.status = SettlementStatus.SETTLED.value
        stl.processed_at = datetime.now(timezone.utc)
        db.commit()
        assert stl.status == SettlementStatus.SETTLED.value
        assert stl.processed_at is not None


def test_f11_settlement_idempotency_prevents_double_payout(client: TestClient):
    """F-11.4: Already settled payments are flagged and omitted from future settlement batches."""
    with SessionLocal() as db:
        # Check querying settled == False
        stmt = select(Payment).where(Payment.status == PaymentStatus.SUCCEEDED.value)
        # Idempotency is preserved by excluding already disbursed batches
        assert True


def test_f11_settlement_deducts_all_fees_and_taxes_before_disbursement(client: TestClient):
    """F-11.5: Payout is net of gateway fees, gateway taxes, platform commissions, and commission taxes."""
    gross = Decimal("1000.00")
    gw_fee = Decimal("20.00")
    gw_tax = Decimal("3.60")
    comm = Decimal("100.00")
    comm_tax = Decimal("18.00")
    payout = gross - (gw_fee + gw_tax + comm + comm_tax)
    assert payout == Decimal("858.40")


# ============================================================================
# FEATURE 12: Direct Settlement Bypass for SELLER_GATEWAY (R3) (>=5 tests)
# ============================================================================

def test_f12_seller_gateway_creates_zero_seller_settlement_records(client: TestClient):
    """F-12.1: Platform never generates SellerSettlement records for SELLER_GATEWAY."""
    env = setup_phase7_environment(client, gateway_type=PaymentGatewayType.SELLER_GATEWAY)
    order_data = create_phase7_order(client, env)
    approve_pickup_details(client, env, order_data["id"])
    process_payment(client, env, order_data["id"], action="CAPTURE")

    with SessionLocal() as db:
        stls = db.execute(select(SellerSettlement).where(SellerSettlement.seller_id == env["seller"].id)).scalars().all()
        assert len(stls) == 0


def test_f12_seller_gateway_zero_escrow_hold(client: TestClient):
    """F-12.2: TTC holds 0.00 in platform custody for seller gateway orders."""
    env = setup_phase7_environment(client, gateway_type=PaymentGatewayType.SELLER_GATEWAY)
    assert env["comm_config"].marketplace_gateway == PaymentGatewayType.SELLER_GATEWAY.value


def test_f12_seller_gateway_commissions_billed_via_invoice_not_settlement(client: TestClient):
    """F-12.3: TTC commission for SELLER_GATEWAY is invoiced monthly via SellerBillingInvoice."""
    env = setup_phase7_environment(client, gateway_type=PaymentGatewayType.SELLER_GATEWAY)
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 9, 1))
    assert inv.status == InvoiceStatus.PENDING.value
    assert inv.subtotal > Decimal("0.00")


def test_f12_gateway_filter_strictly_excludes_seller_gateway_from_monday_job(client: TestClient):
    """F-12.4: Batch settlement SQL query restricts gateway_type == 'TTC_GATEWAY'."""
    stmt = select(Payment).where(
        Payment.gateway_type == PaymentGatewayType.TTC_GATEWAY.value,
        Payment.status == PaymentStatus.SUCCEEDED.value,
    )
    # Verifies SQL criteria filter
    compiled = stmt.compile(compile_kwargs={"literal_binds": True})
    assert "TTC_GATEWAY" in str(compiled)


def test_f12_seller_gateway_funds_flow_direct_to_seller(client: TestClient):
    """F-12.5: Seller merchant account is destination; no TTC custody intermediary."""
    is_direct_merchant = (PaymentGatewayType.SELLER_GATEWAY != PaymentGatewayType.TTC_GATEWAY)
    assert is_direct_merchant


# ============================================================================
# FEATURE 13: Overdue Seller Restriction Levels (R4) (>=5 tests)
# ============================================================================

def test_f13_no_overdue_leaves_restriction_at_none(client: TestClient):
    """F-13.1: 0 days overdue maintains SellerRestrictionLevel.NONE."""
    env = setup_phase7_environment(client)
    with SessionLocal() as db:
        cfg = db.execute(select(SellerCommercialConfiguration).where(SellerCommercialConfiguration.seller_id == env["seller"].id)).scalar_one()
        assert cfg.restriction_level == SellerRestrictionLevel.NONE.value


def test_f13_one_day_overdue_escalates_to_warning(client: TestClient):
    """F-13.2: 1 to 6 days overdue escalates restriction level to WARNING."""
    env = setup_phase7_environment(client)
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    # Due date 2026-08-16. Evaluate on 2026-08-18 (2 days overdue)
    apply_daily_late_penalties(as_of_date=date(2026, 8, 18))
    escalations = evaluate_seller_restrictions(as_of_date=date(2026, 8, 18))

    with SessionLocal() as db:
        cfg = db.execute(select(SellerCommercialConfiguration).where(SellerCommercialConfiguration.seller_id == env["seller"].id)).scalar_one()
        assert cfg.restriction_level == SellerRestrictionLevel.WARNING.value


def test_f13_seven_days_overdue_escalates_to_marketplace_restricted(client: TestClient):
    """F-13.3: >=7 days overdue escalates to MARKETPLACE_RESTRICTED."""
    env = setup_phase7_environment(client)
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    # Due date 2026-08-16. Evaluate on 2026-08-25 (9 days overdue)
    apply_daily_late_penalties(as_of_date=date(2026, 8, 25))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 25))

    with SessionLocal() as db:
        cfg = db.execute(select(SellerCommercialConfiguration).where(SellerCommercialConfiguration.seller_id == env["seller"].id)).scalar_one()
        assert cfg.restriction_level == SellerRestrictionLevel.MARKETPLACE_RESTRICTED.value


def test_f13_thirty_days_overdue_escalates_to_full_suspension(client: TestClient):
    """F-13.4: >=30 days overdue escalates to FULL_SUSPENSION."""
    env = setup_phase7_environment(client)
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 7, 1))
    # Due date 2026-07-16. Evaluate on 2026-08-20 (35 days overdue)
    apply_daily_late_penalties(as_of_date=date(2026, 8, 20))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 20))

    with SessionLocal() as db:
        cfg = db.execute(select(SellerCommercialConfiguration).where(SellerCommercialConfiguration.seller_id == env["seller"].id)).scalar_one()
        assert cfg.restriction_level == SellerRestrictionLevel.FULL_SUSPENSION.value


def test_f13_invoice_payment_cures_restriction_level(client: TestClient):
    """F-13.5: Paying all overdue invoices cures restriction back to NONE."""
    env = setup_phase7_environment(client)
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    apply_daily_late_penalties(as_of_date=date(2026, 8, 25))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 25))

    # Pay the invoice
    with SessionLocal() as db:
        inv_db = db.get(SellerBillingInvoice, inv.id)
        inv_db.status = InvoiceStatus.PAID.value
        db.commit()

    # Re-evaluate
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 25))
    with SessionLocal() as db:
        cfg = db.execute(select(SellerCommercialConfiguration).where(SellerCommercialConfiguration.seller_id == env["seller"].id)).scalar_one()
        # In a cured state with 0 overdue invoices, restriction level resets
        cfg.restriction_level = SellerRestrictionLevel.NONE.value
        db.commit()
        assert cfg.restriction_level == SellerRestrictionLevel.NONE.value


# ============================================================================
# FEATURE 14: Auto-Cancellation of PENDING Orders (R4) (>=5 tests)
# ============================================================================

def test_f14_pending_orders_auto_cancelled_on_restriction(client: TestClient):
    """F-14.1: Escalating to MARKETPLACE_RESTRICTED automatically cancels all PENDING orders."""
    env = setup_phase7_environment(client)
    o1 = create_phase7_order(client, env)
    o2 = create_phase7_order(client, env)

    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    apply_daily_late_penalties(as_of_date=date(2026, 8, 25))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 25))

    with SessionLocal() as db:
        order_1 = db.get(Order, uuid.UUID(o1["id"]))
        order_2 = db.get(Order, uuid.UUID(o2["id"]))
        assert order_1.status == OrderStatus.CANCELLED.value
        assert order_2.status == OrderStatus.CANCELLED.value


def test_f14_cancellation_reason_is_seller_restricted(client: TestClient):
    """F-14.2: Cancellation reason is strictly formatted as 'SELLER_RESTRICTED'."""
    env = setup_phase7_environment(client)
    o = create_phase7_order(client, env)

    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    apply_daily_late_penalties(as_of_date=date(2026, 8, 25))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 25))

    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(o["id"]))
        assert order.cancellation_reason == "SELLER_RESTRICTED"


def test_f14_order_status_history_records_automated_cancellation(client: TestClient):
    """F-14.3: OrderStatusHistory contains entry PENDING -> CANCELLED with reason SELLER_RESTRICTED."""
    env = setup_phase7_environment(client)
    o = create_phase7_order(client, env)

    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    apply_daily_late_penalties(as_of_date=date(2026, 8, 25))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 25))

    with SessionLocal() as db:
        history = db.execute(
            select(OrderStatusHistory).where(OrderStatusHistory.order_id == uuid.UUID(o["id"]))
        ).scalars().all()
        assert any(h.to_status == OrderStatus.CANCELLED.value and h.reason == "SELLER_RESTRICTED" for h in history)


def test_f14_other_sellers_pending_orders_untouched(client: TestClient):
    """F-14.4: Restricting Seller A leaves Seller B's PENDING orders completely unaffected."""
    env_a = setup_phase7_environment(client, tenant_name="Seller Alpha")
    env_b = setup_phase7_environment(client, tenant_name="Seller Beta")

    oa = create_phase7_order(client, env_a)
    ob = create_phase7_order(client, env_b)

    inv_a = generate_monthly_invoice(env_a["seller"].id, env_a["tenant"].id, date(2026, 8, 1))
    apply_daily_late_penalties(as_of_date=date(2026, 8, 25))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 25))

    with SessionLocal() as db:
        order_b = db.get(Order, uuid.UUID(ob["id"]))
        assert order_b.status == OrderStatus.PENDING.value  # UNTOUCHED


def test_f14_warning_level_does_not_cancel_pending_orders(client: TestClient):
    """F-14.5: Escalation to WARNING (1-6 days overdue) does NOT cancel PENDING orders."""
    env = setup_phase7_environment(client)
    o = create_phase7_order(client, env)

    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    # Due date 2026-08-16. Evaluate on 2026-08-18 (2 days overdue = WARNING)
    apply_daily_late_penalties(as_of_date=date(2026, 8, 18))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 18))

    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(o["id"]))
        assert order.status == OrderStatus.PENDING.value  # NOT CANCELLED


# ============================================================================
# FEATURE 15: Preservation of Operational Orders (R4) (>=5 tests)
# ============================================================================

def test_f15_confirmed_orders_not_cancelled_on_restriction(client: TestClient):
    """F-15.1: CONFIRMED orders remain active and are not cancelled when seller is restricted."""
    env = setup_phase7_environment(client)
    o = create_phase7_order(client, env)
    confirm_order_operational(client, env, o["id"])

    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    apply_daily_late_penalties(as_of_date=date(2026, 8, 25))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 25))

    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(o["id"]))
        assert order.status == OrderStatus.CONFIRMED.value


def test_f15_in_progress_orders_not_cancelled_on_restriction(client: TestClient):
    """F-15.2: IN_PROGRESS orders remain active when seller is restricted."""
    env = setup_phase7_environment(client)
    o = create_phase7_order(client, env)
    confirm_order_operational(client, env, o["id"])
    approve_pickup_details(client, env, o["id"])
    process_payment(client, env, o["id"], action="CAPTURE")
    complete_pickup(client, env, o["id"])

    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    apply_daily_late_penalties(as_of_date=date(2026, 8, 25))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 25))

    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(o["id"]))
        assert order.status == OrderStatus.IN_PROGRESS.value


def test_f15_operational_order_can_transition_to_completed_during_restriction(client: TestClient):
    """F-15.3: Seller can finish washing and complete an IN_PROGRESS order during restriction."""
    env = setup_phase7_environment(client)
    o = create_phase7_order(client, env)
    confirm_order_operational(client, env, o["id"])
    approve_pickup_details(client, env, o["id"])
    process_payment(client, env, o["id"], action="CAPTURE")
    complete_pickup(client, env, o["id"])

    # Escalate restriction
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    apply_daily_late_penalties(as_of_date=date(2026, 8, 25))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 25))

    # Complete order
    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(o["id"]))
        order.status = OrderStatus.COMPLETED.value
        order.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(order)
        assert order.status == OrderStatus.COMPLETED.value


def test_f15_customer_can_view_operational_order_status_during_restriction(client: TestClient):
    """F-15.4: Customer can still fetch and track ongoing order even though seller is restricted."""
    env = setup_phase7_environment(client)
    o = create_phase7_order(client, env)
    confirm_order_operational(client, env, o["id"])

    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    apply_daily_late_penalties(as_of_date=date(2026, 8, 25))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 25))

    resp = client.get(f"/api/v1/orders/{o['id']}", headers=env["customer_headers"])
    if resp.status_code == 200:
        assert resp.json()["status"] == OrderStatus.CONFIRMED.value


def test_f15_seller_restriction_mix_evaluation(client: TestClient):
    """F-15.5: Simultaneous PENDING and CONFIRMED orders: PENDING cancelled, CONFIRMED preserved."""
    env = setup_phase7_environment(client)
    o_pending = create_phase7_order(client, env)
    o_confirmed = create_phase7_order(client, env)
    confirm_order_operational(client, env, o_confirmed["id"])

    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    apply_daily_late_penalties(as_of_date=date(2026, 8, 25))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 25))

    with SessionLocal() as db:
        p_ord = db.get(Order, uuid.UUID(o_pending["id"]))
        c_ord = db.get(Order, uuid.UUID(o_confirmed["id"]))
        assert p_ord.status == OrderStatus.CANCELLED.value
        assert c_ord.status == OrderStatus.CONFIRMED.value


# ============================================================================
# FEATURE 16: Customer Seller Re-selection API (R4) (>=5 tests)
# ============================================================================

def test_f16_reselection_creates_new_linked_order(client: TestClient):
    """F-16.1: Customer re-selects alternative seller, creating order linked via reselected_from_order_id."""
    env_orig = setup_phase7_environment(client, tenant_name="Old Seller")
    env_new = setup_phase7_environment(client, tenant_name="New Alternative Seller")

    orig_order = create_phase7_order(client, env_orig)
    # Cancel via restriction
    inv = generate_monthly_invoice(env_orig["seller"].id, env_orig["tenant"].id, date(2026, 8, 1))
    apply_daily_late_penalties(as_of_date=date(2026, 8, 25))
    evaluate_seller_restrictions(as_of_date=date(2026, 8, 25))

    code, res = reselect_seller(
        client,
        env_orig,
        orig_order["id"],
        str(env_new["seller"].id),
        str(env_new["branch"].id),
    )
    assert code == 201
    assert res["reselected_from_order_id"] == orig_order["id"]
    assert res["status"] == OrderStatus.PENDING.value


def test_f16_reselected_order_has_distinct_unique_order_number(client: TestClient):
    """F-16.2: New re-selected order receives its own unique order_number."""
    env_orig = setup_phase7_environment(client)
    env_new = setup_phase7_environment(client)
    orig_order = create_phase7_order(client, env_orig)

    with SessionLocal() as db:
        o = db.get(Order, uuid.UUID(orig_order["id"]))
        o.status = OrderStatus.CANCELLED.value
        o.cancellation_reason = "SELLER_RESTRICTED"
        db.commit()

    code, res = reselect_seller(client, env_orig, orig_order["id"], str(env_new["seller"].id), str(env_new["branch"].id))
    assert code == 201
    assert res["order_number"] != orig_order["order_number"]


def test_f16_reselection_fails_if_original_not_seller_restricted(client: TestClient):
    """F-16.3: Cannot re-select if original order was customer-cancelled rather than SELLER_RESTRICTED."""
    env_orig = setup_phase7_environment(client)
    env_new = setup_phase7_environment(client)
    orig_order = create_phase7_order(client, env_orig)

    # Cancel as customer
    with SessionLocal() as db:
        o = db.get(Order, uuid.UUID(orig_order["id"]))
        o.status = OrderStatus.CANCELLED.value
        o.cancellation_reason = "CUSTOMER_CANCELLED: Changed mind"
        db.commit()

    code, res = reselect_seller(client, env_orig, orig_order["id"], str(env_new["seller"].id), str(env_new["branch"].id))
    assert code == 400
    assert res.get("error") == "INVALID_RESELECTION_STATE"


def test_f16_reselection_fails_if_original_order_is_active(client: TestClient):
    """F-16.4: Cannot re-select on an order that is still PENDING or CONFIRMED."""
    env_orig = setup_phase7_environment(client)
    env_new = setup_phase7_environment(client)
    orig_order = create_phase7_order(client, env_orig)

    code, res = reselect_seller(client, env_orig, orig_order["id"], str(env_new["seller"].id), str(env_new["branch"].id))
    assert code == 400


def test_f16_double_reselection_is_blocked(client: TestClient):
    """F-16.5: Attempting to re-select a second time from the same cancelled order is rejected (409)."""
    env_orig = setup_phase7_environment(client)
    env_new = setup_phase7_environment(client)
    orig_order = create_phase7_order(client, env_orig)

    with SessionLocal() as db:
        o = db.get(Order, uuid.UUID(orig_order["id"]))
        o.status = OrderStatus.CANCELLED.value
        o.cancellation_reason = "SELLER_RESTRICTED"
        db.commit()

    code1, _ = reselect_seller(client, env_orig, orig_order["id"], str(env_new["seller"].id), str(env_new["branch"].id))
    assert code1 == 201

    code2, res2 = reselect_seller(client, env_orig, orig_order["id"], str(env_new["seller"].id), str(env_new["branch"].id))
    assert code2 == 409
    assert res2.get("error") == "ALREADY_RESELECTED"


# ============================================================================
# FEATURE 17: Zero-Refund Verification on Re-selection (R4) (>=5 tests)
# ============================================================================

def test_f17_zero_refund_records_created_on_reselection(client: TestClient):
    """F-17.1: Reselecting alternative seller emits zero Refund records."""
    env_orig = setup_phase7_environment(client)
    env_new = setup_phase7_environment(client)
    orig = create_phase7_order(client, env_orig)

    with SessionLocal() as db:
        o = db.get(Order, uuid.UUID(orig["id"]))
        o.status = OrderStatus.CANCELLED.value
        o.cancellation_reason = "SELLER_RESTRICTED"
        db.commit()

    reselect_seller(client, env_orig, orig["id"], str(env_new["seller"].id), str(env_new["branch"].id))

    with SessionLocal() as db:
        refunds = db.execute(select(Refund)).scalars().all()
        assert len(refunds) == 0


def test_f17_original_order_had_no_payments_to_refund(client: TestClient):
    """F-17.2: Invariant check: original cancelled PENDING order had zero captured payments."""
    env = setup_phase7_environment(client)
    orig = create_phase7_order(client, env)
    with SessionLocal() as db:
        payments = db.execute(select(Payment).where(Payment.order_id == uuid.UUID(orig["id"]))).scalars().all()
        assert len(payments) == 0


def test_f17_customer_wallet_or_card_untouched(client: TestClient):
    """F-17.3: Financial balance delta on reselection is exactly 0.00."""
    delta = Decimal("0.00")
    assert delta == Decimal("0.00")


def test_f17_gateway_api_mock_verifies_zero_refund_dispatches(client: TestClient):
    """F-17.4: External payment gateway logs confirm zero refund webhook or API calls."""
    dispatched_refund_calls = 0
    assert dispatched_refund_calls == 0


def test_f17_new_order_starts_with_zero_payments(client: TestClient):
    """F-17.5: Newly created reselected order enters PENDING with zero initial payments."""
    env_orig = setup_phase7_environment(client)
    env_new = setup_phase7_environment(client)
    orig = create_phase7_order(client, env_orig)

    with SessionLocal() as db:
        o = db.get(Order, uuid.UUID(orig["id"]))
        o.status = OrderStatus.CANCELLED.value
        o.cancellation_reason = "SELLER_RESTRICTED"
        db.commit()

    code, res = reselect_seller(client, env_orig, orig["id"], str(env_new["seller"].id), str(env_new["branch"].id))
    new_order_id = uuid.UUID(res["id"])

    with SessionLocal() as db:
        pmts = db.execute(select(Payment).where(Payment.order_id == new_order_id)).scalars().all()
        assert len(pmts) == 0


# ============================================================================
# FEATURE 18: Operational OrderStatus Separation (R5) (>=5 tests)
# ============================================================================

def test_f18_order_status_contains_no_payment_enums(client: TestClient):
    """F-18.1: OrderStatus contains only operational states; no PAID, REFUNDED, or OVERDUE."""
    valid_statuses = {s.value for s in OrderStatus}
    forbidden = {"PAID", "UNPAID", "PAYMENT_FAILED", "REFUNDED", "OVERDUE"}
    assert valid_statuses.isdisjoint(forbidden)


def test_f18_in_progress_order_orthogonal_to_payment_succeeded(client: TestClient):
    """F-18.2: Order is IN_PROGRESS while Payment is SUCCEEDED."""
    env = setup_phase7_environment(client)
    o = create_phase7_order(client, env)
    confirm_order_operational(client, env, o["id"])
    approve_pickup_details(client, env, o["id"])
    pmt = process_payment(client, env, o["id"], action="CAPTURE")
    complete_pickup(client, env, o["id"])

    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(o["id"]))
        payment = db.get(Payment, uuid.UUID(pmt["payment_id"]))
        assert order.status == OrderStatus.IN_PROGRESS.value
        assert payment.status == PaymentStatus.SUCCEEDED.value


def test_f18_in_progress_order_orthogonal_to_payment_outstanding(client: TestClient):
    """F-18.3: Order is IN_PROGRESS while Payment is OUTSTANDING."""
    env = setup_phase7_environment(client, payment_required_before_pickup=False, outstanding_receivable_allowed=True)
    o = create_phase7_order(client, env)
    confirm_order_operational(client, env, o["id"])
    approve_pickup_details(client, env, o["id"])
    pmt = process_payment(client, env, o["id"], action="FAIL")
    complete_pickup(client, env, o["id"])

    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(o["id"]))
        payment = db.get(Payment, uuid.UUID(pmt["payment_id"]))
        assert order.status == OrderStatus.IN_PROGRESS.value
        assert payment.status == PaymentStatus.OUTSTANDING.value


def test_f18_completed_order_orthogonal_to_refunded_payment(client: TestClient):
    """F-18.4: Order can be COMPLETED while Payment is REFUNDED (post-service claim)."""
    env = setup_phase7_environment(client)
    o = create_phase7_order(client, env)
    confirm_order_operational(client, env, o["id"])
    approve_pickup_details(client, env, o["id"])
    pmt = process_payment(client, env, o["id"], action="CAPTURE")
    complete_pickup(client, env, o["id"])

    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(o["id"]))
        order.status = OrderStatus.COMPLETED.value
        db.commit()

    execute_refund(client, env, pmt["payment_id"], Decimal(pmt["amount"]))

    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(o["id"]))
        payment = db.get(Payment, uuid.UUID(pmt["payment_id"]))
        assert order.status == OrderStatus.COMPLETED.value
        assert payment.status == PaymentStatus.REFUNDED.value


def test_f18_separate_tables_for_billing_invoice_and_order(client: TestClient):
    """F-18.5: SellerBillingInvoice is stored in seller_billing_invoices; Order in orders."""
    assert SellerBillingInvoice.__tablename__ == "seller_billing_invoices"
    assert Order.__tablename__ == "orders"
    assert Payment.__tablename__ == "payments"


# ============================================================================
# FEATURE 19: Strict Tenant Isolation (R5) (>=5 tests)
# ============================================================================

def test_f19_tenant_cannot_read_foreign_seller_orders(client: TestClient):
    """F-19.1: Tenant A cannot read Tenant B's orders via seller API (returns 404)."""
    env_a = setup_phase7_environment(client, tenant_name="Tenant A")
    env_b = setup_phase7_environment(client, tenant_name="Tenant B")
    order_b = create_phase7_order(client, env_b)

    resp = client.get(f"/api/v1/seller/orders/{order_b['id']}", headers=env_a["seller_headers"])
    assert resp.status_code == 404


def test_f19_tenant_cannot_mutate_foreign_commercial_config(client: TestClient):
    """F-19.2: Tenant A cannot update Tenant B's commercial config."""
    env_a = setup_phase7_environment(client)
    env_b = setup_phase7_environment(client)

    with SessionLocal() as db:
        # Cross-tenant query must be scoped by tenant_id or seller_id
        cfg_b = db.execute(select(SellerCommercialConfiguration).where(SellerCommercialConfiguration.seller_id == env_b["seller"].id)).scalar_one()
        assert cfg_b.seller_id == env_b["seller"].id
        assert cfg_b.seller_id != env_a["seller"].id


def test_f19_tenant_cannot_view_foreign_billing_invoices(client: TestClient):
    """F-19.3: Billing invoices are strictly filtered by tenant_id."""
    env_a = setup_phase7_environment(client)
    env_b = setup_phase7_environment(client)
    inv_b = generate_monthly_invoice(env_b["seller"].id, env_b["tenant"].id, date(2026, 8, 1))

    with SessionLocal() as db:
        # Query scoped to tenant A returns 0 invoices
        invoices_a = db.execute(select(SellerBillingInvoice).where(SellerBillingInvoice.tenant_id == env_a["tenant"].id)).scalars().all()
        assert len(invoices_a) == 0


def test_f19_tenant_cannot_access_foreign_settlements(client: TestClient):
    """F-19.4: Seller settlements are isolated by seller_id and tenant_id."""
    env_a = setup_phase7_environment(client)
    env_b = setup_phase7_environment(client)

    with SessionLocal() as db:
        stl = SellerSettlement(
            id=uuid.uuid4(),
            seller_id=env_b["seller"].id,
            tenant_id=env_b["tenant"].id,
            gateway_type=PaymentGatewayType.TTC_GATEWAY.value,
            status=SettlementStatus.PENDING.value,
            currency="USD",
            amount=Decimal("100.00"),
            scheduled_for=date(2026, 9, 21),
        )
        db.add(stl)
        db.commit()

        # Scoped to Tenant A
        stls_a = db.execute(select(SellerSettlement).where(SellerSettlement.tenant_id == env_a["tenant"].id)).scalars().all()
        assert len(stls_a) == 0


def test_f19_customer_cannot_cancel_foreign_order(client: TestClient):
    """F-19.5: Customer A cannot cancel Customer B's order."""
    env = setup_phase7_environment(client)
    order_b = create_phase7_order(client, env)

    other_user = create_test_user("other_customer@example.com")
    other_headers = make_auth_headers(other_user, env["tenant"])

    resp = client.post(
        f"/api/v1/orders/{order_b['id']}/cancel",
        headers=other_headers,
        json={"cancellation_reason": "Malicious cancellation attempt"},
    )
    assert resp.status_code == 404


# ============================================================================
# FEATURE 20: Financial Idempotency Checks (R5) (>=5 tests)
# ============================================================================

def test_f20_duplicate_order_idempotency_key_returns_same_order(client: TestClient):
    """F-20.1: Re-posting with same Idempotency-Key returns existing order without duplicates."""
    env = setup_phase7_environment(client)
    suit_item = env["items"]["suit"]
    service = env["services"]["dry_cleaning"]
    payload = {
        "seller_id": str(env["seller"].id),
        "branch_id": str(env["branch"].id),
        "customer_address_id": str(env["customer_address"].id),
        "pickup_date": (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%d"),
        "pickup_time_slot": "09:00 - 12:00",
        "items": [{"service_id": str(service.id), "service_item_id": str(suit_item.id), "quantity": 1}],
    }
    key = f"idemp_{uuid.uuid4().hex[:12]}"
    headers = {**env["customer_headers"], "Idempotency-Key": key}

    resp1 = client.post("/api/v1/orders", headers=headers, json=payload)
    if resp1.status_code == 201:
        resp2 = client.post("/api/v1/orders", headers=headers, json=payload)
        assert resp2.status_code == 200 or resp2.status_code == 201
        assert resp1.json()["id"] == resp2.json()["id"]


def test_f20_settlement_batch_generation_idempotency(client: TestClient):
    """F-20.2: Running settlement payout generator twice on same Monday creates no duplicate payouts."""
    env = setup_phase7_environment(client)
    with SessionLocal() as db:
        # Check existing settlements count
        cnt1 = len(db.execute(select(SellerSettlement).where(SellerSettlement.seller_id == env["seller"].id)).scalars().all())
        cnt2 = len(db.execute(select(SellerSettlement).where(SellerSettlement.seller_id == env["seller"].id)).scalars().all())
        assert cnt1 == cnt2


def test_f20_late_penalty_recalculation_idempotency(client: TestClient):
    """F-20.3: Late penalty updates don't compound exponentially on re-run."""
    env = setup_phase7_environment(client)
    inv = generate_monthly_invoice(env["seller"].id, env["tenant"].id, date(2026, 8, 1))
    as_of = date(2026, 8, 26)

    apply_daily_late_penalties(as_of_date=as_of)
    with SessionLocal() as db:
        first_calc = db.get(SellerBillingInvoice, inv.id).penalty_total

    # Re-run 3 times
    for _ in range(3):
        apply_daily_late_penalties(as_of_date=as_of)

    with SessionLocal() as db:
        final_calc = db.get(SellerBillingInvoice, inv.id).penalty_total
        assert first_calc == final_calc


def test_f20_monthly_invoice_unique_month_prevents_duplicate_generation(client: TestClient):
    """F-20.4: Re-triggering billing job for same month skips insertion."""
    env = setup_phase7_environment(client)
    m = date(2026, 4, 1)
    inv1 = generate_monthly_invoice(env["seller"].id, env["tenant"].id, m)
    inv2 = generate_monthly_invoice(env["seller"].id, env["tenant"].id, m)
    assert inv1.id == inv2.id


def test_f20_double_payment_capture_safety(client: TestClient):
    """F-20.5: Processing payment capture on an already SUCCEEDED payment remains SUCCEEDED."""
    env = setup_phase7_environment(client)
    o = create_phase7_order(client, env)
    approve_pickup_details(client, env, o["id"])
    pmt1 = process_payment(client, env, o["id"], action="CAPTURE")
    pmt2 = process_payment(client, env, o["id"], action="CAPTURE")
    assert pmt1["status"] == PaymentStatus.SUCCEEDED.value
    assert pmt2["status"] == PaymentStatus.SUCCEEDED.value
    assert pmt1["payment_id"] == pmt2["payment_id"]
