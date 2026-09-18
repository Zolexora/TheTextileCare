from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.exceptions.base import ApiError
from app.core.permissions.constants import PermissionName
from app.core.tenant.context import TenantContext
from app.db import get_db
from app.dependencies import (
    require_permission,
    require_scoped_tenant_context,
)
from app.schemas.membership import (
    MembershipCreate,
    MembershipListResponse,
    MembershipResponse,
    MembershipResponseWrapper,
    MembershipUpdate,
)
from app.services.memberships import MembershipService

router = APIRouter(prefix='/tenants', tags=['memberships'])


def _to_membership_response(m) -> MembershipResponse:
    return MembershipResponse(
        id=m.id,
        tenant_id=m.tenant_id,
        user_id=m.user_id,
        role_id=m.role_id,
        role=m.role.name if m.role else '',
        status=m.status,
        email=m.user.email if m.user else None,
        name=m.user.name if m.user else None,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )


# --- Current Tenant Endpoints ---


@router.get(
    '/current/members',
    response_model=MembershipListResponse,
    summary='List members of current tenant',
)
async def list_current_tenant_members(
    context: TenantContext = Depends(require_permission(PermissionName.MEMBERSHIP_READ.value)),
    db: Session = Depends(get_db),
) -> MembershipListResponse:
    service = MembershipService(db)
    members = service.list_members(context.tenant.id)
    items = [_to_membership_response(m) for m in members]
    return MembershipListResponse(items=items, total=len(items))


@router.post(
    '/current/members',
    response_model=MembershipResponseWrapper,
    status_code=201,
    summary='Add member to current tenant',
)
async def add_current_tenant_member(
    data: MembershipCreate,
    context: TenantContext = Depends(require_permission(PermissionName.MEMBERSHIP_MANAGE.value)),
    db: Session = Depends(get_db),
) -> MembershipResponseWrapper:
    service = MembershipService(db)
    membership = service.add_member(
        tenant_id=context.tenant.id,
        user_id=data.user_id,
        email=data.email,
        role_name=data.role,
        actor_user=context.user,
        actor_role_name=context.role_name,
    )
    return MembershipResponseWrapper(membership=_to_membership_response(membership))


@router.patch(
    '/current/members/{member_identifier}',
    response_model=MembershipResponseWrapper,
    summary='Update member in current tenant',
)
async def update_current_tenant_member(
    member_identifier: uuid.UUID,
    data: MembershipUpdate,
    context: TenantContext = Depends(require_permission(PermissionName.MEMBERSHIP_MANAGE.value)),
    db: Session = Depends(get_db),
) -> MembershipResponseWrapper:
    service = MembershipService(db)
    membership = service.update_member(
        tenant_id=context.tenant.id,
        member_identifier=member_identifier,
        actor_user=context.user,
        actor_role_name=context.role_name,
        role_name=data.role,
        status=data.status,
    )
    return MembershipResponseWrapper(membership=_to_membership_response(membership))


@router.delete(
    '/current/members/{member_identifier}',
    status_code=204,
    summary='Remove member from current tenant',
)
async def remove_current_tenant_member(
    member_identifier: uuid.UUID,
    context: TenantContext = Depends(require_permission(PermissionName.MEMBERSHIP_MANAGE.value)),
    db: Session = Depends(get_db),
) -> Response:
    service = MembershipService(db)
    service.remove_member(
        tenant_id=context.tenant.id,
        member_identifier=member_identifier,
        actor_user=context.user,
        actor_role_name=context.role_name,
    )
    return Response(status_code=204)


# --- Scoped Tenant ID Endpoints ---


@router.get(
    '/{tenant_id}/members',
    response_model=MembershipListResponse,
    summary='List members of specified tenant',
)
async def list_scoped_tenant_members(
    context: TenantContext = Depends(require_scoped_tenant_context),
    db: Session = Depends(get_db),
) -> MembershipListResponse:
    if not context.has_permission(PermissionName.MEMBERSHIP_READ.value):
        raise ApiError(
            status_code=403,
            code='PERMISSION_DENIED',
            message='Missing membership.read permission for this tenant.',
        )
    service = MembershipService(db)
    members = service.list_members(context.tenant.id)
    items = [_to_membership_response(m) for m in members]
    return MembershipListResponse(items=items, total=len(items))


@router.post(
    '/{tenant_id}/members',
    response_model=MembershipResponseWrapper,
    status_code=201,
    summary='Add member to specified tenant',
)
async def add_scoped_tenant_member(
    data: MembershipCreate,
    context: TenantContext = Depends(require_scoped_tenant_context),
    db: Session = Depends(get_db),
) -> MembershipResponseWrapper:
    if not context.has_permission(PermissionName.MEMBERSHIP_MANAGE.value):
        raise ApiError(
            status_code=403,
            code='PERMISSION_DENIED',
            message='Missing membership.manage permission for this tenant.',
        )
    service = MembershipService(db)
    membership = service.add_member(
        tenant_id=context.tenant.id,
        user_id=data.user_id,
        email=data.email,
        role_name=data.role,
        actor_user=context.user,
        actor_role_name=context.role_name,
    )
    return MembershipResponseWrapper(membership=_to_membership_response(membership))


@router.patch(
    '/{tenant_id}/members/{member_identifier}',
    response_model=MembershipResponseWrapper,
    summary='Update member in specified tenant',
)
async def update_scoped_tenant_member(
    member_identifier: uuid.UUID,
    data: MembershipUpdate,
    context: TenantContext = Depends(require_scoped_tenant_context),
    db: Session = Depends(get_db),
) -> MembershipResponseWrapper:
    if not context.has_permission(PermissionName.MEMBERSHIP_MANAGE.value):
        raise ApiError(
            status_code=403,
            code='PERMISSION_DENIED',
            message='Missing membership.manage permission for this tenant.',
        )
    service = MembershipService(db)
    membership = service.update_member(
        tenant_id=context.tenant.id,
        member_identifier=member_identifier,
        actor_user=context.user,
        actor_role_name=context.role_name,
        role_name=data.role,
        status=data.status,
    )
    return MembershipResponseWrapper(membership=_to_membership_response(membership))


@router.delete(
    '/{tenant_id}/members/{member_identifier}',
    status_code=204,
    summary='Remove member from specified tenant',
)
async def remove_scoped_tenant_member(
    member_identifier: uuid.UUID,
    context: TenantContext = Depends(require_scoped_tenant_context),
    db: Session = Depends(get_db),
) -> Response:
    if not context.has_permission(PermissionName.MEMBERSHIP_MANAGE.value):
        raise ApiError(
            status_code=403,
            code='PERMISSION_DENIED',
            message='Missing membership.manage permission for this tenant.',
        )
    service = MembershipService(db)
    service.remove_member(
        tenant_id=context.tenant.id,
        member_identifier=member_identifier,
        actor_user=context.user,
        actor_role_name=context.role_name,
    )
    return Response(status_code=204)
