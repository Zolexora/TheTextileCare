"""Shared E2E test helpers, factory fixtures, and domain verification harness for TTC Driver Logistics.

Supports testing for:
- Driver Profile, Shift & Vehicle Registration (R1, Q51-Q54)
- Driver Compliance Verification & Eligibility Gates (R1, Q55-Q58, Q77)
- 4-Tier Algorithmic Familiarity & Priority Engine (R1, Q71-Q80)
- Authoritative Duty Assignment & PostgreSQL Row-Locking Concurrency (R1, Q61-Q66)
- Assignment Fallback & Pool Expansion (R1, Q69-Q70)
- Manual Reassignment with Mandatory Reason (R2, Q81-Q82)
- Bifurcated Driver Unavailability (Pre-Duty Auto vs Post-Duty Manual Lockout) (R2, Q83-Q87)
- Immutable Assignment History & Operational Deactivation (R2, Q88-Q90)
- Resilient Multi-Channel Notifications & Customer Payloads with Unmasked Phone (R3, Q91-Q100)
- Tenant & Seller Security Isolation & Payment Decoupling (R4, Q60, Q68, Q99)
"""
from __future__ import annotations

import math
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import text, select

from app.db import SessionLocal
from app.models.customer import Customer, CustomerAddress
from app.models.order import Order, OrderStatus
from app.models.pickup import OrderPickup, PickupStatus
from app.models.seller import Seller, Branch
from app.models.tenant import Tenant
from app.models.user import User
from tests.e2e.conftest import (
    create_test_user,
    create_test_tenant,
    create_test_membership,
    create_test_seller,
    create_test_branch,
    create_test_catalog_hierarchy,
    make_auth_headers,
)


# ============================================================================
# DOMAIN ENUMS (Authoritative definitions from Q51-Q100 / PROJECT.md)
# ============================================================================

class DriverStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ON_LEAVE = "ON_LEAVE"
    SUSPENDED = "SUSPENDED"


class ComplianceDocType(str, Enum):
    DL = "DL"
    RC = "RC"
    INSURANCE = "INSURANCE"
    BGC = "BGC"


class VehicleType(str, Enum):
    BIKE = "BIKE"
    SCOOTER = "SCOOTER"
    VAN = "VAN"
    CAR = "CAR"


class DutyType(str, Enum):
    PICKUP = "PICKUP"
    DELIVERY = "DELIVERY"


class DutyStatus(str, Enum):
    UNASSIGNED = "UNASSIGNED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class AssignmentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REASSIGNED = "REASSIGNED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertType(str, Enum):
    MANUAL_REASSIGNMENT = "MANUAL_REASSIGNMENT"
    PRE_DUTY_REASSIGNMENT = "PRE_DUTY_REASSIGNMENT"
    DUTY_UNASSIGNED_NO_DRIVER = "DUTY_UNASSIGNED_NO_DRIVER"
    POST_DUTY_UNAVAILABLE_EMERGENCY = "POST_DUTY_UNAVAILABLE_EMERGENCY"
    LATE_DUTY_START = "LATE_DUTY_START"


class NotificationChannel(str, Enum):
    PUSH = "PUSH"
    IN_APP = "IN_APP"
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"


class NotificationStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    DELIVERED = "DELIVERED"


