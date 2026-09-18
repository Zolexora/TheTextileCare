from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.permissions.constants import (
    DEFAULT_ROLE_PERMISSIONS,
    PLATFORM_ROLES,
    PermissionName,
    RoleName,
)
from app.models.permission import Permission
from app.models.role import Role
from app.repositories.roles import RoleRepository

ROLE_DESCRIPTIONS: dict[str, str] = {
    RoleName.PLATFORM_ADMIN.value: 'Platform super administrator with unrestricted access',
    RoleName.PLATFORM_SUPPORT.value: 'Platform support personnel with operational visibility',
    RoleName.TENANT_OWNER.value: 'Tenant owner with complete organizational control',
    RoleName.TENANT_ADMIN.value: 'Tenant administrator managing members and settings',
    RoleName.TENANT_MEMBER.value: 'Standard tenant member with operational permissions',
    RoleName.TENANT_VIEWER.value: 'Read-only tenant viewer',
    RoleName.SELLER_OWNER.value: 'Seller owner with complete control',
    RoleName.SELLER_ADMIN.value: 'Seller administrator managing branches and staff',
    RoleName.STAFF.value: 'Seller staff with operational permissions',
    RoleName.VIEWER.value: 'Read-only seller viewer',
}

PERMISSION_DESCRIPTIONS: dict[str, str] = {
    PermissionName.TENANT_READ.value: 'View tenant details and configuration',
    PermissionName.TENANT_MANAGE.value: 'Modify tenant configuration and settings',
    PermissionName.MEMBERSHIP_READ.value: 'View tenant membership roster and roles',
    PermissionName.MEMBERSHIP_MANAGE.value: 'Add, modify, or remove tenant memberships',
    PermissionName.ROLE_READ.value: 'View role and permission definitions',
    PermissionName.ROLE_MANAGE.value: 'Manage roles and permission mappings',
    PermissionName.USER_READ.value: 'View user profile information',
    PermissionName.USER_MANAGE.value: 'Manage user profiles and statuses',
    PermissionName.AUDIT_READ.value: 'View audit logs for authorized scope',
    PermissionName.SELLER_READ.value: 'View seller details',
    PermissionName.SELLER_MANAGE.value: 'Manage seller details and lifecycle',
    PermissionName.SELLER_BRANCHES_READ.value: 'View seller branches',
    PermissionName.SELLER_BRANCHES_MANAGE.value: 'Manage seller branches',
    PermissionName.SELLER_STAFF_READ.value: 'View seller staff profiles',
    PermissionName.SELLER_STAFF_MANAGE.value: 'Manage seller staff profiles',
    PermissionName.SELLER_SETTINGS_READ.value: 'View seller settings',

    PermissionName.SELLER_SETTINGS_MANAGE.value: 'Manage seller settings',
    PermissionName.CONFIGURATION_READ.value: 'View tenant and public configuration',
    PermissionName.CONFIGURATION_MANAGE.value: 'Modify tenant configuration',
    PermissionName.CONFIGURATION_PUBLISH.value: 'Publish tenant configuration',
    PermissionName.CONFIGURATION_DEFINITIONS_READ.value: 'View platform configuration definitions',
    PermissionName.CONFIGURATION_DEFINITIONS_MANAGE.value: 'Manage platform configuration definitions',
}


class RoleService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.role_repo = RoleRepository(db)

    def seed_defaults(self) -> None:
        """Seeds default platform and tenant roles, permissions, and their mappings."""
        # 1. Seed Permissions
        permissions_by_name: dict[str, Permission] = {}
        for perm_name, desc in PERMISSION_DESCRIPTIONS.items():
            perm = self.role_repo.get_permission_by_name(perm_name)
            if not perm:
                perm = self.role_repo.create_permission(name=perm_name, description=desc)
            permissions_by_name[perm_name] = perm

        # 2. Seed Roles and Mappings
        for role_name, perms in DEFAULT_ROLE_PERMISSIONS.items():
            is_platform = role_name in PLATFORM_ROLES
            desc = ROLE_DESCRIPTIONS.get(role_name, role_name)
            role = self.role_repo.get_by_name(role_name)
            if not role:
                role = self.role_repo.create(
                    name=role_name,
                    description=desc,
                    is_platform_role=is_platform,
                )

            # Assign permissions
            for perm_name in perms:
                perm = permissions_by_name.get(perm_name)
                if perm:
                    self.role_repo.assign_permission_to_role(role.id, perm.id)

    def list_roles(self) -> list[Role]:
        return self.role_repo.list_all()

    def get_permissions_for_role(self, role_name: str) -> set[str]:
        role = self.role_repo.get_by_name(role_name)
        if not role:
            return set()
        return {p.name for p in role.permissions}
