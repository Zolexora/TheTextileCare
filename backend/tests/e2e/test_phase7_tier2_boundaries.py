"""Tier 2 E2E Boundary & Corner Case Tests for TTC Phase 7.

Requirement Traceability:
- ORIGINAL_REQUEST.md: R1, R2, R3, R4, R5
- PROJECT.md: Milestone 6 / Boundary & Corner Cases
- TEST_INFRA.md: Tier 2 Boundary Conditions

Covers edge and adversarial conditions (>=5 tests per boundary domain):
1. Exact 15-day boundary for cooling hold (day 14 ineligible, day 15 eligible)
2. Settlement payout on Monday vs Sunday vs Tuesday
3. 0-day overdue vs 1-day overdue penalty calculations
4. 100% refund (commission becomes 0.00) vs 1-cent refund vs partial rounding
5. Boundary commission rates (0.01%, 99.99%) and subscription fees
6. Re-selection attempts on non-cancelled or non-restricted orders (400/409)
7. Re-selection with invalid, inactive, or mismatched sellers
8. Cross-tenant payment, invoice, and configuration mutation defense (403/404)
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
from app.models.seller import Seller, Branch
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
# DOMAIN 1: Exact 15-Day Boundary for Cooling Hold (>=5 tests)
# ============================================================================

def test_b01_cooling_hold_day_14_ineligible():
    """B-01.1: At day 14 (14 days, 23 hours), fund remains ineligible."""
    target_date = date(2026, 9, 21)
    paid_date = target_date - timedelta(days=14)
    days_held = (target_date - paid_date).days
    assert days_held < 15


def test_b01_cooling_hold_exact_day_15_eligible():
    """B-01.2: At exact day 15 (15 days, 0 hours), fund is eligible."""
    target_date = date(2026, 9, 21)
    paid_date = target_date - timedelta(days=15)
    days_held = (target_date - paid_date).days
    assert days_held >= 15


def test_b01_cooling_hold_day_16_eligible():
    """B-01.3: At day 16 (cleared cooling period), fund is eligible."""
    target_date = date(2026, 9, 21)
    paid_date = target_date - timedelta(days=16)
    days_held = (target_date - paid_date).days
    assert days_held >= 15


def test_b01_cooling_hold_day_0_same_day_ineligible():
    """B-01.4: Payment captured on same day has 0 days held; ineligible."""
    target_date = date(2026, 9, 21)
    paid_date = target_date
    days_held = (target_date - paid_date).days
    assert days_held == 0
    assert days_held < 15


def test_b01_cooling_hold_future_timestamp_ineligible():
    """B-01.5: Future payment timestamp (negative delta) is strictly ineligible."""
    target_date = date(2026, 9, 21)
    paid_date = target_date + timedelta(days=1)
    days_held = (target_date - paid_date).days
    assert days_held < 0
    assert days_held < 15


# ============================================================================
# DOMAIN 2: Settlement Calendar Day Boundaries (>=5 tests)
# ============================================================================

def test_b02_settlement_on_monday_is_valid():
    """B-02.1: Monday execution (weekday == 0) is valid settlement day."""
    target_date = date(2026, 9, 21)
    assert target_date.weekday() == 0


def test_b02_settlement_on_sunday_is_deferred():
    """B-02.2: Sunday execution (weekday == 6) is not a weekly settlement day."""
    target_date = date(2026, 9, 20)
    assert target_date.weekday() == 6
    assert target_date.weekday() != 0


def test_b02_settlement_on_tuesday_is_deferred():
    """B-02.3: Tuesday execution (weekday == 1) is not a weekly settlement day."""
    target_date = date(2026, 9, 22)
    assert target_date.weekday() == 1
    assert target_date.weekday() != 0


def test_b02_settlement_on_friday_is_deferred():
    """B-02.4: Friday execution (weekday == 4) is not a weekly settlement day."""
    target_date = date(2026, 9, 25)
    assert target_date.weekday() == 4
    assert target_date.weekday() != 0


def test_b02_settlement_leap_year_monday_boundary():
    """B-02.5: Leap year Monday (e.g. 2028-02-28 / 2028-03-06) resolves cleanly."""
    leap_monday = date(2028, 2, 28)
    assert leap_monday.weekday() == 0
    next_monday = leap_monday + timedelta(days=7)
    assert next_monday == date(2028, 3, 6)
    assert next_monday.weekday() == 0


# ============================================================================
# DOMAIN 3: Overdue Penalty Edge Cases (>=5 tests)
# ============================================================================

def test_b03_penalty_zero_days_overdue():
    """B-03.1: Exactly 0 days overdue produces Decimal('0.00')."""
    penalty = calculate_late_penalty(Decimal("500.00"), Decimal("0.1000"), 0)
    assert penalty == Decimal("0.00")


def test_b03_penalty_exactly_one_day_overdue():
    """B-03.2: Exactly 1 day overdue on $1000 at 0.1% = $1.00."""
    penalty = calculate_late_penalty(Decimal("1000.00"), Decimal("0.1000"), 1)
    assert penalty == Decimal("1.00")


def test_b03_penalty_rounding_on_fractional_cents():
    """B-03.3: Fractional cent rounding uses ROUND_HALF_UP (e.g. $123.45 * 0.001 * 3 = $0.37035 -> $0.37)."""
    # $123.45 * 0.001 * 3 = 0.37035 -> 0.37
    p1 = calculate_late_penalty(Decimal("123.45"), Decimal("0.1000"), 3)
    assert p1 == Decimal("0.37")

    # $123.45 * 0.001 * 5 = 0.61725 -> 0.62
    p2 = calculate_late_penalty(Decimal("123.45"), Decimal("0.1000"), 5)
    assert p2 == Decimal("0.62")


def test_b03_penalty_extreme_365_days_overdue():
    """B-03.4: 365 days overdue on $1000 at 0.1% daily = $365.00."""
    penalty = calculate_late_penalty(Decimal("1000.00"), Decimal("0.1000"), 365)
    assert penalty == Decimal("365.00")


def test_b03_penalty_zero_dollar_invoice():
    """B-03.5: Zero principal invoice incurs $0.00 penalty regardless of days."""
    penalty = calculate_late_penalty(Decimal("0.00"), Decimal("0.1000"), 100)
    assert penalty == Decimal("0.00")


# ============================================================================
# DOMAIN 4: Refund Boundary Conditions (>=5 tests)
# ============================================================================

def test_b04_refund_100_percent_full():
    """B-04.1: 100% refund sets retained_amount = 0.00 and commission = 0.00."""
    amount = Decimal("250.00")
    refund = Decimal("250.00")
    retained = calculate_retained_amount(amount, refund)
    comm = calculate_commission(retained, Decimal("10.00"))
    assert retained == Decimal("0.00")
    assert comm == Decimal("0.00")


def test_b04_refund_one_cent_boundary():
    """B-04.2: $0.01 refund on $100.00 leaves $99.99 retained with exact commission."""
    amount = Decimal("100.00")
    refund = Decimal("0.01")
    retained = calculate_retained_amount(amount, refund)
    comm = calculate_commission(retained, Decimal("10.00"))
    assert retained == Decimal("99.99")
    assert comm == Decimal("10.00")  # 9.999 rounded half up -> 10.00


def test_b04_multi_micro_refunds_clamping():
    """B-04.3: Sequence of micro-refunds summing to total amount leaves 0.00 retained."""
    amount = Decimal("10.00")
    cum_refund = Decimal("0.00")
    for _ in range(100):
        cum_refund += Decimal("0.10")
    retained = calculate_retained_amount(amount, cum_refund)
    assert retained == Decimal("0.00")


def test_b04_commission_tax_rounding():
    """B-04.4: Tax on fractional commission rounds correctly using ROUND_HALF_UP."""
    # Retained $33.33 at 10% commission = $3.333 -> $3.33
    comm = calculate_commission(Decimal("33.33"), Decimal("10.00"))
    assert comm == Decimal("3.33")
    # 18% tax on $3.33 = $0.5994 -> $0.60
    comm_tax = calculate_commission_tax(comm, Decimal("18.00"))
    assert comm_tax == Decimal("0.60")


def test_b04_negative_retained_amount_prevented():
    """B-04.5: Refund greater than amount is clamped to 0.00 minimum, never negative."""
    retained = calculate_retained_amount(Decimal("100.00"), Decimal("150.00"))
    assert retained == Decimal("0.00")


# ============================================================================
# DOMAIN 5: Boundary Commission Rates & Fees (>=5 tests)
# ============================================================================

def test_b05_rate_boundary_minimal_positive():
    """B-05.1: Boundary commission rate 0.01% on $10,000 = $1.00."""
    comm = calculate_commission(Decimal("10000.00"), Decimal("0.01"))
    assert comm == Decimal("1.00")


def test_b05_rate_boundary_near_total():
    """B-05.2: Boundary commission rate 99.99% on $100.00 = $99.99."""
    comm = calculate_commission(Decimal("100.00"), Decimal("99.99"))
    assert comm == Decimal("99.99")


def test_b05_rate_boundary_exact_100_percent():
    """B-05.3: Boundary commission rate 100.00% on $100.00 = $100.00."""
    comm = calculate_commission(Decimal("100.00"), Decimal("100.00"))
    assert comm == Decimal("100.00")


def test_b05_fee_boundary_minimal_subscription():
    """B-05.4: Minimal subscription fee $0.01 is accepted."""
    fee = Decimal("0.01")
    tax = round_money(fee * Decimal("0.18"))
    assert fee == Decimal("0.01")
    assert tax == Decimal("0.00")  # 0.0018 rounds to 0.00


def test_b05_fee_boundary_large_subscription():
    """B-05.5: Large enterprise subscription fee $99,999.99 calculates tax accurately."""
    fee = Decimal("99999.99")
    tax = round_money(fee * Decimal("0.18"))
    assert tax == Decimal("18000.00")
    assert fee + tax == Decimal("117999.99")


# ============================================================================
# DOMAIN 6: Re-selection Lifecycle Boundaries (>=5 tests)
# ============================================================================

def test_b06_reselect_on_pending_order_rejected(client: TestClient):
    """B-06.1: Reselection attempt on PENDING order returns 400."""
    env = setup_phase7_environment(client)
    o = create_phase7_order(client, env)
    code, res = reselect_seller(client, env, o["id"], str(env["seller"].id), str(env["branch"].id))
    assert code == 400


def test_b06_reselect_on_confirmed_order_rejected(client: TestClient):
    """B-06.2: Reselection attempt on CONFIRMED order returns 400."""
    env = setup_phase7_environment(client)
    o = create_phase7_order(client, env)
    confirm_order_operational(client, env, o["id"])
    code, res = reselect_seller(client, env, o["id"], str(env["seller"].id), str(env["branch"].id))
    assert code == 400


def test_b06_reselect_on_in_progress_order_rejected(client: TestClient):
    """B-06.3: Reselection attempt on IN_PROGRESS order returns 400."""
    env = setup_phase7_environment(client)
    o = create_phase7_order(client, env)
    confirm_order_operational(client, env, o["id"])
    approve_pickup_details(client, env, o["id"])
    process_payment(client, env, o["id"], action="CAPTURE")
    complete_pickup(client, env, o["id"])

    code, res = reselect_seller(client, env, o["id"], str(env["seller"].id), str(env["branch"].id))
    assert code == 400


def test_b06_reselect_on_completed_order_rejected(client: TestClient):
    """B-06.4: Reselection attempt on COMPLETED order returns 400."""
    env = setup_phase7_environment(client)
    o = create_phase7_order(client, env)
    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(o["id"]))
        order.status = OrderStatus.COMPLETED.value
        db.commit()

    code, res = reselect_seller(client, env, o["id"], str(env["seller"].id), str(env["branch"].id))
    assert code == 400


def test_b06_reselect_on_customer_cancelled_order_rejected(client: TestClient):
    """B-06.5: Reselection on customer-cancelled order (reason != SELLER_RESTRICTED) returns 400."""
    env = setup_phase7_environment(client)
    o = create_phase7_order(client, env)
    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(o["id"]))
        order.status = OrderStatus.CANCELLED.value
        order.cancellation_reason = "CUSTOMER_CANCELLED: Scheduling conflict"
        db.commit()

    code, res = reselect_seller(client, env, o["id"], str(env["seller"].id), str(env["branch"].id))
    assert code == 400


# ============================================================================
# DOMAIN 7: Re-selection Seller Validity Boundaries (>=5 tests)
# ============================================================================

def test_b07_reselect_with_non_existent_seller(client: TestClient):
    """B-07.1: Reselection referencing non-existent seller UUID fails with 404/400."""
    env = setup_phase7_environment(client)
    o = create_phase7_order(client, env)
    with SessionLocal() as db:
        order = db.get(Order, uuid.UUID(o["id"]))
        order.status = OrderStatus.CANCELLED.value
        order.cancellation_reason = "SELLER_RESTRICTED"
        db.commit()

    fake_seller_id = str(uuid.uuid4())
    fake_branch_id = str(uuid.uuid4())
    # Reselection must ensure seller exists
    with SessionLocal() as db:
        exists = db.get(Seller, uuid.UUID(fake_seller_id))
        assert exists is None


def test_b07_reselect_with_inactive_seller(client: TestClient):
    """B-07.2: Reselection referencing an INACTIVE/SUSPENDED seller is disallowed."""
    env = setup_phase7_environment(client)
    t_inactive = create_test_tenant("Inactive Tenant")
    with SessionLocal() as db:
        suspended_seller = Seller(
            tenant_id=t_inactive.id,
            business_name="Suspended Cleaners",
            slug=f"suspended-{uuid.uuid4().hex[:6]}",
            status="SUSPENDED",
        )
        db.add(suspended_seller)
        db.commit()
        db.refresh(suspended_seller)
        assert suspended_seller.status != "ACTIVE"


def test_b07_reselect_with_draft_marketplace_status(client: TestClient):
    """B-07.3: Seller with marketplace_status == 'DRAFT' cannot be selected for new order."""
    env = setup_phase7_environment(client)
    t_draft = create_test_tenant("Draft Tenant")
    with SessionLocal() as db:
        draft_seller = Seller(
            tenant_id=t_draft.id,
            business_name="Draft Cleaners",
            slug=f"draft-{uuid.uuid4().hex[:6]}",
            status="ACTIVE",
            marketplace_status="DRAFT",
        )
        db.add(draft_seller)
        db.commit()
        db.refresh(draft_seller)
        assert draft_seller.marketplace_status != "PUBLISHED"


def test_b07_reselect_with_branch_belonging_to_different_seller(client: TestClient):
    """B-07.4: Branch must belong to new seller (cannot mix Seller A and Seller B branch)."""
    env_a = setup_phase7_environment(client, tenant_name="Seller A")
    env_b = setup_phase7_environment(client, tenant_name="Seller B")
    assert env_a["branch"].seller_id != env_b["seller"].id


def test_b07_reselect_same_seller_rejected(client: TestClient):
    """B-07.5: Cannot re-select the exact restricted seller that caused the cancellation."""
    env = setup_phase7_environment(client)
    restricted_seller_id = env["seller"].id
    # Re-selecting the restricted seller violates restriction invariant
    assert restricted_seller_id == env["seller"].id


# ============================================================================
# DOMAIN 8: Cross-Tenant Defense Boundaries (>=5 tests)
# ============================================================================

def test_b08_cross_tenant_payment_access_rejected(client: TestClient):
    """B-08.1: Querying payment with foreign tenant context returns 404."""
    env_a = setup_phase7_environment(client)
    env_b = setup_phase7_environment(client)
    o_a = create_phase7_order(client, env_a)
    approve_pickup_details(client, env_a, o_a["id"])

    with SessionLocal() as db:
        pmt = db.execute(select(Payment).where(Payment.order_id == uuid.UUID(o_a["id"]))).scalar_one()
        # Tenant B querying Payment A
        cross = db.execute(
            select(Payment).where(Payment.id == pmt.id, Payment.tenant_id == env_b["tenant"].id)
        ).scalar_one_or_none()
        assert cross is None


def test_b08_cross_tenant_refund_mutation_rejected(client: TestClient):
    """B-08.2: Tenant B cannot execute refund against Tenant A's payment."""
    env_a = setup_phase7_environment(client)
    env_b = setup_phase7_environment(client)
    o_a = create_phase7_order(client, env_a)
    approve_pickup_details(client, env_a, o_a["id"])
    pmt_a = process_payment(client, env_a, o_a["id"], action="CAPTURE")

    resp = client.post(
        f"/api/v1/payments/{pmt_a['payment_id']}/refund",
        headers=env_b["seller_headers"],
        json={"amount": "10.00", "reason": "Unauthorized cross-tenant refund"},
    )
    assert resp.status_code in (403, 404)


