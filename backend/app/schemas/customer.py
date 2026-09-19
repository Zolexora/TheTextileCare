from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field


class CustomerAddressCreate(BaseModel):
    label: str | None = None
    recipient_name: str | None = None
    phone: str | None = None
    address_line_1: str
    address_line_2: str | None = None
    locality: str | None = None
    city: str
    state: str
    postal_code: str
    country: str = "IN"
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    is_default: bool = False


class CustomerAddressUpdate(BaseModel):
    label: str | None = None
    recipient_name: str | None = None
    phone: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    locality: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    is_default: bool | None = None


class CustomerAddressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    label: str | None = None
    recipient_name: str | None = None
    phone: str | None = None
    address_line_1: str
    address_line_2: str | None = None
    locality: str | None = None
    city: str
    state: str
    postal_code: str
    country: str
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    is_default: bool


class CustomerProfileUpdate(BaseModel):
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None


class CustomerProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    display_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class CustomerSellerLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seller_id: uuid.UUID
    status: str
    first_interaction_at: datetime
    last_interaction_at: datetime
