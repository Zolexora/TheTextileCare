from __future__ import annotations

from enum import Enum


class RoleName(str, Enum):
    PLATFORM_ADMIN = 'PLATFORM_ADMIN'
    PLATFORM_SUPPORT = 'PLATFORM_SUPPORT'
    TENANT_OWNER = 'TENANT_OWNER'
    TENANT_ADMIN = 'TENANT_ADMIN'
    TENANT_MEMBER = 'TENANT_MEMBER'
    TENANT_VIEWER = 'TENANT_VIEWER'


class PermissionName(str, Enum):
    TENANT_READ = 'tenant.read'
    TENANT_MANAGE = 'tenant.manage'
    MEMBERSHIP_READ = 'membership.read'
    MEMBERSHIP_MANAGE = 'membership.manage'
    ROLE_READ = 'role.read'
    ROLE_MANAGE = 'role.manage'
    USER_READ = 'user.read'
    USER_MANAGE = 'user.manage'
    AUDIT_READ = 'audit.read'


PLATFORM_ROLES = {
    RoleName.PLATFORM_ADMIN.value,
    RoleName.PLATFORM_SUPPORT.value,
}

TENANT_ROLES = {
    RoleName.TENANT_OWNER.value,
    RoleName.TENANT_ADMIN.value,
    RoleName.TENANT_MEMBER.value,
    RoleName.TENANT_VIEWER.value,
}

# Role to Permissions matrix following least privilege
DEFAULT_ROLE_PERMISSIONS: dict[str, list[str]] = {
    RoleName.PLATFORM_ADMIN.value: [
        PermissionName.TENANT_READ.value,
        PermissionName.TENANT_MANAGE.value,
        PermissionName.MEMBERSHIP_READ.value,
        PermissionName.MEMBERSHIP_MANAGE.value,
        PermissionName.ROLE_READ.value,
        PermissionName.ROLE_MANAGE.value,
        PermissionName.USER_READ.value,
        PermissionName.USER_MANAGE.value,
        PermissionName.AUDIT_READ.value,
    ],
    RoleName.PLATFORM_SUPPORT.value: [
        PermissionName.TENANT_READ.value,
        PermissionName.MEMBERSHIP_READ.value,
        PermissionName.ROLE_READ.value,
        PermissionName.USER_READ.value,
        PermissionName.AUDIT_READ.value,
    ],
    RoleName.TENANT_OWNER.value: [
        PermissionName.TENANT_READ.value,
        PermissionName.TENANT_MANAGE.value,
        PermissionName.MEMBERSHIP_READ.value,
        PermissionName.MEMBERSHIP_MANAGE.value,
        PermissionName.ROLE_READ.value,
        PermissionName.USER_READ.value,
        PermissionName.AUDIT_READ.value,
    ],
    RoleName.TENANT_ADMIN.value: [
        PermissionName.TENANT_READ.value,
        PermissionName.TENANT_MANAGE.value,
        PermissionName.MEMBERSHIP_READ.value,
        PermissionName.MEMBERSHIP_MANAGE.value,
        PermissionName.ROLE_READ.value,
        PermissionName.USER_READ.value,
        PermissionName.AUDIT_READ.value,
    ],
    RoleName.TENANT_MEMBER.value: [
        PermissionName.TENANT_READ.value,
        PermissionName.MEMBERSHIP_READ.value,
        PermissionName.USER_READ.value,
    ],
    RoleName.TENANT_VIEWER.value: [
        PermissionName.TENANT_READ.value,
    ],
}
