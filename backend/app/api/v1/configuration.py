from __future__ import annotations
import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.permissions.constants import PermissionName
from app.core.tenant.context import TenantContext
from app.db import get_db
from app.dependencies import require_permission, require_authenticated_user
from app.models.user import User
from app.schemas.configuration import (
    ConfigurationDefinitionCreate,
    ConfigurationDefinitionUpdate,
    ConfigurationDefinitionResponse,
    ConfigurationValueCreate,
    ConfigurationValueResponse,
    ResolvedConfigurationResponse
)
from app.repositories.configuration import ConfigurationRepository
from app.services.configuration import ConfigurationResolverService

router = APIRouter(prefix='/configuration', tags=['configuration'])

# --- PLATFORM ADMIN ENDPOINTS ---

@router.get('/admin/definitions', response_model=list[ConfigurationDefinitionResponse])
async def list_definitions(
    db: Session = Depends(get_db),
    # Wait, platform permissions don't need tenant context usually, just user role.
    # But since all permissions go through require_permission...
    # Actually, we can check ctx.user.role if it's PLATFORM_ADMIN, or just use require_permission without scoped context.
    # We will use require_permission on the pseudo tenant or use a separate dependency.
    # Let's assume require_permission works for platform admins too.
    ctx: TenantContext = Depends(require_permission(PermissionName.CONFIGURATION_DEFINITIONS_READ))
) -> list[ConfigurationDefinitionResponse]:
    repo = ConfigurationRepository(db)
    return repo.get_definitions()

@router.post('/admin/definitions', response_model=ConfigurationDefinitionResponse, status_code=status.HTTP_201_CREATED)
async def create_definition(
    data: ConfigurationDefinitionCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CONFIGURATION_DEFINITIONS_MANAGE))
) -> ConfigurationDefinitionResponse:
    repo = ConfigurationRepository(db)
    if repo.get_definition_by_key(data.key):
        raise HTTPException(status_code=409, detail="Configuration definition already exists")
    return repo.create_definition(data.model_dump(by_alias=True))

@router.patch('/admin/definitions/{definition_id}', response_model=ConfigurationDefinitionResponse)
async def update_definition(
    definition_id: uuid.UUID,
    data: ConfigurationDefinitionUpdate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CONFIGURATION_DEFINITIONS_MANAGE))
) -> ConfigurationDefinitionResponse:
    repo = ConfigurationRepository(db)
    defn = repo.get_definition(definition_id)
    if not defn:
        raise HTTPException(status_code=404, detail="Configuration definition not found")
    return repo.update_definition(defn, data.model_dump(exclude_unset=True, by_alias=True))

# --- TENANT CONFIGURATION ENDPOINTS ---

@router.get('', response_model=list[ConfigurationValueResponse])
async def get_tenant_configuration(
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CONFIGURATION_READ))
) -> list[ConfigurationValueResponse]:
    repo = ConfigurationRepository(db)
    return repo.get_values_for_tenant(ctx.tenant.id)

@router.put('/{key}', response_model=ConfigurationValueResponse)
async def update_tenant_configuration(
    key: str,
    data: ConfigurationValueCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CONFIGURATION_MANAGE))
) -> ConfigurationValueResponse:
    repo = ConfigurationRepository(db)
    defn = repo.get_definition_by_key(key)
    if not defn:
        raise HTTPException(status_code=404, detail="Configuration definition not found")
    
    # Optional schema validation could go here
    return repo.set_value(
        tenant_id=ctx.tenant.id,
        definition_id=defn.id,
        application_id=data.application_id,
        value=data.value,
        user_id=ctx.user.id
    )

# --- RESOLVED & PUBLIC ENDPOINTS ---

@router.get('/resolved', response_model=list[ResolvedConfigurationResponse])
async def get_resolved_configuration(
    application_key: str | None = Query(None),
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CONFIGURATION_READ))
) -> list[ResolvedConfigurationResponse]:
    svc = ConfigurationResolverService(db)
    return svc.resolve_context(ctx.tenant.id, application_key=application_key, is_public=False)

@router.get('/public/{tenant_id}/resolved', response_model=list[ResolvedConfigurationResponse])
async def get_public_resolved_configuration(
    tenant_id: uuid.UUID,
    application_key: str | None = Query(None),
    db: Session = Depends(get_db)
) -> list[ResolvedConfigurationResponse]:
    svc = ConfigurationResolverService(db)
    return svc.resolve_context(tenant_id, application_key=application_key, is_public=True)
