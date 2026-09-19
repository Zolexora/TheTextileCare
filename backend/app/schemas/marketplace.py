from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Sequence

from pydantic import BaseModel, ConfigDict, Field


class MarketplaceSellerResponse(BaseModel):
    """Customer-safe seller representation."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_name: str
    display_name: str | None = None
    slug: str
    description: str | None = None
    logo_url: str | None = None


class MarketplaceBranchResponse(BaseModel):
    """Customer-safe branch representation."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    seller_id: uuid.UUID
    name: str
    phone: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    latitude: float | None = None
    longitude: float | None = None


class MarketplaceCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parent_id: uuid.UUID | None = None
    name: str
    description: str | None = None
    image_url: str | None = None


class MarketplaceServiceItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    image_url: str | None = None


class MarketplaceServiceAddonResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None


class MarketplaceServiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    category_id: uuid.UUID
    name: str
    description: str | None = None
    image_url: str | None = None
    is_per_weight: bool
    is_per_item: bool
    is_per_unit: bool
    
    items: list[MarketplaceServiceItemResponse] = Field(default_factory=list)
    addons: list[MarketplaceServiceAddonResponse] = Field(default_factory=list)
