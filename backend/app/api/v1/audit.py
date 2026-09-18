from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.exceptions.base import ApiError
from app.core.permissions.constants import PermissionName
from app.core.tenant.context import TenantContext
from app.db import get_db
from app.dependencies import (
    require_permission,
    require_platform_admin,
    require_scoped_tenant_context,
)
from app.models.user import User
from app.schemas.audit import AuditEventResponse, AuditListResponse
from app.services.audit import AuditService

router = APIRouter(tags=['audit'])


@router.get(
    '/tenants/current/audit-logs',
    response_model=AuditListResponse,
    summary='List audit events for current tenant',
)
async def list_current_tenant_audit_logs(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    context: TenantContext = Depends(require_permission(PermissionName.AUDIT_READ.value)),
    db: Session = Depends(get_db),
) -> AuditListResponse:
    audit_service = AuditService(db)
    items, total = audit_service.list_for_tenant(
        tenant_id=context.tenant.id, limit=limit, offset=offset
    )
    return AuditListResponse(
        items=[AuditEventResponse.model_validate(e) for e in items],
        total=total,
    )


@router.get(
    '/tenants/{tenant_id}/audit-logs',
    response_model=AuditListResponse,
    summary='List audit events for specified tenant',
)
async def list_scoped_tenant_audit_logs(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    context: TenantContext = Depends(require_scoped_tenant_context),
    db: Session = Depends(get_db),
) -> AuditListResponse:
    if not context.has_permission(PermissionName.AUDIT_READ.value):
        raise ApiError(
            status_code=403,
            code='PERMISSION_DENIED',
            message='Missing audit.read permission for this tenant.',
        )
    audit_service = AuditService(db)
    items, total = audit_service.list_for_tenant(
        tenant_id=context.tenant.id, limit=limit, offset=offset
    )
    return AuditListResponse(
        items=[AuditEventResponse.model_validate(e) for e in items],
        total=total,
    )


@router.get(
    '/platform/audit-logs',
    response_model=list[AuditEventResponse],
    summary='List platform-level audit logs',
)
async def list_platform_audit_logs(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _admin: User = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> list[AuditEventResponse]:
    audit_service = AuditService(db)
    items = audit_service.list_platform_events(limit=limit, offset=offset)
    return [AuditEventResponse.model_validate(e) for e in items]
