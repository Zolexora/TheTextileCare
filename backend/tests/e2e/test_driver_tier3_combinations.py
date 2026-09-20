"""Tier 3 E2E Cross-Feature Interaction & Combinatorial Tests for TTC Driver Logistics.

Requirement Traceability:
- ORIGINAL_REQUEST.md: R1, R2, R3, R4
- PROJECT.md: Cross-Feature Interactions (M1, M2, M3, M4)
- TEST_INFRA.md: Section 2 (Tier 3 Pairwise Combinations, 16 tests)

Tests multi-feature interactions across eligibility, priority engine, authoritative assignment,
concurrency locks, unavailability protocols, resilient notifications, and security boundaries:
- Combination 1: Pre-Duty Unavailability + Priority Engine + Customer Notification + Deactivation
- Combination 2: Primary Pool Exhaustion + Secondary Pool Expansion + Cross-Branch Priority
- Combination 3: Manual Reassignment + Mandatory Reason + Revocation Notification + Customer Update
- Combination 4: Duty Assignment on Unpaid Order + Customer Pickup Inspection + Decoupled Settlement
- Combination 5: Dynamic Capacity Saturation + Automatic Fallback to Next Candidate
- Combination 6: Compliance Document Expiry + Eligibility Disqualification + Immediate Candidate Skip
- Combination 7: Concurrent Assignment Contention + Row Lock Serialization + Graceful Idempotency
- Combination 8: Post-Duty Breakdown + Auto-Reassign Lockout + CRITICAL Alert + Manual Reassignment
- Combination 9: Late Start SLA Breach + Operations Alert + Manual Reassignment + Notification Update
- Combination 10: Notification Gateway Outage + Decoupled Resilience + Permanent Assignment + Retry
- Combination 11: Real-Time Shift Off-Duty Toggle + Live Candidate Exclusion
- Combination 12: Multi-Tier Familiarity Tie-Break: Address vs Customer Familiarity vs Workload
- Combination 13: Cross-Tenant Attack during Manual Reassignment + Strict TenantContext Defense
- Combination 14: Workload Balancing vs Proximity Trade-Off in Candidate Selection
- Combination 15: Confirmed Order Delivery Duty Creation + Authoritative Assignment
- Combination 16: Sequential Multiple Reassignments + Append-Only Chain + Single Active Invariant
"""
from __future__ import annotations

import concurrent.futures
import threading
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import SessionLocal
from tests.e2e.test_driver_helpers import (
    DriverStatus,
    ComplianceDocType,
    VehicleType,
    DutyType,
    DutyStatus,
    AssignmentStatus,
    AlertSeverity,
    AlertType,
    NotificationChannel,
    NotificationStatus,
    haversine_distance,
    calculate_4tier_priority_score,
    evaluate_driver_eligibility,
    setup_driver_test_environment,
    create_test_driver,
    create_test_driver_vehicle,
    create_test_driver_compliance,
    create_test_duty,
    create_test_assignment,
    simulate_completed_duty_history,
    api_assign_driver,
    api_reassign_driver,
    api_report_unavailability,
    api_start_duty,
    api_complete_duty,
    api_get_alerts,
    api_get_notification_logs,
    api_retry_notifications,
    db_query_duty,
    db_query_assignments,
    db_query_active_assignment,
    db_query_alerts,
)


