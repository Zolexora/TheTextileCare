from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID | None = None
    actor_user_id: uuid.UUID | None = None
    event_type: str
    entity_type: str | None = None
    entity_id: str | None = None
    payload: dict[str, Any] = {}
    created_at: datetime


class AuditListResponse(BaseModel):
    items: list[AuditEventResponse]
    total: int
