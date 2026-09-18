from __future__ import annotations

import uuid
from datetime import datetime, time
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SellerBase(BaseModel):
    business_name: str = Field(..., max_length=255)
    legal_name: str | None = Field(None, max_length=255)
    display_name: str | None = Field(None, max_length=255)
    slug: str = Field(..., max_length=100)
    description: str | None = Field(None, max_length=1000)
    business_type: str | None = Field(None, max_length=100)
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    website: str | None = Field(None, max_length=255)
    logo_url: str | None = Field(None, max_length=1000)


class SellerCreate(SellerBase):
    pass


class SellerUpdate(BaseModel):
    business_name: str | None = Field(None, max_length=255)
    legal_name: str | None = Field(None, max_length=255)
    display_name: str | None = Field(None, max_length=255)
    slug: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=1000)
    business_type: str | None = Field(None, max_length=100)
    status: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    website: str | None = Field(None, max_length=255)
    logo_url: str | None = Field(None, max_length=1000)


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
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)
    address_line_1: str | None = Field(None, max_length=255)
    address_line_2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=50)
    country: str | None = Field(None, max_length=100)
    latitude: float | None = None
    longitude: float | None = None


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    code: str | None = Field(None, max_length=50)
    status: str | None = Field(None, max_length=50)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)
    address_line_1: str | None = Field(None, max_length=255)
    address_line_2: str | None = Field(None, max_length=255)
    city: str | None = Field(None, max_length=100)
    state: str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=50)
    country: str | None = Field(None, max_length=100)
    latitude: float | None = None
    longitude: float | None = None


class BranchResponse(BranchBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    seller_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime


class StaffProfileBase(BaseModel):
    employee_code: str | None = Field(None, max_length=50)
    display_name: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)


class StaffProfileCreate(StaffProfileBase):
    user_id: uuid.UUID
    seller_id: uuid.UUID | None = None


class StaffProfileUpdate(BaseModel):
    employee_code: str | None = Field(None, max_length=50)
    display_name: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    status: str | None = Field(None, max_length=50)


class StaffProfileResponse(StaffProfileBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    seller_id: uuid.UUID | None
    user_id: uuid.UUID
    status: str
    created_at: datetime
    updated_at: datetime


class SellerSettingsBase(BaseModel):
    timezone: str = Field(default='UTC', max_length=100)
    currency: str = Field(default='USD', max_length=3)
    locale: str = Field(default='en-US', max_length=20)
    date_format: str = Field(default='YYYY-MM-DD', max_length=50)
    time_format: str = Field(default='24h', max_length=50)


class SellerSettingsUpdate(BaseModel):
    timezone: str | None = Field(None, max_length=100)
    currency: str | None = Field(None, max_length=3)
    locale: str | None = Field(None, max_length=20)
    date_format: str | None = Field(None, max_length=50)
    time_format: str | None = Field(None, max_length=50)


class SellerSettingsResponse(SellerSettingsBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    seller_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class BusinessHourBase(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6)
    is_open: bool = True
    open_time: time | None = None
    close_time: time | None = None


class BusinessHourCreate(BusinessHourBase):
    branch_id: uuid.UUID


class BusinessHourUpdate(BaseModel):
    is_open: bool | None = None
    open_time: time | None = None
    close_time: time | None = None


class BusinessHourResponse(BusinessHourBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    branch_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
