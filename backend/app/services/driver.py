"""Phase 8 — Driver Management & Eligibility Evaluation Services.

Features 4 & 6:
- Driver onboarding, profile management, vehicle management
- Shift status and availability toggling
- Compliance document verification
- 5-Gate strict binary driver eligibility evaluation
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import ApiError
from app.models.driver import (
    ComplianceDocumentType,
    Driver,
    DriverAvailabilityStatus,
    DriverComplianceDocument,
    DriverComplianceStatus,
    DriverSellerAuthorization,
    DriverStatus,
    DriverVehicle,
    REQUIRED_COMPLIANCE_DOCUMENTS,
)
from app.models.seller import Branch, Seller
from app.models.user import User
from app.schemas.driver import (
    DriverComplianceCreate,
    DriverCreate,
    DriverOnboardRequest,
    DriverVehicleCreate,
    EligibilityEvaluationResult,
)


class DriverEligibilityService:
    """Evaluates strict binary eligibility for driver dispatch candidates (R1, Q53, Q56, Q58, Q77)."""

    MANDATORY_DOCUMENTS = frozenset(REQUIRED_COMPLIANCE_DOCUMENTS)

    def __init__(self, db: Session) -> None:
        self.db = db

    def evaluate_driver(
        self,
        driver: Driver,
        seller_id: uuid.UUID,
        branch_id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        as_of_date: date | None = None,
        active_duties_count: int | None = None,
        required_capacity: int = 1,
    ) -> EligibilityEvaluationResult:
        """Evaluate a single driver against all 5 binary eligibility gates."""
        reasons: list[str] = []
        check_date = as_of_date or datetime.now(timezone.utc).date()

        # Gate 1: Operational Status
        if driver.status != DriverStatus.ACTIVE.value:
            reasons.append(
                f"Driver status is '{driver.status}'; must be '{DriverStatus.ACTIVE.value}' (inactive)."
            )

        # Gate 2: Shift State & Operational Availability
        if not getattr(driver, "is_on_duty", True):
            reasons.append("Driver is currently off-duty.")

        if getattr(driver, "availability_status", "AVAILABLE") != DriverAvailabilityStatus.AVAILABLE.value:
            reasons.append(
                f"Driver availability is '{driver.availability_status}'; must be '{DriverAvailabilityStatus.AVAILABLE.value}' (offline/busy)."
            )

        # Gate 3: Tenant / Seller Authorization
        is_authorized = False
        if driver.seller_id is not None and driver.seller_id == seller_id:
            # Check branch match if branch-scoped and driver is branch-anchored
            effective_branch = driver.home_branch_id or driver.branch_id
            if branch_id is None or effective_branch is None or effective_branch == branch_id:
                is_authorized = True
        else:
            # Check authorizations list (either pre-loaded in __dict__ or queried from db)
            if "authorizations" in driver.__dict__ and driver.__dict__["authorizations"] is not None:
                auth_list = driver.__dict__["authorizations"]
            else:
                auth_list = self.db.scalars(
                    select(DriverSellerAuthorization).where(
                        DriverSellerAuthorization.driver_id == driver.id
                    )
                ).all()

            for auth in auth_list:
                if auth.seller_id == seller_id and auth.is_authorized:
                    if auth.branch_id is None or branch_id is None or auth.branch_id == branch_id:
                        is_authorized = True
                        break

        if not is_authorized:
            reasons.append(f"Driver is not authorized to service seller '{seller_id}' (unauthorized).")

        # Gate 4: 4-Way Compliance Document Validity
        docs_by_type: dict[str, DriverComplianceDocument] = {}
        if "compliance_documents" in driver.__dict__ and driver.__dict__["compliance_documents"] is not None:
            loaded_docs = driver.__dict__["compliance_documents"]
        else:
            doc_stmt = select(DriverComplianceDocument).where(
                DriverComplianceDocument.driver_id == driver.id
            )
            loaded_docs = self.db.scalars(doc_stmt).all()

        for doc in loaded_docs:
            docs_by_type[doc.document_type] = doc

        for required_type in sorted(self.MANDATORY_DOCUMENTS):
            doc = docs_by_type.get(required_type)
            if doc is None:
                reasons.append(f"Missing required compliance document: '{required_type}'.")
                continue
            if not doc.is_verified:
                reasons.append(f"Compliance document '{required_type}' is not verified (unverified).")
            if doc.valid_until is not None:
                valid_date = (
                    doc.valid_until.date()
                    if isinstance(doc.valid_until, datetime)
                    else doc.valid_until
                )
                if valid_date < check_date:
                    reasons.append(
                        f"Compliance document '{required_type}' expired on {valid_date.isoformat()} (current: {check_date.isoformat()})."
                    )

        # Gate 5: Active Workload Capacity
        if active_duties_count is None:
            active_duties_count = self._get_active_duties_count(driver.id)

        if active_duties_count + required_capacity - 1 >= driver.max_active_duties or active_duties_count >= driver.max_active_duties:
            reasons.append(
                f"Driver active duties count ({active_duties_count}) reaches or exceeds capacity limit ({driver.max_active_duties})."
            )

        is_eligible = len(reasons) == 0
        return EligibilityEvaluationResult(
            is_eligible=is_eligible,
            driver_id=driver.id,
            reasons=reasons,
            active_duties_count=active_duties_count,
            max_active_duties=driver.max_active_duties,
        )

    def evaluate_eligibility(
        self,
        driver_id: uuid.UUID,
        seller_id: uuid.UUID,
        branch_id: uuid.UUID | None = None,
        required_capacity: int = 1,
        as_of_date: date | None = None,
    ) -> EligibilityEvaluationResult:
        """Lookup driver and evaluate eligibility by ID (convenience method)."""
        stmt = (
            select(Driver)
            .options(
                joinedload(Driver.compliance_documents),
                joinedload(Driver.authorizations),
                joinedload(Driver.home_branch),
            )
            .where(Driver.id == driver_id)
        )
        driver = self.db.execute(stmt).unique().scalar_one_or_none()
        if not driver:
            return EligibilityEvaluationResult(
                is_eligible=False,
                driver_id=driver_id,
                reasons=["Driver not found."],
                active_duties_count=0,
                max_active_duties=0,
            )

        return self.evaluate_driver(
            driver=driver,
            seller_id=seller_id,
            branch_id=branch_id,
            as_of_date=as_of_date,
            required_capacity=required_capacity,
        )

    def get_eligible_candidates(
        self,
        seller_id: uuid.UUID,
        branch_id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        as_of_date: date | None = None,
        required_capacity: int = 1,
    ) -> list[Driver]:
        """Fetch all eligible driver candidates for a seller/branch without N+1 queries."""
        stmt = (
            select(Driver)
            .options(
                joinedload(Driver.compliance_documents),
                joinedload(Driver.authorizations),
                joinedload(Driver.home_branch),
            )
            .where(
                Driver.status == DriverStatus.ACTIVE.value,
                Driver.availability_status == DriverAvailabilityStatus.AVAILABLE.value,
                Driver.is_on_duty.is_(True),
            )
        )
        if tenant_id:
            stmt = stmt.where(or_(Driver.tenant_id == tenant_id, Driver.tenant_id.is_(None)))

        drivers = self.db.execute(stmt).unique().scalars().all()
        eligible: list[Driver] = []
        for driver in drivers:
            result = self.evaluate_driver(
                driver=driver,
                seller_id=seller_id,
                branch_id=branch_id,
                tenant_id=tenant_id,
                as_of_date=as_of_date,
                required_capacity=required_capacity,
            )
            if result.is_eligible:
                eligible.append(driver)
        return eligible

    def _get_active_duties_count(self, driver_id: uuid.UUID) -> int:
        """Query active duties count from database if table exists."""
        try:
            from sqlalchemy import text
            stmt = text("""
                SELECT COUNT(id) FROM driver_duties
                WHERE active_driver_id = :driver_id
                AND status IN ('ASSIGNED', 'STARTED', 'IN_PROGRESS')
            """)
            count = self.db.scalar(stmt, {"driver_id": driver_id})
            return count or 0
        except Exception:
            return 0


class DriverService:
    """Driver Domain Service handling lifecycle CRUD, shift updates, and compliance."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def onboard_driver(
        self,
        data: DriverOnboardRequest | DriverCreate,
        actor_user_id: uuid.UUID | None = None,
    ) -> Driver:
        """Onboard a new driver with profile, optional initial vehicle, and documents."""
        # 1. Resolve User
        user_id = getattr(data, "user_id", None)
        if user_id is None:
            email = getattr(data, "email", None)
            if not email:
                raise ApiError(status_code=400, code="INVALID_INPUT", message="User ID or Email is required.")
            user = self.db.execute(select(User).where(User.email == email)).scalar_one_or_none()
            if not user:
                user = User(
                    email=email,
                    auth_user_id=f"auth-{email}",
                    name=data.full_name,
                )
                self.db.add(user)
                self.db.flush()
            user_id = user.id

        # Check existing driver profile
        existing = self.db.execute(select(Driver).where(Driver.user_id == user_id)).scalar_one_or_none()
        if existing:
            raise ApiError(status_code=400, code="DUPLICATE_USER", message="A driver profile already exists for this user.")

        phone_num = getattr(data, "phone_number", None) or getattr(data, "phone", None) or ""
        driver = Driver(
            user_id=user_id,
            tenant_id=data.tenant_id,
            seller_id=data.seller_id,
            home_branch_id=getattr(data, "home_branch_id", None) or getattr(data, "branch_id", None),
            branch_id=getattr(data, "branch_id", None) or getattr(data, "home_branch_id", None),
            full_name=data.full_name,
            phone_number=phone_num,
            phone=phone_num,
            status=DriverStatus.ACTIVE.value,
            is_on_duty=False,
            compliance_status=DriverComplianceStatus.PENDING.value,
            availability_status=DriverAvailabilityStatus.AVAILABLE.value,
            max_active_duties=data.max_active_duties,
        )
        self.db.add(driver)
        self.db.flush()

        # Add initial vehicle if provided
        vehicle_data = getattr(data, "vehicle", None) or getattr(data, "initial_vehicle", None)
        if vehicle_data:
            plate = getattr(vehicle_data, "plate_number", "") or getattr(vehicle_data, "license_plate", "")
            vehicle = DriverVehicle(
                driver_id=driver.id,
                make=vehicle_data.make,
                model=vehicle_data.model,
                plate_number=plate,
                license_plate=plate,
                vehicle_type=getattr(vehicle_data.vehicle_type, "value", str(vehicle_data.vehicle_type)),
                color=vehicle_data.color,
                is_active=True,
            )
            self.db.add(vehicle)

        # Add compliance documents if provided
        documents = getattr(data, "documents", [])
        for doc_data in documents:
            doc = DriverComplianceDocument(
                driver_id=driver.id,
                document_type=doc_data.document_type,
                document_number=doc_data.document_number,
                document_url=doc_data.document_url,
                valid_from=doc_data.valid_from,
                valid_until=doc_data.valid_until,
                is_verified=False,
            )
            self.db.add(doc)

        self.db.commit()
        return self.get_driver(driver.id)  # type: ignore

    def get_driver(self, driver_id: uuid.UUID) -> Driver | None:
        """Fetch driver by ID with eager relationships."""
        stmt = (
            select(Driver)
            .options(
                joinedload(Driver.vehicles),
                joinedload(Driver.compliance_documents),
                joinedload(Driver.authorizations),
                joinedload(Driver.home_branch),
            )
            .where(Driver.id == driver_id)
        )
        return self.db.execute(stmt).unique().scalar_one_or_none()

    def list_drivers(
        self,
        status: str | None = None,
        compliance_status: str | None = None,
        availability_status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Driver], int]:
        """List platform drivers with optional filtering and pagination."""
        stmt = (
            select(Driver)
            .options(
                joinedload(Driver.vehicles),
                joinedload(Driver.compliance_documents),
                joinedload(Driver.authorizations),
            )
        )
        count_stmt = select(func.count(Driver.id))

        if status:
            stmt = stmt.where(Driver.status == status)
            count_stmt = count_stmt.where(Driver.status == status)
        if compliance_status:
            stmt = stmt.where(Driver.compliance_status == compliance_status)
            count_stmt = count_stmt.where(Driver.compliance_status == compliance_status)
        if availability_status:
            stmt = stmt.where(Driver.availability_status == availability_status)
            count_stmt = count_stmt.where(Driver.availability_status == availability_status)

        total = self.db.scalar(count_stmt) or 0
        items = self.db.execute(stmt.offset(offset).limit(limit)).unique().scalars().all()
        return list(items), total

    def list_seller_drivers(
        self,
        seller_id: uuid.UUID,
        branch_id: uuid.UUID | None = None,
        availability_status: str | None = None,
        is_on_duty: bool | None = None,
    ) -> list[Driver]:
        """List drivers authorized for a specific seller/branch."""
        auth_subq = select(DriverSellerAuthorization.driver_id).where(
            DriverSellerAuthorization.seller_id == seller_id,
            DriverSellerAuthorization.is_authorized.is_(True),
        )
        if branch_id is not None:
            auth_subq = auth_subq.where(
                or_(
                    DriverSellerAuthorization.branch_id == branch_id,
                    DriverSellerAuthorization.branch_id.is_(None),
                )
            )

        stmt = (
            select(Driver)
            .options(
                joinedload(Driver.vehicles),
                joinedload(Driver.compliance_documents),
                joinedload(Driver.authorizations),
            )
            .where(
                or_(
                    Driver.seller_id == seller_id,
                    Driver.id.in_(auth_subq),
                )
            )
        )
        if branch_id is not None:
            stmt = stmt.where(
                or_(
                    Driver.home_branch_id == branch_id,
                    Driver.branch_id == branch_id,
                    Driver.home_branch_id.is_(None),
                    Driver.id.in_(auth_subq),
                )
            )
        if availability_status is not None:
            stmt = stmt.where(Driver.availability_status == availability_status)
        if is_on_duty is not None:
            stmt = stmt.where(Driver.is_on_duty.is_(is_on_duty))

        return list(self.db.execute(stmt).unique().scalars().all())

    def update_driver_status(
        self,
        driver_id: uuid.UUID,
        seller_id: uuid.UUID | None = None,
        is_on_duty: bool | None = None,
        availability_status: str | None = None,
    ) -> Driver:
        """Update shift state and operational availability."""
        driver = self.get_driver(driver_id)
        if not driver:
            raise ApiError(status_code=404, code="DRIVER_NOT_FOUND", message="Driver profile not found.")

        # If seller_id provided, verify driver authorization
        if seller_id is not None and driver.seller_id != seller_id:
            auth = self.db.execute(
                select(DriverSellerAuthorization).where(
                    DriverSellerAuthorization.driver_id == driver_id,
                    DriverSellerAuthorization.seller_id == seller_id,
                    DriverSellerAuthorization.is_authorized.is_(True),
                )
            ).scalar_one_or_none()
            if not auth:
                raise ApiError(status_code=403, code="PERMISSION_DENIED", message="Driver is not authorized for this seller.")

        if is_on_duty is not None:
            driver.is_on_duty = is_on_duty
            # Auto update availability to OFFLINE if off-duty
            if not is_on_duty and availability_status is None:
                driver.availability_status = DriverAvailabilityStatus.OFFLINE.value

        if availability_status is not None:
            driver.availability_status = availability_status

        self.db.commit()
        self.db.refresh(driver)
        return driver

    def link_driver_to_branch(
        self,
        driver_id: uuid.UUID,
        seller_id: uuid.UUID,
        branch_id: uuid.UUID,
        tenant_id: uuid.UUID,
        is_authorized: bool = True,
    ) -> DriverSellerAuthorization:
        """Link or update driver authorization to seller branch."""
        driver = self.get_driver(driver_id)
        if not driver:
            raise ApiError(status_code=404, code="DRIVER_NOT_FOUND", message="Driver not found.")

        branch = self.db.get(Branch, branch_id)
        if not branch or branch.seller_id != seller_id:
            raise ApiError(status_code=404, code="BRANCH_NOT_FOUND", message="Branch not found for this seller.")

        stmt = select(DriverSellerAuthorization).where(
            DriverSellerAuthorization.driver_id == driver_id,
            DriverSellerAuthorization.seller_id == seller_id,
            DriverSellerAuthorization.branch_id == branch_id,
        )
        auth = self.db.execute(stmt).scalar_one_or_none()
        if auth:
            auth.is_authorized = is_authorized
        else:
            auth = DriverSellerAuthorization(
                driver_id=driver_id,
                tenant_id=tenant_id,
                seller_id=seller_id,
                branch_id=branch_id,
                is_authorized=is_authorized,
            )
            self.db.add(auth)

        self.db.commit()
        self.db.refresh(auth)
        return auth

    def unlink_driver_from_branch(
        self,
        driver_id: uuid.UUID,
        seller_id: uuid.UUID,
        branch_id: uuid.UUID,
    ) -> None:
        """Revoke driver authorization for seller branch."""
        stmt = select(DriverSellerAuthorization).where(
            DriverSellerAuthorization.driver_id == driver_id,
            DriverSellerAuthorization.seller_id == seller_id,
            DriverSellerAuthorization.branch_id == branch_id,
        )
        auth = self.db.execute(stmt).scalar_one_or_none()
        if not auth:
            raise ApiError(status_code=404, code="NOT_FOUND", message="Authorization record not found.")

        auth.is_authorized = False
        self.db.commit()

    def list_compliance_documents(self, driver_id: uuid.UUID) -> list[DriverComplianceDocument]:
        """List compliance documents for a driver."""
        driver = self.get_driver(driver_id)
        if not driver:
            raise ApiError(status_code=404, code="DRIVER_NOT_FOUND", message="Driver profile not found.")
        return list(driver.compliance_documents)

    def verify_compliance_document(
        self,
        driver_id: uuid.UUID,
        document_id: uuid.UUID,
        is_verified: bool,
        valid_until: datetime | None = None,
        actor_user_id: uuid.UUID | None = None,
        rejection_reason: str | None = None,
    ) -> DriverComplianceDocument:
        """Verify or reject a driver compliance document and re-evaluate driver compliance status."""
        stmt = select(DriverComplianceDocument).where(
            DriverComplianceDocument.id == document_id,
            DriverComplianceDocument.driver_id == driver_id,
        )
        doc = self.db.execute(stmt).scalar_one_or_none()
        if not doc:
            raise ApiError(status_code=404, code="DOCUMENT_NOT_FOUND", message="Compliance document not found.")

        doc.is_verified = is_verified
        if is_verified:
            doc.verified_at = datetime.now(timezone.utc)
            doc.verified_by_user_id = actor_user_id
            doc.rejection_reason = None
            if valid_until is not None:
                doc.valid_until = valid_until
        else:
            doc.rejection_reason = rejection_reason or "Document verification rejected"

        # Re-evaluate driver overall compliance status
        driver = self.get_driver(driver_id)
        if driver:
            docs = self.db.scalars(
                select(DriverComplianceDocument).where(DriverComplianceDocument.driver_id == driver_id)
            ).all()
            docs_by_type = {d.document_type: d for d in docs}
            all_valid = True
            now_date = datetime.now(timezone.utc).date()
            for req in REQUIRED_COMPLIANCE_DOCUMENTS:
                d = docs_by_type.get(req)
                if not d or not d.is_verified:
                    all_valid = False
                    break
                if d.valid_until:
                    d_date = d.valid_until.date() if isinstance(d.valid_until, datetime) else d.valid_until
                    if d_date < now_date:
                        all_valid = False
                        break

            driver.compliance_status = (
                DriverComplianceStatus.COMPLIANT.value
                if all_valid
                else DriverComplianceStatus.PENDING.value
            )

        self.db.commit()
        self.db.refresh(doc)
        return doc

    def update_driver_location(
        self,
        driver_id: uuid.UUID,
        latitude: Decimal | float,
        longitude: Decimal | float,
    ) -> Driver:
        """Update driver's current coordinates for proximity calculations."""
        driver = self.get_driver(driver_id)
        if not driver:
            raise ApiError(status_code=404, code="DRIVER_NOT_FOUND", message="Driver not found.")

        driver.current_latitude = Decimal(str(latitude))
        driver.current_longitude = Decimal(str(longitude))
        self.db.commit()
        self.db.refresh(driver)
        return driver