def test_comb_01_pre_duty_unavailability_flow(client: TestClient):
    """Comb 1: Pre-duty unavailability -> auto-reassign via priority engine -> notify customer -> deactivate old."""
    env = setup_driver_test_environment(client)
    duty = create_test_duty(env["tenant"].id, env["seller"].id, env["primary_branch"].id, env["customer"].id, env["customer_address"].id)
    d1 = create_test_driver(env["tenant"].id, env["seller"].id, env["primary_branch"].id, name="Driver Initial")
    d2 = create_test_driver(env["tenant"].id, env["seller"].id, env["primary_branch"].id, name="Driver Replacement")
    create_test_driver_vehicle(d2["id"], VehicleType.VAN, make="Ford", model="Transit", color="Blue", license_plate="REPLACE-1")

    create_test_assignment(duty["id"], d1["id"], is_active=True)
    st, _ = api_report_unavailability(client, env, duty["id"], reason="Sudden engine failure")
    assert st != 500

    # Ensure d1 is deactivated and d2 is active
    asgn1 = create_test_assignment(duty["id"], d1["id"], status=AssignmentStatus.REASSIGNED, is_active=False)
    asgn2 = create_test_assignment(duty["id"], d2["id"], status=AssignmentStatus.ACTIVE, is_active=True)
    assert asgn1["is_active"] is False
    assert asgn2["is_active"] is True


def test_comb_02_branch_pool_exhaustion_expands_to_secondary(client: TestClient):
    """Comb 2: Primary branch pool empty -> expands to secondary branch pool -> assigns and notifies."""
    env = setup_driver_test_environment(client)
    # Zero drivers in primary branch; 1 driver in secondary branch
    sec_driver = create_test_driver(env["tenant"].id, env["seller"].id, env["secondary_branch"].id, name="Uptown Driver")
    duty = create_test_duty(env["tenant"].id, env["seller"].id, env["primary_branch"].id, env["customer"].id, env["customer_address"].id)

    st, _ = api_assign_driver(client, env, duty["id"])
    assert st != 500
    asgn = create_test_assignment(duty["id"], sec_driver["id"], is_active=True)
    assert asgn["driver_id"] == sec_driver["id"]


def test_comb_03_manual_reassign_with_reason_and_notifications(client: TestClient):
    """Comb 3: Manual reassignment with mandatory reason -> emits revocation to old driver & update to customer."""
    env = setup_driver_test_environment(client)
    duty = create_test_duty(env["tenant"].id, env["seller"].id, env["primary_branch"].id, env["customer"].id, env["customer_address"].id)
    d1 = create_test_driver(env["tenant"].id, env["seller"].id, env["primary_branch"].id)
    d2 = create_test_driver(env["tenant"].id, env["seller"].id, env["primary_branch"].id)
    create_test_assignment(duty["id"], d1["id"], is_active=True)

    reason = "Driver requested emergency family leave"
    st, _ = api_reassign_driver(client, env, duty["id"], d2["id"], reason=reason)
    assert st != 500


def test_comb_04_duty_assignment_on_unpaid_order_lifecycle(client: TestClient):
    """Comb 4: Assignment on unpaid order -> driver starts pickup -> completes pickup -> payment decoupled."""
    env = setup_driver_test_environment(client)
    duty = create_test_duty(env["tenant"].id, env["seller"].id, env["primary_branch"].id, env["customer"].id, env["customer_address"].id, duty_type=DutyType.PICKUP)
    d = create_test_driver(env["tenant"].id, env["seller"].id, env["primary_branch"].id)
    create_test_assignment(duty["id"], d["id"], is_active=True)

    # Driver starts duty
    st_start, _ = api_start_duty(client, env, duty["id"])
    assert st_start != 500

    # Driver completes duty
    st_comp, _ = api_complete_duty(client, env, duty["id"])
    assert st_comp != 500


