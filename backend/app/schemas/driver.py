"""Phase 8 — Driver Domain Pydantic v2 Schemas."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.driver import (
    ComplianceDocType,
    ComplianceDocumentType,
    DriverAvailabilityStatus,
    DriverComplianceStatus,
    DriverStatus,
    VehicleType,
)

__all__ = [
    "DriverStatus",
    "DriverComplianceStatus",
    "DriverAvailabilityStatus",
    "VehicleType",
    "ComplianceDocumentType",
    "ComplianceDocType",
    "DriverVehicleBase",
    "DriverVehicleCreate",
    "DriverVehicleUpdate",
    "DriverVehicleResponse",
    "DriverComplianceDocumentBase",
    "DriverComplianceBase",
    "DriverComplianceDocumentCreate",
    "DriverComplianceCreate",
    "DriverComplianceDocumentVerifyRequest",
    "ComplianceVerifyRequest",
    "DriverComplianceDocumentResponse",
    "DriverComplianceResponse",
    "DriverSellerAuthorizationCreate",
    "DriverBranchLinkRequest",
    "DriverSellerAuthorizationResponse",
    "DriverCreate",
    "DriverUpdate",
    "DriverStatusUpdateRequest",
    "DriverShiftUpdate",
    "DriverLocationUpdate",
    "DriverOnboardRequest",
    "DriverResponse",
    "DriverDetailResponse",
    "DriverListResponse",
    "CustomerDriverInfoResponse",
    "DutyRankingContext",
    "CandidateRankingProfile",
    "DriverScoreBreakdown",
    "DriverRankingResult",
    "EligibilityEvaluationResult",
]


# ---------------------------------------------------------------------------
# Vehicle Schemas
# ---------------------------------------------------------------------------
class DriverVehicleBase(BaseModel):
    make: str = Field(..., min_length=1, max_length=100)
    model: str = Field(..., min_length=1, max_length=100)
    plate_number: str = Field("", max_length=50)
    license_plate: str | None = Field(default=None, max_length=50)
    vehicle_type: VehicleType = VehicleType.SCOOTER
    color: str | None = Field(default=None, max_length=50)


class DriverVehicleCreate(DriverVehicleBase):
    pass


class DriverVehicleUpdate(BaseModel):
    make: str | None = Field(default=None, min_length=1, max_length=100)
    model: str | None = Field(default=None, min_length=1, max_length=100)
    plate_number: str | None = Field(default=None, max_length=50)
    license_plate: str | None = Field(default=None, max_length=50)
    vehicle_type: VehicleType | None = None
    color: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None


class DriverVehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    driver_id: uuid.UUID
    make: str
    model: str
    plate_number: str
    license_plate: str | None = None
    vehicle_type: str
    color: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Compliance Document Schemas
# ---------------------------------------------------------------------------
class DriverComplianceDocumentBase(BaseModel):
    document_type: str = Field(..., max_length=50)
    document_number: str | None = Field(default=None, max_length=100)
    document_url: str | None = Field(default=None, max_length=1000)
    valid_from: datetime | None = None
    valid_until: datetime | None = None


DriverComplianceBase = DriverComplianceDocumentBase


class DriverComplianceDocumentCreate(DriverComplianceDocumentBase):
    pass


DriverComplianceCreate = DriverComplianceDocumentCreate


class DriverComplianceDocumentVerifyRequest(BaseModel):
    is_verified: bool
    valid_until: datetime | None = None
    rejection_reason: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=500)


ComplianceVerifyRequest = DriverComplianceDocumentVerifyRequest


class DriverComplianceDocumentResponse(DriverComplianceDocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    driver_id: uuid.UUID
    is_verified: bool
    verified_at: datetime | None = None
    verified_by_user_id: uuid.UUID | None = None
    rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime
    is_valid: bool = False


DriverComplianceResponse = DriverComplianceDocumentResponse


# ---------------------------------------------------------------------------
# Seller Authorization Schemas
# ---------------------------------------------------------------------------
class DriverSellerAuthorizationCreate(BaseModel):
    tenant_id: uuid.UUID
    seller_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    is_authorized: bool = True


class DriverBranchLinkRequest(BaseModel):
    is_authorized: bool = True


class DriverSellerAuthorizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    driver_id: uuid.UUID
    tenant_id: uuid.UUID
    seller_id: uuid.UUID
    branch_id: uuid.UUID | None = None
    is_authorized: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Driver Profile & Shift Schemas
# ---------------------------------------------------------------------------
class DriverCreate(BaseModel):
    user_id: uuid.UUID
    tenant_id: uuid.UUID | None = None
    seller_id: uuid.UUID | None = None
    home_branch_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    full_name: str = Field(..., min_length=1, max_length=255)
    phone_number: str = Field(..., min_length=5, max_length=50)
    phone: str | None = Field(default=None, max_length=50)
    max_active_duties: int = Field(default=3, ge=1, le=20)
    initial_vehicle: DriverVehicleCreate | None = None


class DriverUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone_number: str | None = Field(default=None, min_length=5, max_length=50)
    phone: str | None = Field(default=None, max_length=50)
    home_branch_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    status: DriverStatus | None = None
    max_active_duties: int | None = Field(default=None, ge=1, le=20)


class DriverStatusUpdateRequest(BaseModel):
    is_on_duty: bool | None = None
    availability_status: str | None = Field(default=None, max_length=50)


class DriverShiftUpdate(BaseModel):
    is_on_duty: bool
    availability_status: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None


class DriverLocationUpdate(BaseModel):
    latitude: Decimal = Field(..., ge=Decimal("-90.0"), le=Decimal("90.0"))
    longitude: Decimal = Field(..., ge=Decimal("-180.0"), le=Decimal("180.0"))


class DriverOnboardRequest(BaseModel):
    email: str = Field(..., max_length=255)
    full_name: str = Field(..., max_length=255)
    phone_number: str = Field(..., max_length=50)
    tenant_id: uuid.UUID | None = None
    seller_id: uuid.UUID | None = None
    home_branch_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    max_active_duties: int = Field(default=3, ge=1, le=20)
    vehicle: DriverVehicleCreate | None = None
    documents: list[DriverComplianceCreate] = Field(default_factory=list)


class DriverResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    tenant_id: uuid.UUID | None = None
    seller_id: uuid.UUID | None = None
    home_branch_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    full_name: str
    phone_number: str
    phone: str | None = None
    status: str
    compliance_status: str
    availability_status: str
    is_on_duty: bool
    max_active_duties: int
    current_latitude: Decimal | float | None = None
    current_longitude: Decimal | float | None = None
    is_eligible_for_dispatch: bool = False
    created_at: datetime
    updated_at: datetime


class DriverDetailResponse(DriverResponse):
    vehicles: list[DriverVehicleResponse] = Field(default_factory=list)
    compliance_documents: list[DriverComplianceDocumentResponse] = Field(default_factory=list)
    authorizations: list[DriverSellerAuthorizationResponse] = Field(default_factory=list)


class DriverListResponse(BaseModel):
    items: list[DriverResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Customer-Facing Active Driver Payload (R3 Invariant)
# ---------------------------------------------------------------------------
class CustomerDriverInfoResponse(BaseModel):
    driver_name: str
    driver_phone: str  # Unmasked actual phone number per R3
    vehicle_make: str
    vehicle_model: str
    vehicle_plate_number: str
    vehicle_type: str
    vehicle_color: str | None = None


# ---------------------------------------------------------------------------
# Priority Engine & Eligibility Contexts & Results
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DutyRankingContext:
    """Normalized duty context required for driver candidate ranking."""

    duty_id: uuid.UUID
    seller_id: uuid.UUID
    tenant_id: uuid.UUID
    customer_id: uuid.UUID
    customer_address_id: uuid.UUID | None = None
    branch_id: uuid.UUID | None = None
    target_latitude: float | None = None
    target_longitude: float | None = None


@dataclass
class CandidateRankingProfile:
    """Historical familiarity and operational metrics for a candidate driver."""

    driver: Any  # Driver model instance
    address_familiarity_count: int = 0
    customer_familiarity_count: int = 0
    active_duties_count: int = 0
    distance_meters: float = float("inf")


@dataclass(frozen=True)
class DriverScoreBreakdown:
    """Detailed score breakdown for auditable ranking evaluation."""

    address_familiarity: int
    customer_familiarity: int
    active_duties: int
    distance_meters: float
    distance_km: float = 0.0


@dataclass(frozen=True)
class DriverRankingResult:
    """Deterministic ranking output item for a candidate driver."""

    driver_id: uuid.UUID
    driver: Any  # Driver model instance
    rank: int  # 1-indexed (1 = primary selected candidate)
    score_breakdown: DriverScoreBreakdown

    # Convenience score properties for test ergonomics
    @property
    def address_familiarity_score(self) -> int:
        return self.score_breakdown.address_familiarity

    @property
    def customer_familiarity_score(self) -> int:
        return self.score_breakdown.customer_familiarity

    @property
    def active_workload(self) -> int:
        return self.score_breakdown.active_duties

    @property
    def distance_km(self) -> float:
        return self.score_breakdown.distance_km


@dataclass(frozen=True)
class EligibilityEvaluationResult:
    """Result of binary eligibility evaluation with diagnostic reasons."""

    is_eligible: bool
    driver_id: uuid.UUID
    reasons: list[str]
    active_duties_count: int
    max_active_duties: int
