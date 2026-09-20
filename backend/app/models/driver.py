"""Phase 8 — Driver Domain Models.

Manages driver profiles, vehicles, compliance verification credentials,
and seller branch logistics authorizations.
"""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

if TYPE_CHECKING:
    from app.models.seller import Branch, Seller
    from app.models.tenant import Tenant
    from app.models.user import User


class DriverStatus(str, enum.Enum):
    """Operational lifecycle status of a driver."""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ON_LEAVE = "ON_LEAVE"
    SUSPENDED = "SUSPENDED"


class DriverComplianceStatus(str, enum.Enum):
    """Overall compliance evaluation status of a driver."""
    PENDING = "PENDING"
    COMPLIANT = "COMPLIANT"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class DriverAvailabilityStatus(str, enum.Enum):
    """Shift and availability state."""
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"


class VehicleType(str, enum.Enum):
    """Supported vehicle categories."""
    BIKE = "BIKE"
    SCOOTER = "SCOOTER"
    VAN = "VAN"
    CAR = "CAR"
    BICYCLE = "BICYCLE"


class ComplianceDocumentType(str, enum.Enum):
    """Mandatory compliance document types per Q55."""
    DL = "DL"                  # Driving License
    RC = "RC"                  # Registration Certificate
    INSURANCE = "INSURANCE"    # Vehicle Insurance
    BGC = "BGC"                # Background Verification Check


# Aliases for cross-compatibility
ComplianceDocType = ComplianceDocumentType

REQUIRED_COMPLIANCE_DOCUMENTS = {
    ComplianceDocumentType.DL.value,
    ComplianceDocumentType.RC.value,
    ComplianceDocumentType.INSURANCE.value,
    ComplianceDocumentType.BGC.value,
}


