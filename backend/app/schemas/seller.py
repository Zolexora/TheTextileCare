from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SellerBase(BaseModel):
    name: str = Field(..., max_length=255)


class SellerCreate(SellerBase):
    pass


class SellerUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    status: str | None = Field(None, max_length=50)


class SellerResponse(SellerBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime


class BranchBase(BaseModel):
    name: str = Field(..., max_length=255)
    code: str = Field(..., max_length=50)
    timezone: str = Field(default='UTC', max_length=100)


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    status: str | None = Field(None, max_length=50)
    timezone: str | None = Field(None, max_length=100)


class BranchResponse(BranchBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    seller_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime


class StaffProfileBase(BaseModel):
    job_title: str | None = Field(None, max_length=100)


class StaffProfileCreate(StaffProfileBase):
    user_id: uuid.UUID


class StaffProfileUpdate(BaseModel):
    job_title: str | None = Field(None, max_length=100)
    status: str | None = Field(None, max_length=50)


class StaffProfileResponse(StaffProfileBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    seller_id: uuid.UUID
    user_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime


class SellerSettingsBase(BaseModel):
    currency: str = Field(default='USD', max_length=3)
    tax_rate: float | None = None
    business_hours: dict[str, Any] | None = None


class SellerSettingsUpdate(BaseModel):
    currency: str | None = Field(None, max_length=3)
    tax_rate: float | None = None
    business_hours: dict[str, Any] | None = None


class SellerSettingsResponse(SellerSettingsBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    seller_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