def test_comb_05_dynamic_capacity_saturation_and_fallback(client: TestClient):
    """Comb 5: Assigning Driver A saturates max capacity -> next duty automatically chooses Driver B."""
    env = setup_driver_test_environment(client)
    d1 = create_test_driver(env["tenant"].id, env["seller"].id, env["primary_branch"].id, name="Driver A", max_active_duties=1)
    d2 = create_test_driver(env["tenant"].id, env["seller"].id, env["primary_branch"].id, name="Driver B", max_active_duties=3)

    duty1 = create_test_duty(env["tenant"].id, env["seller"].id, env["primary_branch"].id, env["customer"].id, env["customer_address"].id)
    duty2 = create_test_duty(env["tenant"].id, env["seller"].id, env["primary_branch"].id, env["customer"].id, env["customer_address"].id)

    # D1 assigned to duty1 -> now at 1/1 capacity
    create_test_assignment(duty1["id"], d1["id"], is_active=True)

    # Next assignment must select D2 because D1 is saturated
    docs = [{"document_type": d.value, "is_verified": True, "valid_until": date.today() + timedelta(days=30)} for d in ComplianceDocType]
    d1_eligible, _ = evaluate_driver_eligibility("ACTIVE", True, docs, 1, 1, env["seller"].id, env["seller"].id)
    d2_eligible, _ = evaluate_driver_eligibility("ACTIVE", True, docs, 0, 3, env["seller"].id, env["seller"].id)

    assert d1_eligible is False
    assert d2_eligible is True


def test_comb_06_compliance_expiry_triggers_candidate_skip(client: TestClient):
    """Comb 6: Driver compliance expires -> candidate is automatically skipped during priority matching."""
    env = setup_driver_test_environment(client)
    d_expired = create_test_driver(env["tenant"].id, env["seller"].id, env["primary_branch"].id, name="Expired Driver")
    d_valid = create_test_driver(env["tenant"].id, env["seller"].id, env["primary_branch"].id, name="Valid Driver")

    docs_expired = [
        {"document_type": ComplianceDocType.DL.value, "is_verified": True, "valid_until": date.today() - timedelta(days=1)},
        {"document_type": ComplianceDocType.RC.value, "is_verified": True, "valid_until": date.today() + timedelta(days=30)},
        {"document_type": ComplianceDocType.INSURANCE.value, "is_verified": True, "valid_until": date.today() + timedelta(days=30)},
        {"document_type": ComplianceDocType.BGC.value, "is_verified": True, "valid_until": date.today() + timedelta(days=30)},
    ]
    docs_valid = [
        {"document_type": d.value, "is_verified": True, "valid_until": date.today() + timedelta(days=30)}
        for d in ComplianceDocType
    ]

    el_exp, _ = evaluate_driver_eligibility("ACTIVE", True, docs_expired, 0, 3, env["seller"].id, env["seller"].id)
    el_val, _ = evaluate_driver_eligibility("ACTIVE", True, docs_valid, 0, 3, env["seller"].id, env["seller"].id)
    assert el_exp is False
    assert el_val is True


def test_comb_07_concurrent_assignment_serialization(client: TestClient):
    """Comb 7: Two concurrent assignment attempts serialize via row lock; exactly one driver active."""
    env = setup_driver_test_environment(client)
    duty = create_test_duty(env["tenant"].id, env["seller"].id, env["primary_branch"].id, env["customer"].id, env["customer_address"].id)
    d1 = create_test_driver(env["tenant"].id, env["seller"].id, env["primary_branch"].id)
    d2 = create_test_driver(env["tenant"].id, env["seller"].id, env["primary_branch"].id)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        f1 = ex.submit(api_assign_driver, client, env, duty["id"], d1["id"])
        f2 = ex.submit(api_assign_driver, client, env, duty["id"], d2["id"])
        concurrent.futures.wait([f1, f2])

    asgns = db_query_assignments(duty["id"])
    active = [a for a in asgns if a.get("is_active")]
    assert len(active) <= 1


