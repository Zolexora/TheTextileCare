from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.exceptions.base import ApiError
from app.core.permissions.constants import PermissionName
from app.core.tenant.context import TenantContext
from app.db import get_db
from app.dependencies import (
    require_authenticated_user,
    require_permission,
    require_scoped_tenant_context,
)
from app.models.user import User
from app.schemas.tenant import (
    TenantCreate,
    TenantListResponse,
    TenantResponse,
    TenantUpdate,
)
from app.services.tenants import TenantService

router = APIRouter(prefix='/tenants', tags=['tenants'])


@router.get('', response_model=TenantListResponse, summary='List accessible tenants for user')
async def list_tenants(
    current_user: User = Depends(require_authenticated_user),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> TenantListResponse:
    tenant_service = TenantService(db)
    # Check if platform admin
    from app.core.tenant.resolver import TenantResolver

    if TenantResolver(db).is_user_platform_admin(current_user.id):
        items, total = tenant_service.list_all(limit=limit, offset=offset)
    else:
        user_tenants = tenant_service.list_user_tenants(current_user.id)
        total = len(user_tenants)
        items = user_tenants[offset : offset + limit]

    return TenantListResponse(
        items=[TenantResponse.model_validate(t) for t in items],
        total=total,
    )


@router.post('', response_model=TenantResponse, status_code=201, summary='Create new tenant')
async def create_tenant(
    data: TenantCreate,
    current_user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> TenantResponse:
    tenant_service = TenantService(db)
    tenant, _ = tenant_service.create_tenant(
        name=data.name,
        slug=data.slug,
        creator_user=current_user,
    )
    return TenantResponse.model_validate(tenant)


@router.get('/current', response_model=TenantResponse, summary='Get current tenant in context')
async def get_current_tenant(
    context: TenantContext = Depends(require_permission(PermissionName.TENANT_READ.value)),
) -> TenantResponse:
    return TenantResponse.model_validate(context.tenant)


@router.patch('/current', response_model=TenantResponse, summary='Update current tenant in context')
async def update_current_tenant(
    data: TenantUpdate,
    context: TenantContext = Depends(require_permission(PermissionName.TENANT_MANAGE.value)),
    db: Session = Depends(get_db),
) -> TenantResponse:
    tenant_service = TenantService(db)
    updated = tenant_service.update_tenant(
        tenant_id=context.tenant.id,
        actor_user=context.user,
        name=data.name,
        status=data.status,
    )
    return TenantResponse.model_validate(updated)


@router.get('/{tenant_id}', response_model=TenantResponse, summary='Get specific tenant by ID')
async def get_tenant_by_id(
    context: TenantContext = Depends(require_scoped_tenant_context),
) -> TenantResponse:
    if not context.has_permission(PermissionName.TENANT_READ.value):
        raise ApiError(
            status_code=403,
            code='PERMISSION_DENIED',
            message='Missing tenant.read permission for this tenant.',
        )
    return TenantResponse.model_validate(context.tenant)


@router.patch('/{tenant_id}', response_model=TenantResponse, summary='Update specific tenant by ID')
async def update_tenant_by_id(
    data: TenantUpdate,
    context: TenantContext = Depends(require_scoped_tenant_context),
    db: Session = Depends(get_db),
) -> TenantResponse:
    if not context.has_permission(PermissionName.TENANT_MANAGE.value):
        raise ApiError(
            status_code=403,
            code='PERMISSION_DENIED',
            message='Missing tenant.manage permission for this tenant.',
        )
    tenant_service = TenantService(db)
    updated = tenant_service.update_tenant(
        tenant_id=context.tenant.id,
        actor_user=context.user,
        name=data.name,
        status=data.status,
    )
    return TenantResponse.model_validate(updated)