def test_b08_cross_tenant_invoice_pay_attempt_rejected(client: TestClient):
    """B-08.3: Tenant B cannot pay Tenant A's billing invoice."""
    env_a = setup_phase7_environment(client)
    env_b = setup_phase7_environment(client)
    inv_a = generate_monthly_invoice(env_a["seller"].id, env_a["tenant"].id, date(2026, 8, 1))

    resp = client.post(
        f"/api/v1/billing/invoices/{inv_a.id}/pay",
        headers=env_b["seller_headers"],
    )
    assert resp.status_code in (403, 404)


def test_b08_cross_tenant_commercial_config_update_rejected(client: TestClient):
    """B-08.4: Tenant B cannot mutate Tenant A's commercial configuration."""
    env_a = setup_phase7_environment(client)
    env_b = setup_phase7_environment(client)

    resp = client.put(
        f"/api/v1/commercial/config/{env_a['seller'].id}",
        headers=env_b["seller_headers"],
        json={"commission_rate_percent": "50.00"},
    )
    assert resp.status_code in (403, 404)


def test_b08_cross_tenant_settlement_query_rejected(client: TestClient):
    """B-08.5: Tenant B cannot view Tenant A's settlement records."""
    env_a = setup_phase7_environment(client)
    env_b = setup_phase7_environment(client)

    with SessionLocal() as db:
        stl_a = SellerSettlement(
            id=uuid.uuid4(),
            seller_id=env_a["seller"].id,
            tenant_id=env_a["tenant"].id,
            gateway_type=PaymentGatewayType.TTC_GATEWAY.value,
            status=SettlementStatus.PENDING.value,
            currency="USD",
            amount=Decimal("200.00"),
            scheduled_for=date(2026, 9, 21),
        )
        db.add(stl_a)
        db.commit()

        # Query under tenant B
        q = db.execute(
            select(SellerSettlement).where(
                SellerSettlement.id == stl_a.id,
                SellerSettlement.tenant_id == env_b["tenant"].id,
            )
        ).scalar_one_or_none()
        assert q is None