class Driver(Base):
    """Driver profile entity linked 1:1 with User."""

    __tablename__ = "drivers"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_drivers_user_id"),
        CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'ON_LEAVE', 'SUSPENDED')",
            name="ck_drivers_status",
        ),
        CheckConstraint(
            "compliance_status IN ('PENDING', 'COMPLIANT', 'EXPIRED', 'REJECTED', 'SUSPENDED')",
            name="ck_drivers_compliance_status",
        ),
        CheckConstraint(
            "availability_status IN ('AVAILABLE', 'BUSY', 'OFFLINE')",
            name="ck_drivers_availability_status",
        ),
        CheckConstraint("max_active_duties >= 1", name="ck_drivers_max_active_duties"),
        Index("ix_drivers_user_id", "user_id", unique=True),
        Index("ix_drivers_tenant_id", "tenant_id"),
        Index("ix_drivers_seller_id", "seller_id"),
        Index("ix_drivers_home_branch_id", "home_branch_id"),
        Index("ix_drivers_branch_id", "branch_id"),
        Index("ix_drivers_status_duty", "status", "is_on_duty", "compliance_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True
    )
    seller_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sellers.id", ondelete="SET NULL"), nullable=True
    )
    home_branch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("seller_branches.id", ondelete="SET NULL"), nullable=True
    )
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("seller_branches.id", ondelete="SET NULL"), nullable=True
    )

    full_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    phone_number: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    status: Mapped[str] = mapped_column(
        String(50), default=DriverStatus.ACTIVE.value, nullable=False
    )
    is_on_duty: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    compliance_status: Mapped[str] = mapped_column(
        String(50), default=DriverComplianceStatus.PENDING.value, nullable=False
    )
    availability_status: Mapped[str] = mapped_column(
        String(50), default=DriverAvailabilityStatus.AVAILABLE.value, nullable=False
    )

    current_latitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    current_longitude: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 7), nullable=True
    )
    max_active_duties: Mapped[int] = mapped_column(
        Integer, default=3, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped[User] = relationship("User")
    tenant: Mapped[Tenant | None] = relationship("Tenant")
    seller: Mapped[Seller | None] = relationship("Seller")
    home_branch: Mapped[Branch | None] = relationship(
        "Branch", foreign_keys=[home_branch_id]
    )
    branch: Mapped[Branch | None] = relationship(
        "Branch", foreign_keys=[branch_id]
    )

    vehicles: Mapped[list[DriverVehicle]] = relationship(
        "DriverVehicle", back_populates="driver", cascade="all, delete-orphan"
    )
    authorizations: Mapped[list[DriverSellerAuthorization]] = relationship(
        "DriverSellerAuthorization", back_populates="driver", cascade="all, delete-orphan"
    )
    compliance_documents: Mapped[list[DriverComplianceDocument]] = relationship(
        "DriverComplianceDocument", back_populates="driver", cascade="all, delete-orphan"
    )

    @property
    def is_eligible_for_dispatch(self) -> bool:
        """Binary eligibility evaluator for priority matching (R1, Q56, Q77)."""
        return (
            self.status == DriverStatus.ACTIVE.value
            and self.is_on_duty
            and self.availability_status == DriverAvailabilityStatus.AVAILABLE.value
            and self.compliance_status == DriverComplianceStatus.COMPLIANT.value
        )

    @property
    def resolved_phone(self) -> str:
        return self.phone_number or self.phone or ""

    @property
    def effective_branch_id(self) -> uuid.UUID | None:
        return self.home_branch_id or self.branch_id


class DriverVehicle(Base):
    """Vehicle profile registered for a driver."""

    __tablename__ = "driver_vehicles"
    __table_args__ = (
        CheckConstraint(
            "vehicle_type IN ('BIKE', 'SCOOTER', 'VAN', 'CAR', 'BICYCLE')",
            name="ck_driver_vehicles_type",
        ),
        Index("ix_driver_vehicles_driver_id", "driver_id"),
        Index("ix_driver_vehicles_plate_number", "plate_number"),
        Index("ix_driver_vehicles_license_plate", "license_plate"),
        Index("ix_driver_vehicles_driver_active", "driver_id", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False
    )

    make: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    plate_number: Mapped[str] = mapped_column(String(50), default="", nullable=False)
    license_plate: Mapped[str | None] = mapped_column(String(50), nullable=True)
    vehicle_type: Mapped[str] = mapped_column(
        String(50), default=VehicleType.SCOOTER.value, nullable=False
    )
    color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    driver: Mapped[Driver] = relationship("Driver", back_populates="vehicles")

    @property
    def resolved_plate(self) -> str:
        return self.plate_number or self.license_plate or ""


class DriverSellerAuthorization(Base):
    """Driver authorization to service a tenant, seller, or branch."""

    __tablename__ = "driver_seller_authorizations"
    __table_args__ = (
        UniqueConstraint("driver_id", "seller_id", "branch_id", name="uq_driver_seller_branch_auth"),
        Index("ix_driver_seller_auth_driver_id", "driver_id"),
        Index("ix_driver_seller_auth_seller_id", "seller_id"),
        Index("ix_driver_seller_auth_branch_id", "branch_id"),
        Index("ix_driver_seller_auth_lookup", "driver_id", "seller_id", "is_authorized"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sellers.id", ondelete="CASCADE"), nullable=False
    )
    branch_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("seller_branches.id", ondelete="CASCADE"), nullable=True
    )
    is_authorized: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    driver: Mapped[Driver] = relationship("Driver", back_populates="authorizations")
    tenant: Mapped[Tenant] = relationship("Tenant")
    seller: Mapped[Seller] = relationship("Seller")
    branch: Mapped[Branch | None] = relationship("Branch")


class DriverComplianceDocument(Base):
    """Compliance credential document for a driver (DL, RC, Insurance, BGC)."""

    __tablename__ = "driver_compliance_documents"
    __table_args__ = (
        UniqueConstraint("driver_id", "document_type", name="uq_driver_compliance_driver_doc"),
        CheckConstraint(
            "document_type IN ('DL', 'RC', 'INSURANCE', 'BGC')",
            name="ck_driver_compliance_doc_type",
        ),
        Index("ix_driver_compliance_driver_id", "driver_id"),
        Index("ix_driver_compliance_doc_type", "document_type"),
        Index("ix_driver_compliance_valid_until", "valid_until"),
        Index("ix_driver_compliance_eval", "driver_id", "document_type", "is_verified", "valid_until"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False
    )
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    document_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    document_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    valid_from: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    valid_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    rejection_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    driver: Mapped[Driver] = relationship("Driver", back_populates="compliance_documents")
    verified_by: Mapped[User | None] = relationship("User")

    @property
    def is_valid(self) -> bool:
        """Evaluates whether document is verified and unexpired.
        
        Per Q56: document expiring today is valid until end of today.
        """
        if not self.is_verified:
            return False
        if self.valid_until is not None:
            now_date = datetime.now(timezone.utc).date()
            doc_date = (
                self.valid_until.date()
                if isinstance(self.valid_until, datetime)
                else self.valid_until
            )
            if doc_date < now_date:
                return False
        return True


# Alias for backward compatibility
DriverCompliance = DriverComplianceDocument

class DutyType(str, enum.Enum):
    PICKUP = "PICKUP"
    DELIVERY = "DELIVERY"

class DutyStatus(str, enum.Enum):
    UNASSIGNED = "UNASSIGNED"
    ASSIGNED = "ASSIGNED"
    STARTED = "STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class AssignmentStatus(str, enum.Enum):
    ASSIGNED = "ASSIGNED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class DriverDuty(Base):
    __tablename__ = "driver_duties"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="RESTRICT"), nullable=False)
    seller_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sellers.id", ondelete="RESTRICT"), nullable=False)
    branch_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("seller_branches.id", ondelete="RESTRICT"), nullable=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False)
    destination_address_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("customer_addresses.id", ondelete="RESTRICT"), nullable=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"), nullable=True)
    active_driver_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True)
    
    duty_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=DutyStatus.UNASSIGNED.value, nullable=False)
    
    scheduled_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    destination_latitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    destination_longitude: Mapped[float | None] = mapped_column(Numeric(10, 7), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class DriverAssignment(Base):
    __tablename__ = "driver_assignments"
    __table_args__ = (
        # Partial unique index: only one active assignment per duty at the DB level
        Index(
            "uix_driver_assignments_duty_active",
            "duty_id",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    duty_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("driver_duties.id", ondelete="CASCADE"), nullable=False)
    driver_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("drivers.id", ondelete="RESTRICT"), nullable=False)
    
    status: Mapped[str] = mapped_column(String(50), default=AssignmentStatus.ASSIGNED.value, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reassignment_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    unassigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

