from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class ApplicationBase(BaseModel):
    key: str
    name: str
    description: str | None = None
    application_type: str
    status: str = "ACTIVE"

class ApplicationCreate(ApplicationBase):
    pass

class ApplicationResponse(ApplicationBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ApplicationModuleBase(BaseModel):
    key: str
    name: str
    description: str | None = None
    status: str = "ACTIVE"

class ApplicationModuleResponse(ApplicationModuleBase):
    id: UUID
    application_id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ConfigurationDefinitionBase(BaseModel):
    key: str
    name: str
    description: str | None = None
    domain: str
    data_type: str
    schema_: dict[str, Any] | None = Field(None, alias='schema')
    default_value: Any | None = None
    is_public: bool = False
    is_sensitive: bool = False
    status: str = "ACTIVE"

class ConfigurationDefinitionCreate(ConfigurationDefinitionBase):
    pass

class ConfigurationDefinitionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    schema_: dict[str, Any] | None = Field(None, alias='schema')
    default_value: Any | None = None
    is_public: bool | None = None
    is_sensitive: bool | None = None
    status: str | None = None

class ConfigurationDefinitionResponse(ConfigurationDefinitionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

class ConfigurationValueBase(BaseModel):
    value: Any

class ConfigurationValueCreate(ConfigurationValueBase):
    definition_id: UUID
    application_id: UUID | None = None
    module_id: UUID | None = None

class ConfigurationValueResponse(ConfigurationValueBase):
    id: UUID
    tenant_id: UUID
    application_id: UUID | None
    module_id: UUID | None
    definition_id: UUID
    version: int
    status: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ConfigurationValueUpdateRequest(ConfigurationValueBase):
    pass

class ResolvedConfigurationResponse(BaseModel):
    key: str
    value: Any
    is_public: bool
    domain: str
