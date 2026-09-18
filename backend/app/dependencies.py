from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.exceptions.base import ApiError
from app.core.security.auth import get_current_user as core_get_current_user
from app.core.tenant.context import TenantContext
from app.core.tenant.resolver import TenantResolver
from app.db import SessionLocal, engine, get_db
from app.models.user import User

__all__ = [
    'SessionLocal',
    'engine',
    'get_current_user',
    'get_db',
    'get_request_id',
    'require_authenticated_user',
    'require_permission',
    'require_platform_admin',
    'require_role',
    'require_scoped_tenant_context',
    'require_tenant_context',
]


def get_request_id(request: Request) -> str:
    return request.headers.get('x-request-id', 'unknown-request')


def require_authenticated_user(request: Request, db: Session = Depends(get_db)) -> User:
    return core_get_current_user(request, db)


# Alias for compatibility
get_current_user = require_authenticated_user


def require_tenant_context(
    request: Request,
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> TenantContext:
    resolver = TenantResolver(db)
    return resolver.resolve(request, user)


def require_scoped_tenant_context(
    tenant_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> TenantContext:
    resolver = TenantResolver(db)
    return resolver.resolve(request, user, explicit_tenant_id=tenant_id)


def require_permission(permission_name: str) -> Callable[..., TenantContext]:
    def dependency(
        context: TenantContext = Depends(require_tenant_context),
    ) -> TenantContext:
        if not context.has_permission(permission_name):
            raise ApiError(
                status_code=403,
                code='PERMISSION_DENIED',
                message=f"Missing required permission: '{permission_name}'",
            )
        return context

    return dependency


def require_role(*role_names: str) -> Callable[..., TenantContext]:
    allowed_roles = set(role_names)

    def dependency(
        context: TenantContext = Depends(require_tenant_context),
    ) -> TenantContext:
        if context.is_platform_admin:
            return context
        if context.role_name not in allowed_roles:
            raise ApiError(
                status_code=403,
                code='ROLE_DENIED',
                message=f"Role '{context.role_name}' is not authorized for this operation.",
            )
        return context

    return dependency


def require_platform_admin(
    request: Request,
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> User:
    resolver = TenantResolver(db)
    if not resolver.is_user_platform_admin(user.id):
        raise ApiError(
            status_code=403,
            code='PLATFORM_ADMIN_REQUIRED',
            message='Platform administrator privileges are required.',
        )
    return user
