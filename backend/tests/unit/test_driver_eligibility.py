"""Unit tests for DriverEligibilityService (Milestone 1).

Validates strict binary eligibility gates:
1. Active status
2. On-duty shift & availability
3. Seller / tenant authorization
4. 4-way compliance document validity (DL, RC, INSURANCE, BGC)
5. Workload capacity threshold (active_duties < max_active_duties)
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
import pytest

from app.db import SessionLocal
from app.models.driver import (
    Driver,
    DriverAvailabilityStatus,
    DriverComplianceDocument,
    DriverSellerAuthorization,
    DriverStatus,
)
from app.services.driver import DriverEligibilityService
from tests.conftest import (
    create_test_branch,
    create_test_driver,
    create_test_driver_authorization,
    create_test_driver_compliance,
    create_test_seller,
    create_test_tenant,
)


def test_active_compliant_available_driver_is_eligible():
    """Verify driver with ACTIVE status, on duty, valid compliance, and available capacity is eligible."""
    tenant = create_test_tenant("Tenant A")
    seller = create_test_seller(tenant.id)
    branch = create_test_branch(tenant.id, seller.id)

    driver = create_test_driver(
        tenant_id=tenant.id,
        seller_id=seller.id,
        home_branch_id=branch.id,
        status=DriverStatus.ACTIVE.value,
        is_on_duty=True,
        availability_status=DriverAvailabilityStatus.AVAILABLE.value,
        max_active_duties=3,
    )
    for doc in ["DL", "RC", "INSURANCE", "BGC"]:
        create_test_driver_compliance(driver.id, doc_type=doc, is_verified=True, days_valid=180)

    with SessionLocal() as db:
        svc = DriverEligibilityService(db)
        result = svc.evaluate_eligibility(driver.id, seller_id=seller.id, branch_id=branch.id)

        assert result.is_eligible is True
        assert len(result.reasons) == 0
        assert result.active_duties_count == 0
        assert result.max_active_duties == 3


def test_inactive_driver_disqualified():
    """Verify driver with status != ACTIVE is disqualified."""
    tenant = create_test_tenant("Tenant B")
    seller = create_test_seller(tenant.id)
    branch = create_test_branch(tenant.id, seller.id)

    driver = create_test_driver(
        tenant_id=tenant.id,
        seller_id=seller.id,
        status=DriverStatus.INACTIVE.value,
        is_on_duty=True,
        availability_status=DriverAvailabilityStatus.AVAILABLE.value,
    )
    for doc in ["DL", "RC", "INSURANCE", "BGC"]:
        create_test_driver_compliance(driver.id, doc_type=doc, is_verified=True, days_valid=180)

    with SessionLocal() as db:
        svc = DriverEligibilityService(db)
        result = svc.evaluate_eligibility(driver.id, seller_id=seller.id, branch_id=branch.id)

        assert result.is_eligible is False
        assert any("status" in r.lower() or "inactive" in r.lower() for r in result.reasons)


def test_offline_or_unavailable_driver_disqualified():
    """Verify driver who is OFFLINE or BUSY is disqualified."""
    tenant = create_test_tenant("Tenant C")
    seller = create_test_seller(tenant.id)

    driver = create_test_driver(
        tenant_id=tenant.id,
        seller_id=seller.id,
        status=DriverStatus.ACTIVE.value,
        is_on_duty=True,
        availability_status=DriverAvailabilityStatus.OFFLINE.value,
    )
    for doc in ["DL", "RC", "INSURANCE", "BGC"]:
        create_test_driver_compliance(driver.id, doc_type=doc, is_verified=True, days_valid=180)

    with SessionLocal() as db:
        svc = DriverEligibilityService(db)
        result = svc.evaluate_eligibility(driver.id, seller_id=seller.id)

        assert result.is_eligible is False
        assert any("offline" in r.lower() or "availability" in r.lower() for r in result.reasons)


def test_off_duty_driver_disqualified():
    """Verify driver who is off-duty (is_on_duty=False) is disqualified."""
    tenant = create_test_tenant("Tenant D")
    seller = create_test_seller(tenant.id)

    driver = create_test_driver(
        tenant_id=tenant.id,
        seller_id=seller.id,
        status=DriverStatus.ACTIVE.value,
        is_on_duty=False,
        availability_status=DriverAvailabilityStatus.AVAILABLE.value,
    )
    for doc in ["DL", "RC", "INSURANCE", "BGC"]:
        create_test_driver_compliance(driver.id, doc_type=doc, is_verified=True, days_valid=180)

    with SessionLocal() as db:
        svc = DriverEligibilityService(db)
        result = svc.evaluate_eligibility(driver.id, seller_id=seller.id)

        assert result.is_eligible is False
        assert any("off-duty" in r.lower() for r in result.reasons)


def test_unauthorized_seller_disqualified():
    """Verify driver without authorization for the requested seller is disqualified."""
    tenant = create_test_tenant("Tenant E")
    seller_a = create_test_seller(tenant.id, business_name="Seller Organization A")
    seller_b = create_test_seller(tenant.id, business_name="Seller Organization B")

    driver = create_test_driver(
        tenant_id=tenant.id,
        seller_id=seller_a.id,
        status=DriverStatus.ACTIVE.value,
        is_on_duty=True,
        availability_status=DriverAvailabilityStatus.AVAILABLE.value,
    )
    for doc in ["DL", "RC", "INSURANCE", "BGC"]:
        create_test_driver_compliance(driver.id, doc_type=doc, is_verified=True, days_valid=180)

    with SessionLocal() as db:
        svc = DriverEligibilityService(db)
        # Attempt to evaluate for seller_b
        result = svc.evaluate_eligibility(driver.id, seller_id=seller_b.id)

        assert result.is_eligible is False
        assert any("unauthorized" in r.lower() or "not authorized" in r.lower() for r in result.reasons)


def test_authorized_shared_platform_driver_is_eligible():
    """Verify shared platform driver (seller_id=None) with seller authorization is eligible."""
    tenant = create_test_tenant("Tenant F")
    seller = create_test_seller(tenant.id)

    # Shared pool driver (seller_id is None)
    driver = create_test_driver(
        tenant_id=tenant.id,
        seller_id=None,
        status=DriverStatus.ACTIVE.value,
        is_on_duty=True,
        availability_status=DriverAvailabilityStatus.AVAILABLE.value,
    )
    for doc in ["DL", "RC", "INSURANCE", "BGC"]:
        create_test_driver_compliance(driver.id, doc_type=doc, is_verified=True, days_valid=180)

    # Grant explicit authorization for seller
    create_test_driver_authorization(
        driver_id=driver.id,
        tenant_id=tenant.id,
        seller_id=seller.id,
        is_authorized=True,
    )

    with SessionLocal() as db:
        svc = DriverEligibilityService(db)
        result = svc.evaluate_eligibility(driver.id, seller_id=seller.id)

        assert result.is_eligible is True
        assert len(result.reasons) == 0


def test_missing_required_document_disqualified():
    """Verify driver missing any mandatory document (e.g. BGC) is disqualified."""
    tenant = create_test_tenant("Tenant G")
    seller = create_test_seller(tenant.id)

    driver = create_test_driver(tenant_id=tenant.id, seller_id=seller.id, is_on_duty=True)
    # Only create DL, RC, INSURANCE - miss BGC
    create_test_driver_compliance(driver.id, doc_type="DL", is_verified=True, days_valid=100)
    create_test_driver_compliance(driver.id, doc_type="RC", is_verified=True, days_valid=100)
    create_test_driver_compliance(driver.id, doc_type="INSURANCE", is_verified=True, days_valid=100)

    with SessionLocal() as db:
        svc = DriverEligibilityService(db)
        result = svc.evaluate_eligibility(driver.id, seller_id=seller.id)

        assert result.is_eligible is False
        assert any("bgc" in r.lower() and "missing" in r.lower() for r in result.reasons)


def test_unverified_document_disqualified():
    """Verify driver with an unverified compliance document is disqualified."""
    tenant = create_test_tenant("Tenant H")
    seller = create_test_seller(tenant.id)

    driver = create_test_driver(tenant_id=tenant.id, seller_id=seller.id, is_on_duty=True)
    create_test_driver_compliance(driver.id, doc_type="DL", is_verified=True, days_valid=100)
    create_test_driver_compliance(driver.id, doc_type="RC", is_verified=True, days_valid=100)
    create_test_driver_compliance(driver.id, doc_type="INSURANCE", is_verified=True, days_valid=100)
    create_test_driver_compliance(driver.id, doc_type="BGC", is_verified=False, days_valid=100)  # Unverified!

    with SessionLocal() as db:
        svc = DriverEligibilityService(db)
        result = svc.evaluate_eligibility(driver.id, seller_id=seller.id)

        assert result.is_eligible is False
        assert any("bgc" in r.lower() and "unverified" in r.lower() for r in result.reasons)


def test_expired_document_boundary():
    """Verify document expired yesterday is rejected, and document expiring today is valid (inclusive)."""
    tenant = create_test_tenant("Tenant I")
    seller = create_test_seller(tenant.id)
    today = date.today()

    # Driver with expired insurance (yesterday)
    driver_expired = create_test_driver(tenant_id=tenant.id, seller_id=seller.id, is_on_duty=True)
    create_test_driver_compliance(driver_expired.id, doc_type="DL", is_verified=True, days_valid=100)
    create_test_driver_compliance(driver_expired.id, doc_type="RC", is_verified=True, days_valid=100)
    create_test_driver_compliance(driver_expired.id, doc_type="BGC", is_verified=True, days_valid=100)
    create_test_driver_compliance(
        driver_expired.id,
        doc_type="INSURANCE",
        is_verified=True,
        valid_until=today - timedelta(days=1),
    )

    with SessionLocal() as db:
        svc = DriverEligibilityService(db)
        res_expired = svc.evaluate_eligibility(driver_expired.id, seller_id=seller.id)
        assert res_expired.is_eligible is False
        assert any("insurance" in r.lower() and "expired" in r.lower() for r in res_expired.reasons)

    # Driver with document expiring today (boundary: inclusive)
    driver_today = create_test_driver(tenant_id=tenant.id, seller_id=seller.id, is_on_duty=True)
    create_test_driver_compliance(driver_today.id, doc_type="DL", is_verified=True, days_valid=100)
    create_test_driver_compliance(driver_today.id, doc_type="RC", is_verified=True, days_valid=100)
    create_test_driver_compliance(driver_today.id, doc_type="BGC", is_verified=True, days_valid=100)
    create_test_driver_compliance(
        driver_today.id,
        doc_type="INSURANCE",
        is_verified=True,
        valid_until=today,
    )

    with SessionLocal() as db:
        svc = DriverEligibilityService(db)
        res_today = svc.evaluate_eligibility(driver_today.id, seller_id=seller.id)
        assert res_today.is_eligible is True


def test_workload_capacity_boundary():
    """Verify driver at or exceeding max_active_duties is rejected."""
    tenant = create_test_tenant("Tenant J")
    seller = create_test_seller(tenant.id)

    driver = create_test_driver(
        tenant_id=tenant.id,
        seller_id=seller.id,
        is_on_duty=True,
        max_active_duties=3,
    )
    for doc in ["DL", "RC", "INSURANCE", "BGC"]:
        create_test_driver_compliance(driver.id, doc_type=doc, is_verified=True, days_valid=180)

    with SessionLocal() as db:
        svc = DriverEligibilityService(db)

        # Case 1: active duties = 2, max = 3 -> ELIGIBLE
        res_ok = svc.evaluate_driver(driver, seller_id=seller.id, active_duties_count=2)
        assert res_ok.is_eligible is True

        # Case 2: active duties = 3, max = 3 -> INELIGIBLE (at capacity)
        res_full = svc.evaluate_driver(driver, seller_id=seller.id, active_duties_count=3)
        assert res_full.is_eligible is False
        assert any("capacity" in r.lower() for r in res_full.reasons)

        # Case 3: active duties = 4, max = 3 -> INELIGIBLE
        res_over = svc.evaluate_driver(driver, seller_id=seller.id, active_duties_count=4)
        assert res_over.is_eligible is False
