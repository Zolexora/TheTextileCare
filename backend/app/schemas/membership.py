from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class MembershipCreate(BaseModel):
    user_id: uuid.UUID | None = None
    email: EmailStr | None = None
    role: str = Field(min_length=1)
    status: str = 'ACTIVE'


class MembershipUpdate(BaseModel):
    role: str | None = None
    status: str | None = None


class MembershipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    role_id: uuid.UUID
    role: str
    status: str
    email: str | None = None
    name: str | None = None
    created_at: datetime
    updated_at: datetime


class MembershipResponseWrapper(BaseModel):
    membership: MembershipResponse


class MembershipListResponse(BaseModel):
    items: list[MembershipResponse]
    total: int
