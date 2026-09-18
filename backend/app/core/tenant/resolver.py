from __future__ import annotations

import uuid

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions.base import ApiError
from app.core.permissions.constants import RoleName
from app.core.tenant.context import TenantContext
from app.models.membership import Membership
from app.models.role import Role
from app.models.user import User
from app.repositories.memberships import MembershipRepository
from app.repositories.tenants import TenantRepository


class TenantResolver:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.tenant_repo = TenantRepository(db)
        self.membership_repo = MembershipRepository(db)

    def is_user_platform_admin(self, user_id: uuid.UUID) -> bool:
        stmt = (
            select(Membership)
            .join(Role, Role.id == Membership.role_id)
            .where(
                Membership.user_id == user_id,
                Membership.status == 'ACTIVE',
                Role.name == RoleName.PLATFORM_ADMIN.value,
            )
        )
        return self.db.execute(stmt).scalar_one_or_none() is not None

    def is_user_platform_support(self, user_id: uuid.UUID) -> bool:
        stmt = (
            select(Membership)
            .join(Role, Role.id == Membership.role_id)
            .where(
                Membership.user_id == user_id,
                Membership.status == 'ACTIVE',
                Role.name == RoleName.PLATFORM_SUPPORT.value,
            )
        )
        return self.db.execute(stmt).scalar_one_or_none() is not None

    def resolve(
        self,
        request: Request,
        user: User,
        explicit_tenant_id: uuid.UUID | None = None,
    ) -> TenantContext:
        is_plat_admin = self.is_user_platform_admin(user.id)
        is_plat_support = self.is_user_platform_support(user.id)

        target_tenant_id = explicit_tenant_id
        if not target_tenant_id:
            # Check headers
            header_tid = request.headers.get('x-tenant-id') or request.headers.get('X-Tenant-Id')
            if header_tid:
                try:
                    target_tenant_id = uuid.UUID(header_tid)
                except ValueError:
                    raise ApiError(
                        status_code=400,
                        code='INVALID_TENANT_ID',
                        message='The provided X-Tenant-Id header is not a valid UUID.',
                    )

        if target_tenant_id:
            tenant = self.tenant_repo.get_by_id(target_tenant_id)
            if not tenant or tenant.status != 'ACTIVE':
                raise ApiError(
                    status_code=404,
                    code='TENANT_NOT_FOUND',
                    message='Tenant not found or inactive.',
                )

            # Check membership
            membership = self.membership_repo.get_by_tenant_and_user(target_tenant_id, user.id)
            if not membership or membership.status != 'ACTIVE':
                # If user is platform admin or support, allow access in platform mode
                if is_plat_admin or is_plat_support:
                    permissions = set()
                    if is_plat_admin:
                        from app.core.permissions.constants import DEFAULT_ROLE_PERMISSIONS

                        permissions = set(DEFAULT_ROLE_PERMISSIONS[RoleName.PLATFORM_ADMIN.value])
                    elif is_plat_support:
                        from app.core.permissions.constants import DEFAULT_ROLE_PERMISSIONS

                        permissions = set(DEFAULT_ROLE_PERMISSIONS[RoleName.PLATFORM_SUPPORT.value])

                    return TenantContext(
                        user=user,
                        tenant=tenant,
                        membership=None,
                        role=None,
                        permissions=permissions,
                        is_platform_admin=is_plat_admin,
                        is_platform_support=is_plat_support,
                    )

                # Cross-tenant access denied
                raise ApiError(
                    status_code=403,
                    code='ACCESS_DENIED',
                    message='You do not have access to this tenant.',
                )

            role = membership.role
            permissions = {p.name for p in role.permissions} if role else set()

            return TenantContext(
                user=user,
                tenant=tenant,
                membership=membership,
                role=role,
                permissions=permissions,
                is_platform_admin=is_plat_admin,
                is_platform_support=is_plat_support,
            )

        # No tenant specified in header or explicitly: resolve from user's active memberships
        user_memberships = self.membership_repo.list_for_user(user.id)
        if not user_memberships:
            raise ApiError(
                status_code=403,
                code='NO_TENANT_MEMBERSHIP',
                message='User has no active tenant memberships. Please specify a tenant context.',
            )

        # Default to first active tenant membership
        primary_membership = user_memberships[0]
        tenant = primary_membership.tenant
        role = primary_membership.role
        permissions = {p.name for p in role.permissions} if role else set()

        return TenantContext(
            user=user,
            tenant=tenant,
            membership=primary_membership,
            role=role,
            permissions=permissions,
            is_platform_admin=is_plat_admin,
            is_platform_support=is_plat_support,
        )