# ============================================================================
# AUTHORITATIVE MATHEMATICAL & ALGORITHMIC FORMULAS
# ============================================================================

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two geographic coordinates in kilometers."""
    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return radius_km * c


def calculate_4tier_priority_score(
    address_familiarity: int,
    customer_familiarity: int,
    active_duties: int,
    distance_km: float,
    created_at: datetime,
    driver_id: uuid.UUID,
) -> tuple:
    """Calculate the deterministic 6-element comparison key for driver priority ranking.
    
    Precedence:
    1. Address Familiarity (descending)
    2. Customer Familiarity (descending)
    3. Workload (active duties ascending -> negative for descending sort)
    4. Distance (ascending -> negative for descending sort)
    5. Driver Seniority (registration created_at ascending -> negative timestamp)
    6. Driver ID (UUID ascending -> negative int)
    """
    ts = created_at.timestamp() if isinstance(created_at, datetime) else 0.0
    id_val = int(driver_id) if isinstance(driver_id, uuid.UUID) else 0
    return (
        address_familiarity,
        customer_familiarity,
        -active_duties,
        -round(distance_km, 4),
        -ts,
        -id_val,
    )


def evaluate_driver_eligibility(
    status: str,
    is_on_duty: bool,
    compliance_docs: list[dict[str, Any]],
    active_duties_count: int,
    max_active_duties: int,
    driver_seller_id: uuid.UUID,
    duty_seller_id: uuid.UUID,
    as_of_date: date | None = None,
) -> tuple[bool, list[str]]:
    """Strict binary eligibility gate predicate (Q53, Q56, Q58, Q77)."""
    reasons = []
    as_of = as_of_date or date.today()

    if status != DriverStatus.ACTIVE.value:
        reasons.append(f"Driver status is {status}, expected ACTIVE")

    if not is_on_duty:
        reasons.append("Driver is currently off duty")

    if driver_seller_id != duty_seller_id:
        reasons.append(f"Driver seller {driver_seller_id} does not match duty seller {duty_seller_id}")

    if active_duties_count >= max_active_duties:
        reasons.append(f"Driver active duties ({active_duties_count}) reached capacity ({max_active_duties})")

    # Compliance check across all 4 mandatory documents
    required_docs = {ComplianceDocType.DL.value, ComplianceDocType.RC.value, ComplianceDocType.INSURANCE.value, ComplianceDocType.BGC.value}
    found_docs = set()
    for doc in compliance_docs:
        dtype = doc.get("document_type")
        found_docs.add(dtype)
        if not doc.get("is_verified", False):
            reasons.append(f"Compliance document {dtype} is unverified")
        exp = doc.get("valid_until")
        if isinstance(exp, str):
            exp = date.fromisoformat(exp)
        if exp is not None and exp < as_of:
            reasons.append(f"Compliance document {dtype} expired on {exp}")

    missing_docs = required_docs - found_docs
    if missing_docs:
        reasons.append(f"Missing mandatory compliance documents: {missing_docs}")

    is_eligible = len(reasons) == 0
    return is_eligible, reasons


# ============================================================================
# TEST ENVIRONMENT FACTORY
# ============================================================================

def setup_driver_test_environment(
    client: TestClient,
    tenant_name: str = "Metropolitan Logistics Corp",
    seller_name: str = "TTC FastWash",
    customer_email: str = "customer@example.com",
    seller_admin_email: str = "seller_admin@example.com",
    platform_admin_email: str = "platform_admin@thetextilecare.com",
) -> dict[str, Any]:
    """Create a fully isolated multi-tenant environment with tenant, seller, branches, customer, and addresses."""
    unique_suffix = uuid.uuid4().hex[:6]
    tenant = create_test_tenant(f"{tenant_name} {unique_suffix}")
    seller_user = create_test_user(f"{unique_suffix}_{seller_admin_email}")
    customer_user = create_test_user(f"{unique_suffix}_{customer_email}")
    platform_admin_user = create_test_user(f"{unique_suffix}_{platform_admin_email}")

    create_test_membership(tenant.id, seller_user.id, "SELLER_ADMIN")
    create_test_membership(tenant.id, platform_admin_user.id, "PLATFORM_ADMIN")

    seller_headers = make_auth_headers(seller_user, tenant)
    customer_headers = {"X-User-Id": str(customer_user.id)}
    admin_headers = make_auth_headers(platform_admin_user, tenant)

    seller = create_test_seller(tenant.id, business_name=f"{seller_name} {unique_suffix}")
    primary_branch = create_test_branch(
        tenant.id, seller.id, name=f"Downtown Hub {unique_suffix}", code=f"DT-{unique_suffix.upper()}"
    )
    secondary_branch = create_test_branch(
        tenant.id, seller.id, name=f"Uptown Hub {unique_suffix}", code=f"UP-{unique_suffix.upper()}"
    )

    # Customer and address (Downtown coordinates: lat 40.7128, lon -74.0060)
    with SessionLocal() as db:
        customer = Customer(
            id=uuid.uuid4(),
            user_id=customer_user.id,
            email=customer_user.email,
            phone="+15550192834",
            display_name="Sarah Jenkins",
        )
        db.add(customer)
        db.flush()

        customer_address = CustomerAddress(
            id=uuid.uuid4(),
            customer_id=customer.id,
            label="Apartment",
            address_line_1="742 Evergreen Terrace",
            city="Springfield",
            state="IL",
            postal_code="62704",
            latitude=Decimal("40.7128"),
            longitude=Decimal("-74.0060"),
            is_default=True,
        )
        db.add(customer_address)
        db.commit()

    return {
        "tenant": tenant,
        "seller": seller,
        "primary_branch": primary_branch,
        "secondary_branch": secondary_branch,
        "seller_user": seller_user,
        "customer_user": customer_user,
        "platform_admin_user": platform_admin_user,
        "seller_headers": seller_headers,
        "customer_headers": customer_headers,
        "admin_headers": admin_headers,
        "customer": customer,
        "customer_address": customer_address,
        "unique_suffix": unique_suffix,
    }


# ============================================================================
# DATABASE FACTORY HELPERS (Direct DB population & inspection)
# ============================================================================

def create_test_driver(
    tenant_id: uuid.UUID,
    seller_id: uuid.UUID,
    branch_id: uuid.UUID | None = None,
    name: str = "John Driver",
    phone: str = "+15550199999",
    status: DriverStatus = DriverStatus.ACTIVE,
    is_on_duty: bool = True,
    max_active_duties: int = 3,
    latitude: float = 40.7125,
    longitude: float = -74.0055,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    """Create a driver record with linked user, vehicle, and valid compliance documents."""
    driver_id = uuid.uuid4()
    user_id = uuid.uuid4()
    now = created_at or datetime.now(timezone.utc)
    email = f"driver_{driver_id.hex[:6]}@example.com"

    with SessionLocal() as db:
        # Create driver user
        user = User(
            id=user_id,
            email=email,
            auth_user_id=f"auth-{email}",
            name=name,
        )
        db.add(user)
        db.flush()

        # Insert driver record
        insert_driver_sql = text("""
            INSERT INTO drivers (
                id, user_id, tenant_id, seller_id, branch_id, full_name, phone_number,
                phone, status, is_on_duty, compliance_status, availability_status,
                max_active_duties, current_latitude, current_longitude, created_at, updated_at
            ) VALUES (
                :id, :user_id, :tenant_id, :seller_id, :branch_id, :full_name, :phone_number,
                :phone, :status, :is_on_duty, 'COMPLIANT', 'AVAILABLE',
                :max_active_duties, :latitude, :longitude, :created_at, :updated_at
            )
        """)
        db.execute(
            insert_driver_sql,
            {
                "id": driver_id,
                "user_id": user_id,
                "tenant_id": tenant_id,
                "seller_id": seller_id,
                "branch_id": branch_id,
                "full_name": name,
                "phone_number": phone,
                "phone": phone,
                "status": status.value,
                "is_on_duty": is_on_duty,
                "max_active_duties": max_active_duties,
                "latitude": latitude,
                "longitude": longitude,
                "created_at": now,
                "updated_at": now,
            },
        )
        db.commit()

    return {
        "id": driver_id,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "seller_id": seller_id,
        "branch_id": branch_id,
        "name": name,
        "phone": phone,
        "status": status.value,
        "is_on_duty": is_on_duty,
        "max_active_duties": max_active_duties,
        "latitude": latitude,
        "longitude": longitude,
        "created_at": now,
    }


def create_test_driver_vehicle(
    driver_id: uuid.UUID,
    vehicle_type: VehicleType = VehicleType.VAN,
    make: str = "Ford",
    model: str = "Transit",
    color: str = "White",
    license_plate: str = "TTC-101",
) -> dict[str, Any]:
    """Attach vehicle specifications to driver."""
    vehicle_id = uuid.uuid4()
    with SessionLocal() as db:
        sql = text("""
            INSERT INTO driver_vehicles (
                id, driver_id, vehicle_type, make, model, color, license_plate, created_at, updated_at
            ) VALUES (
                :id, :driver_id, :vehicle_type, :make, :model, :color, :license_plate, NOW(), NOW()
            )
        """)
        try:
            db.execute(
                sql,
                {
                    "id": vehicle_id,
                    "driver_id": driver_id,
                    "vehicle_type": vehicle_type.value,
                    "make": make,
                    "model": model,
                    "color": color,
                    "license_plate": license_plate,
                },
            )
            db.commit()
        except Exception as e:


            db.rollback()

    return {
        "id": vehicle_id,
        "driver_id": driver_id,
        "vehicle_type": vehicle_type.value,
        "make": make,
        "model": model,
        "color": color,
        "license_plate": license_plate,
    }


def create_test_driver_compliance(
    driver_id: uuid.UUID,
    document_type: ComplianceDocType = ComplianceDocType.DL,
    valid_until: date | None = None,
    is_verified: bool = True,
) -> dict[str, Any]:
    """Attach a compliance verification document to driver."""
    doc_id = uuid.uuid4()
    expiry = valid_until or (date.today() + timedelta(days=365))
    with SessionLocal() as db:
        sql = text("""
            INSERT INTO driver_compliance_documents (
                id, driver_id, document_type, document_number, valid_until, is_verified, created_at, updated_at
            ) VALUES (
                :id, :driver_id, :document_type, :doc_num, :valid_until, :is_verified, NOW(), NOW()
            )
        """)
        try:
            db.execute(
                sql,
                {
                    "id": doc_id,
                    "driver_id": driver_id,
                    "document_type": document_type.value,
                    "doc_num": f"DOC-{doc_id.hex[:8].upper()}",
                    "valid_until": expiry,
                    "is_verified": is_verified,
                },
            )
            db.commit()
        except Exception as e:


            db.rollback()

    return {
        "id": doc_id,
        "driver_id": driver_id,
        "document_type": document_type.value,
        "valid_until": expiry,
        "is_verified": is_verified,
    }


def create_test_duty(
    tenant_id: uuid.UUID,
    seller_id: uuid.UUID,
    branch_id: uuid.UUID,
    customer_id: uuid.UUID,
    address_id: uuid.UUID,
    duty_type: DutyType = DutyType.PICKUP,
    status: DutyStatus = DutyStatus.UNASSIGNED,
    scheduled_start: datetime | None = None,
    scheduled_end: datetime | None = None,
    order_id: uuid.UUID | None = None,
    destination_latitude: float = 40.7128,
    destination_longitude: float = -74.0060,
) -> dict[str, Any]:
    """Create a logistics duty record."""
    duty_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    start_time = scheduled_start or (now + timedelta(hours=1))
    end_time = scheduled_end or (start_time + timedelta(hours=2))

    with SessionLocal() as db:
        sql = text("""
            INSERT INTO driver_duties (
                id, tenant_id, seller_id, branch_id, customer_id, destination_address_id,
                order_id, duty_type, status, scheduled_window_start, scheduled_window_end,
                destination_latitude, destination_longitude, created_at, updated_at
            ) VALUES (
                :id, :tenant_id, :seller_id, :branch_id, :customer_id, :dest_addr,
                :order_id, :duty_type, :status, :start_time, :end_time,
                :lat, :lon, NOW(), NOW()
            )
        """)
        try:
            db.execute(
                sql,
                {
                    "id": duty_id,
                    "tenant_id": tenant_id,
                    "seller_id": seller_id,
                    "branch_id": branch_id,
                    "customer_id": customer_id,
                    "dest_addr": address_id,
                    "order_id": order_id,
        "order_id": order_id,
                    "duty_type": duty_type.value,
                    "status": status.value,
                    "start_time": start_time,
                    "end_time": end_time,
                    "lat": destination_latitude,
                    "lon": destination_longitude,
                },
            )
            db.commit()
        except Exception as e:


            db.rollback()

    return {
        "id": duty_id,
        "tenant_id": tenant_id,
        "seller_id": seller_id,
        "branch_id": branch_id,
        "customer_id": customer_id,
        "address_id": address_id,
        "order_id": order_id,
        "duty_type": duty_type.value,
        "status": status.value,
        "scheduled_window_start": start_time,
        "scheduled_window_end": end_time,
        "latitude": destination_latitude,
        "longitude": destination_longitude,
    }


def create_test_assignment(
    duty_id: uuid.UUID,
    driver_id: uuid.UUID,
    status: AssignmentStatus = AssignmentStatus.ACTIVE,
    is_active: bool = True,
    actor_user_id: uuid.UUID | None = None,
    reassignment_reason: str | None = None,
    assigned_at: datetime | None = None,
    unassigned_at: datetime | None = None,
) -> dict[str, Any]:
    """Create an assignment record representing driver-duty linkage."""
    assignment_id = uuid.uuid4()
    now = assigned_at or datetime.now(timezone.utc)
    with SessionLocal() as db:
        sql = text("""
            INSERT INTO driver_assignments (
                id, duty_id, driver_id, status, is_active, actor_user_id,
                reassignment_reason, assigned_at, unassigned_at, created_at, updated_at
            ) VALUES (
                :id, :duty_id, :driver_id, :status, :is_active, :actor_id,
                :reason, :assigned_at, :unassigned_at, NOW(), NOW()
            )
        """)
        try:
            db.execute(
                sql,
                {
                    "id": assignment_id,
                    "duty_id": duty_id,
                    "driver_id": driver_id,
                    "status": status.value,
                    "is_active": is_active,
                    "actor_id": actor_user_id,
                    "reason": reassignment_reason,
                    "assigned_at": now,
                    "unassigned_at": unassigned_at,
                },
            )
            db.commit()
        except Exception as e:


            db.rollback()

    return {
        "id": assignment_id,
        "duty_id": duty_id,
        "driver_id": driver_id,
        "status": status.value,
        "is_active": is_active,
        "actor_user_id": actor_user_id,
        "reassignment_reason": reassignment_reason,
        "assigned_at": now,
        "unassigned_at": unassigned_at,
    }


def simulate_completed_duty_history(
    tenant_id: uuid.UUID,
    seller_id: uuid.UUID,
    branch_id: uuid.UUID,
    driver_id: uuid.UUID,
    customer_id: uuid.UUID,
    address_id: uuid.UUID,
    count: int = 1,
) -> list[uuid.UUID]:
    """Seed historical completed duties for driver familiarity scoring."""
    created_duty_ids = []
    with SessionLocal() as db:
        for _ in range(count):
            duty_id = uuid.uuid4()
            past_time = datetime.now(timezone.utc) - timedelta(days=7)
            try:
                db.execute(
                    text("""
                        INSERT INTO driver_duties (
                            id, tenant_id, seller_id, branch_id, customer_id, destination_address_id,
                            duty_type, status, scheduled_window_start, scheduled_window_end,
                            completed_at, created_at, updated_at
                        ) VALUES (
                            :id, :tenant_id, :seller_id, :branch_id, :cust_id, :addr_id,
                            'PICKUP', 'COMPLETED', :st, :et, :ct, NOW(), NOW()
                        )
                    """),
                    {
                        "id": duty_id,
                        "tenant_id": tenant_id,
                        "seller_id": seller_id,
                        "branch_id": branch_id,
                        "cust_id": customer_id,
                        "addr_id": address_id,
                        "st": past_time,
                        "et": past_time + timedelta(hours=2),
                        "ct": past_time + timedelta(hours=1),
                    },
                )
                db.execute(
                    text("""
                        INSERT INTO driver_assignments (
                            id, duty_id, driver_id, status, is_active, assigned_at, unassigned_at, created_at, updated_at
                        ) VALUES (
                            :asgn_id, :duty_id, :driver_id, 'COMPLETED', FALSE, :at, :uat, NOW(), NOW()
                        )
                    """),
                    {
                        "asgn_id": uuid.uuid4(),
                        "duty_id": duty_id,
                        "driver_id": driver_id,
                        "at": past_time,
                        "uat": past_time + timedelta(hours=1),
                    },
                )
                created_duty_ids.append(duty_id)
            except Exception as e:


                db.rollback()
                break
        db.commit()
    return created_duty_ids


# ============================================================================
# API CALL HELPERS (Opaque-box REST client wrappers)
# ============================================================================

def api_create_driver(
    client: TestClient,
    env: dict[str, Any],
    name: str = "Carlos Driver",
    phone: str = "+15550198888",
    max_active_duties: int = 3,
    vehicle_type: str = "VAN",
    make: str = "Toyota",
    model: str = "Sienna",
    color: str = "Silver",
    license_plate: str = "DRV-8888",
    branch_id: uuid.UUID | None = None,
) -> tuple[int, dict[str, Any]]:
    """POST /api/v1/seller/drivers - Onboard a driver with vehicle."""
    payload = {
        "name": name,
        "phone": phone,
        "max_active_duties": max_active_duties,
        "branch_id": str(branch_id or env["primary_branch"].id),
        "vehicle": {
            "vehicle_type": vehicle_type,
            "make": make,
            "model": model,
            "color": color,
            "license_plate": license_plate,
        },
    }
    resp = client.post("/api/v1/seller/drivers", json=payload, headers=env["seller_headers"])
    data = resp.json() if resp.status_code < 500 else {}
    return resp.status_code, data


def api_list_drivers(
    client: TestClient,
    env: dict[str, Any],
    params: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    """GET /api/v1/seller/drivers - List drivers."""
    resp = client.get("/api/v1/seller/drivers", params=params or {}, headers=env["seller_headers"])
    data = resp.json() if resp.status_code < 500 else {}
    return resp.status_code, data


def api_get_driver(
    client: TestClient,
    env: dict[str, Any],
    driver_id: uuid.UUID | str,
) -> tuple[int, dict[str, Any]]:
    """GET /api/v1/seller/drivers/{driver_id} - Get driver details."""
    resp = client.get(f"/api/v1/seller/drivers/{driver_id}", headers=env["seller_headers"])
    data = resp.json() if resp.status_code < 500 else {}
    return resp.status_code, data


def api_update_driver_shift(
    client: TestClient,
    env: dict[str, Any],
    driver_id: uuid.UUID | str,
    is_on_duty: bool,
) -> tuple[int, dict[str, Any]]:
    """PUT /api/v1/seller/drivers/{driver_id}/shift - Toggle driver shift status."""
    resp = client.put(
        f"/api/v1/seller/drivers/{driver_id}/shift",
        json={"is_on_duty": is_on_duty},
        headers=env["seller_headers"],
    )
    data = resp.json() if resp.status_code < 500 else {}
    return resp.status_code, data


def api_upload_compliance(
    client: TestClient,
    env: dict[str, Any],
    driver_id: uuid.UUID | str,
    document_type: str,
    valid_until: str,
    is_verified: bool = True,
) -> tuple[int, dict[str, Any]]:
    """POST /api/v1/seller/drivers/{driver_id}/compliance - Upload or update compliance document."""
    payload = {
        "document_type": document_type,
        "valid_until": valid_until,
        "is_verified": is_verified,
    }
    resp = client.post(
        f"/api/v1/seller/drivers/{driver_id}/compliance",
        json=payload,
        headers=env["seller_headers"],
    )
    data = resp.json() if resp.status_code < 500 else {}
    return resp.status_code, data


def api_create_duty(
    client: TestClient,
    env: dict[str, Any],
    duty_type: str = "PICKUP",
    order_id: uuid.UUID | str | None = None,
    customer_id: uuid.UUID | str | None = None,
    address_id: uuid.UUID | str | None = None,
    branch_id: uuid.UUID | str | None = None,
    scheduled_start: str | None = None,
    scheduled_end: str | None = None,
) -> tuple[int, dict[str, Any]]:
    """POST /api/v1/seller/duties - Create logistics duty."""
    now = datetime.now(timezone.utc)
    st = scheduled_start or (now + timedelta(hours=1)).isoformat()
    et = scheduled_end or (now + timedelta(hours=3)).isoformat()
    payload = {
        "duty_type": duty_type,
        "order_id": str(order_id) if order_id else None,
        "customer_id": str(customer_id or env["customer"].id),
        "destination_address_id": str(address_id or env["customer_address"].id),
        "branch_id": str(branch_id or env["primary_branch"].id),
        "scheduled_window_start": st,
        "scheduled_window_end": et,
    }
    resp = client.post("/api/v1/seller/duties", json=payload, headers=env["seller_headers"])
    data = resp.json() if resp.status_code < 500 else {}
    return resp.status_code, data


def api_get_duty(
    client: TestClient,
    env: dict[str, Any],
    duty_id: uuid.UUID | str,
) -> tuple[int, dict[str, Any]]:
    """GET /api/v1/seller/duties/{duty_id} - Query duty status and active assignment."""
    resp = client.get(f"/api/v1/seller/duties/{duty_id}", headers=env["seller_headers"])
    data = resp.json() if resp.status_code < 500 else {}
    return resp.status_code, data


def api_list_duties(
    client: TestClient,
    env: dict[str, Any],
    params: dict[str, Any] | None = None,
) -> tuple[int, Any]:
    """GET /api/v1/seller/duties - List duties."""
    resp = client.get("/api/v1/seller/duties", params=params or {}, headers=env["seller_headers"])
    data = resp.json() if resp.status_code < 500 else {}
    return resp.status_code, data


def api_assign_driver(
    client: TestClient,
    env: dict[str, Any],
    duty_id: uuid.UUID | str,
    driver_id: uuid.UUID | str | None = None,
    notes: str | None = None,
) -> tuple[int, dict[str, Any]]:
    """POST /api/v1/seller/duties/{duty_id}/assign - Authoritative duty assignment."""
    payload: dict[str, Any] = {}
    if driver_id:
        payload["driver_id"] = str(driver_id)
    if notes:
        payload["notes"] = notes
    resp = client.post(
        f"/api/v1/seller/duties/{duty_id}/assign",
        json=payload,
        headers=env["seller_headers"],
    )
    data = resp.json() if resp.status_code < 500 else {}
    return resp.status_code, data


def api_reassign_driver(
    client: TestClient,
    env: dict[str, Any],
    duty_id: uuid.UUID | str,
    new_driver_id: uuid.UUID | str,
    reason: str,
) -> tuple[int, dict[str, Any]]:
    """POST /api/v1/seller/duties/{duty_id}/reassign - Manual reassignment with mandatory reason."""
    payload = {
        "new_driver_id": str(new_driver_id) if new_driver_id else None,
        "reason": reason,
    }
    resp = client.post(
        f"/api/v1/seller/duties/{duty_id}/reassign",
        json=payload,
        headers=env["seller_headers"],
    )
    data = resp.json() if resp.status_code < 500 else {}
    return resp.status_code, data


def api_report_unavailability(
    client: TestClient,
    env: dict[str, Any],
    duty_id: uuid.UUID | str,
    reason: str = "Vehicle mechanical issue",
) -> tuple[int, dict[str, Any]]:
    """POST /api/v1/seller/duties/{duty_id}/unavailability - Report driver unavailable."""
    payload = {"reason": reason}
    resp = client.post(
        f"/api/v1/seller/duties/{duty_id}/unavailability",
        json=payload,
        headers=env["seller_headers"],
    )
    data = resp.json() if resp.status_code < 500 else {}
    return resp.status_code, data


def api_start_duty(
    client: TestClient,
    env: dict[str, Any],
    duty_id: uuid.UUID | str,
) -> tuple[int, dict[str, Any]]:
    """POST /api/v1/seller/duties/{duty_id}/start - Start duty progress."""
    resp = client.post(
        f"/api/v1/seller/duties/{duty_id}/start",
        json={},
        headers=env["seller_headers"],
    )
    data = resp.json() if resp.status_code < 500 else {}
    return resp.status_code, data


def api_complete_duty(
    client: TestClient,
    env: dict[str, Any],
    duty_id: uuid.UUID | str,
) -> tuple[int, dict[str, Any]]:
    """POST /api/v1/seller/duties/{duty_id}/complete - Complete duty fulfillment."""
    resp = client.post(
        f"/api/v1/seller/duties/{duty_id}/complete",
        json={},
        headers=env["seller_headers"],
    )
    data = resp.json() if resp.status_code < 500 else {}
    return resp.status_code, data


def api_get_alerts(
    client: TestClient,
    env: dict[str, Any],
    severity: str | None = None,
) -> tuple[int, Any]:
    """GET /api/v1/seller/alerts - Query operations alerts."""
    params = {}
    if severity:
        params["severity"] = severity
    resp = client.get("/api/v1/seller/alerts", params=params, headers=env["seller_headers"])
    data = resp.json() if resp.status_code < 500 else {}
    return resp.status_code, data


def api_get_notification_logs(
    client: TestClient,
    env: dict[str, Any],
    duty_id: uuid.UUID | str | None = None,
) -> tuple[int, Any]:
    """GET /api/v1/notifications/logs - Query notification dispatch records."""
    params = {}
    if duty_id:
        params["duty_id"] = str(duty_id)
    resp = client.get("/api/v1/notifications/logs", params=params, headers=env["seller_headers"])
    data = resp.json() if resp.status_code < 500 else {}
    return resp.status_code, data


def api_retry_notifications(
    client: TestClient,
    env: dict[str, Any],
    notification_id: uuid.UUID | str | None = None,
) -> tuple[int, dict[str, Any]]:
    """POST /api/v1/notifications/retry - Trigger retry of failed notifications."""
    payload = {}
    if notification_id:
        payload["notification_id"] = str(notification_id)
    resp = client.post("/api/v1/notifications/retry", json=payload, headers=env["seller_headers"])
    data = resp.json() if resp.status_code < 500 else {}
    return resp.status_code, data


def api_get_notification_configs(
    client: TestClient,
    env: dict[str, Any],
) -> tuple[int, Any]:
    """GET /api/v1/notifications/configs - Query notification channel routing configs."""
    resp = client.get("/api/v1/notifications/configs", headers=env["seller_headers"])
    data = resp.json() if resp.status_code < 500 else {}
    return resp.status_code, data


def api_update_notification_configs(
    client: TestClient,
    env: dict[str, Any],
    configs: list[dict[str, Any]] | dict[str, Any],
) -> tuple[int, Any]:
    """PUT /api/v1/notifications/configs - Update notification channel routing preferences."""
    resp = client.put("/api/v1/notifications/configs", json=configs, headers=env["seller_headers"])
    data = resp.json() if resp.status_code < 500 else {}
    return resp.status_code, data


# ============================================================================
# DB VERIFICATION HELPERS (Opaque inspection of database rows)
# ============================================================================

def db_query_duty(duty_id: uuid.UUID) -> dict[str, Any] | None:
    """Fetch duty row from DB."""
    with SessionLocal() as db:
        try:
            res = db.execute(
                text("SELECT * FROM driver_duties WHERE id = :id"),
                {"id": duty_id},
            ).mappings().first()
            return dict(res) if res else None
        except Exception as e:


            db.rollback()
            return None


def db_query_assignments(duty_id: uuid.UUID) -> list[dict[str, Any]]:
    """Fetch all assignments for a duty from DB ordered by assigned_at."""
    with SessionLocal() as db:
        try:
            res = db.execute(
                text("SELECT * FROM driver_assignments WHERE duty_id = :id ORDER BY assigned_at ASC"),
                {"id": duty_id},
            ).mappings().all()
            return [dict(r) for r in res]
        except Exception as e:


            db.rollback()
            return []


def db_query_active_assignment(duty_id: uuid.UUID) -> dict[str, Any] | None:
    """Fetch the single active assignment for a duty."""
    with SessionLocal() as db:
        try:
            res = db.execute(
                text("SELECT * FROM driver_assignments WHERE duty_id = :id AND is_active = TRUE"),
                {"id": duty_id},
            ).mappings().first()
            return dict(res) if res else None
        except Exception as e:


            db.rollback()
            return None


def db_query_alerts(seller_id: uuid.UUID | None = None) -> list[dict[str, Any]]:
    """Fetch operations alerts from DB."""
    with SessionLocal() as db:
        try:
            if seller_id:
                res = db.execute(
                    text("SELECT * FROM operations_alerts WHERE seller_id = :sid ORDER BY created_at DESC"),
                    {"sid": seller_id},
                ).mappings().all()
            else:
                res = db.execute(
                    text("SELECT * FROM operations_alerts ORDER BY created_at DESC"),
                ).mappings().all()
            return [dict(r) for r in res]
        except Exception as e:


            db.rollback()
            return []


def db_query_notifications(duty_id: uuid.UUID | None = None) -> list[dict[str, Any]]:
    """Fetch notification logs from DB."""
    with SessionLocal() as db:
        try:
            if duty_id:
                res = db.execute(
                    text("SELECT * FROM notification_logs WHERE duty_id = :did ORDER BY created_at DESC"),
                    {"did": duty_id},
                ).mappings().all()
            else:
                res = db.execute(
                    text("SELECT * FROM notification_logs ORDER BY created_at DESC"),
                ).mappings().all()
            return [dict(r) for r in res]
        except Exception as e:


            db.rollback()
            return []