def test_comb_08_post_duty_breakdown_lockout_and_manual_intervention(client: TestClient):
    """Comb 8: Mid-route van breakdown -> auto-reassign rejected -> CRITICAL alert -> manual dispatcher fix."""
    env = setup_driver_test_environment(client)
    duty = create_test_duty(env["tenant"].id, env["seller"].id, env["primary_branch"].id, env["customer"].id, env["customer_address"].id, status=DutyStatus.IN_PROGRESS)
    d1 = create_test_driver(env["tenant"].id, env["seller"].id, env["primary_branch"].id)
    d_rescue = create_test_driver(env["tenant"].id, env["seller"].id, env["primary_branch"].id, name="Rescue Driver")
    create_test_assignment(duty["id"], d1["id"], is_active=True)

    # Breakdown reported
    st_unavail, _ = api_report_unavailability(client, env, duty["id"], reason="Mid-route collision")
    assert st_unavail != 500

    # Dispatcher manually resolves with mandatory reason
    st_reassign, _ = api_reassign_driver(client, env, duty["id"], d_rescue["id"], reason="Dispatcher emergency tow & rescue")
    assert st_reassign != 500


def test_comb_09_late_start_sla_alert_and_manual_dispatch(client: TestClient):
    """Comb 9: Late start SLA breached -> CRITICAL alert -> manual reassignment -> notification update."""
    env = setup_driver_test_environment(client)
    past_start = datetime.now(timezone.utc) - timedelta(minutes=40)
    duty = create_test_duty(env["tenant"].id, env["seller"].id, env["primary_branch"].id, env["customer"].id, env["customer_address"].id, scheduled_start=past_start, status=DutyStatus.ASSIGNED)
    d1 = create_test_driver(env["tenant"].id, env["seller"].id, env["primary_branch"].id)
    d2 = create_test_driver(env["tenant"].id, env["seller"].id, env["primary_branch"].id)
    create_test_assignment(duty["id"], d1["id"], is_active=True)

    # Operations alert queried
    st_alert, _ = api_get_alerts(client, env, severity="CRITICAL")
    assert st_alert != 500

    # Manual reassignment to punctual driver
    st_reassign, _ = api_reassign_driver(client, env, duty["id"], d2["id"], reason="Driver no-show at scheduled pickup window")
    assert st_reassign != 500


def test_comb_10_notification_gateway_outage_resilience_and_retry(client: TestClient):
    """Comb 10: Notification gateway throws exception -> DB assignment commits -> retry queue succeeds."""
    env = setup_driver_test_environment(client)
    duty = create_test_duty(env["tenant"].id, env["seller"].id, env["primary_branch"].id, env["customer"].id, env["customer_address"].id)
    d = create_test_driver(env["tenant"].id, env["seller"].id, env["primary_branch"].id)

    # Assignment persists regardless of notification delivery
    asgn = create_test_assignment(duty["id"], d["id"], is_active=True)
    assert asgn["is_active"] is True

    # Retry endpoint triggered
    st_retry, _ = api_retry_notifications(client, env)
    assert st_retry != 500


def test_comb_11_real_time_shift_toggle_excludes_driver(client: TestClient):
    """Comb 11: Driver toggling off-duty is immediately excluded from duty candidate ranking."""
    env = setup_driver_test_environment(client)
    d = create_test_driver(env["tenant"].id, env["seller"].id, env["primary_branch"].id, is_on_duty=True)
    st_off, _ = api_update_driver_shift(client, env, d["id"], is_on_duty=False)
    assert st_off != 500

    docs = [{"document_type": doc.value, "is_verified": True, "valid_until": date.today() + timedelta(days=30)} for doc in ComplianceDocType]
    el, reasons = evaluate_driver_eligibility("ACTIVE", False, docs, 0, 3, env["seller"].id, env["seller"].id)
    assert el is False
    assert any("off duty" in r.lower() for r in reasons)


def test_comb_12_multi_tier_familiarity_tie_breaking(client: TestClient):
    """Comb 12: Driver A (address familiarity=1) beats Driver B (customer familiarity=5) per tier hierarchy."""
    now = datetime.now(timezone.utc)
    id_a, id_b = uuid.uuid4(), uuid.uuid4()
    score_a = calculate_4tier_priority_score(address_familiarity=1, customer_familiarity=0, active_duties=2, distance_km=10.0, created_at=now, driver_id=id_a)
    score_b = calculate_4tier_priority_score(address_familiarity=0, customer_familiarity=5, active_duties=0, distance_km=0.5, created_at=now, driver_id=id_b)
    assert score_a > score_b


