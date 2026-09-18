from __future__ import annotations

from pydantic import BaseModel

from app.schemas.membership import MembershipResponse
from app.schemas.tenant import TenantResponse
from app.schemas.user import UserResponse


class AuthMeResponse(BaseModel):
    user: UserResponse
    tenants: list[TenantResponse] = []
    memberships: list[MembershipResponse] = []
