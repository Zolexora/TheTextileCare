from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

# Base Models
class CatalogBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: str | None = Field(None, max_length=1000)

class CategoryBase(BaseModel):
    parent_id: UUID | None = None
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=255)
    description: str | None = Field(None, max_length=1000)
    image_url: str | None = Field(None, max_length=1000)
    sort_order: int = 0

class ServiceBase(BaseModel):
    category_id: UUID | None = None
    name: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=255)
    description: str | None = Field(None, max_length=2000)
    short_description: str | None = Field(None, max_length=500)
    service_type: str = Field("SERVICE", max_length=50)
    sort_order: int = 0
    image_url: str | None = Field(None, max_length=1000)

class ServiceItemBase(BaseModel):
    name: str = Field(..., max_length=255)
    code: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=1000)
    unit_type: str = Field("ITEM", max_length=50)
    sort_order: int = 0

class ServiceAddonBase(BaseModel):
    name: str = Field(..., max_length=255)
    code: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=1000)
    sort_order: int = 0


# Create Models
class CatalogCreate(CatalogBase):
    seller_id: UUID

class CatalogUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=1000)

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    parent_id: UUID | None = None
    name: str | None = Field(None, max_length=255)
    slug: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=1000)
    image_url: str | None = Field(None, max_length=1000)
    sort_order: int | None = None

class ServiceCreate(ServiceBase):
    pass

class ServiceUpdate(BaseModel):
    category_id: UUID | None = None
    name: str | None = Field(None, max_length=255)
    slug: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=2000)
    short_description: str | None = Field(None, max_length=500)
    service_type: str | None = Field(None, max_length=50)
    sort_order: int | None = None
    image_url: str | None = Field(None, max_length=1000)

class ServiceItemCreate(ServiceItemBase):
    pass

class ServiceItemUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    code: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=1000)
    unit_type: str | None = Field(None, max_length=50)
    sort_order: int | None = None

class ServiceAddonCreate(ServiceAddonBase):
    pass

class ServiceAddonUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    code: str | None = Field(None, max_length=100)
    description: str | None = Field(None, max_length=1000)
    sort_order: int | None = None


# Response Models
class CatalogResponse(CatalogBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: UUID
    seller_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

class CategoryResponse(CategoryBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: UUID
    catalog_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

class ServiceResponse(ServiceBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: UUID
    catalog_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

class ServiceItemResponse(ServiceItemBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: UUID
    service_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

class ServiceAddonResponse(ServiceAddonBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tenant_id: UUID
    service_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime
