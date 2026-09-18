from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.models.membership import Membership
from app.models.role import Role
from app.models.tenant import Tenant
from app.models.user import User


@dataclass
class TenantContext:
    user: User
    tenant: Tenant
    membership: Membership | None
    role: Role | None
    permissions: set[str] = field(default_factory=set)
    is_platform_admin: bool = False
    is_platform_support: bool = False

    @property
    def tenant_id(self) -> uuid.UUID:
        return self.tenant.id

    @property
    def user_id(self) -> uuid.UUID:
        return self.user.id

    @property
    def role_name(self) -> str | None:
        return self.role.name if self.role else None

    def has_permission(self, permission: str) -> bool:
        if self.is_platform_admin:
            return True
        return permission in self.permissions