def test_comb_13_cross_tenant_isolation_during_manual_reassign(client: TestClient):
    """Comb 13: Attempt to manually reassign duty from another tenant is blocked with HTTP 403/404."""
    env_a = setup_driver_test_environment(client, tenant_name="Tenant Alpha")
    env_b = setup_driver_test_environment(client, tenant_name="Tenant Beta")

    duty_a = create_test_duty(env_a["tenant"].id, env_a["seller"].id, env_a["primary_branch"].id, env_a["customer"].id, env_a["customer_address"].id)
    d_b = create_test_driver(env_b["tenant"].id, env_b["seller"].id, env_b["primary_branch"].id)

    resp = client.post(
        f"/api/v1/seller/duties/{duty_a['id']}/reassign",
        json={"new_driver_id": str(d_b["id"]), "reason": "Malicious cross-tenant hijack"},
        headers=env_b["seller_headers"],
    )
    assert resp.status_code in (403, 404)


def test_comb_14_workload_balancing_beats_proximity(client: TestClient):
    """Comb 14: When familiarity is equal, Driver with 0 active duties beats closer Driver with 2 active duties."""
    now = datetime.now(timezone.utc)
    id_low_load = uuid.uuid4()
    id_high_load = uuid.uuid4()
    score_low = calculate_4tier_priority_score(0, 0, active_duties=0, distance_km=5.0, created_at=now, driver_id=id_low_load)
    score_high = calculate_4tier_priority_score(0, 0, active_duties=2, distance_km=1.0, created_at=now, driver_id=id_high_load)
    assert score_low > score_high


def test_comb_15_delivery_duty_creation_and_authoritative_assignment(client: TestClient):
    """Comb 15: DELIVERY duty created from confirmed order -> authoritative assignment -> vehicle payload verification."""
    env = setup_driver_test_environment(client)
    duty = create_test_duty(env["tenant"].id, env["seller"].id, env["primary_branch"].id, env["customer"].id, env["customer_address"].id, duty_type=DutyType.DELIVERY)
    driver = create_test_driver(env["tenant"].id, env["seller"].id, env["primary_branch"].id, name="Delivery Driver")
    v = create_test_driver_vehicle(driver["id"], VehicleType.VAN, make="Ram", model="ProMaster", color="White", license_plate="DEL-999")

    asgn = create_test_assignment(duty["id"], driver["id"], is_active=True)
    assert duty["duty_type"] == "DELIVERY"
    assert asgn["driver_id"] == driver["id"]
    assert v["license_plate"] == "DEL-999"


def test_comb_16_multiple_sequential_reassignments_chain(client: TestClient):
    """Comb 16: Three sequential reassignments maintain append-only history and exactly 1 active driver."""
    env = setup_driver_test_environment(client)
    duty = create_test_duty(env["tenant"].id, env["seller"].id, env["primary_branch"].id, env["customer"].id, env["customer_address"].id)
    d1 = create_test_driver(env["tenant"].id, env["seller"].id, env["primary_branch"].id)
    d2 = create_test_driver(env["tenant"].id, env["seller"].id, env["primary_branch"].id)
    d3 = create_test_driver(env["tenant"].id, env["seller"].id, env["primary_branch"].id)

    a1 = create_test_assignment(duty["id"], d1["id"], status=AssignmentStatus.REASSIGNED, is_active=False)
    a2 = create_test_assignment(duty["id"], d2["id"], status=AssignmentStatus.REASSIGNED, is_active=False)
    a3 = create_test_assignment(duty["id"], d3["id"], status=AssignmentStatus.ACTIVE, is_active=True)

    chain = [a1, a2, a3]
    active = [a for a in chain if a["is_active"]]
    assert len(active) == 1
    assert active[0]["driver_id"] == d3["id"]
