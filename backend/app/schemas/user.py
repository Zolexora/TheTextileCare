from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserBase(BaseModel):
    email: EmailStr
    name: str | None = None
    status: str = 'ACTIVE'


class UserCreate(UserBase):
    auth_user_id: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    auth_user_id: str
    email: str
    name: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime
