from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select

from app.models.audit import AuditEvent
from app.repositories.base import BaseRepository

SENSITIVE_KEYS = {
    'password',
    'token',
    'secret',
    'api_key',
    'access_token',
    'refresh_token',
    'authorization',
    'private_key',
    'credential',
}


def sanitize_payload(data: Any) -> Any:
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if any(sensitive in k.lower() for sensitive in SENSITIVE_KEYS):
                sanitized[k] = '[REDACTED]'
            else:
                sanitized[k] = sanitize_payload(v)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_payload(item) for item in data]
    return data


class AuditRepository(BaseRepository):
    def create(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        tenant_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
    ) -> AuditEvent:
        clean_payload = sanitize_payload(payload or {})
        event = AuditEvent(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            payload=clean_payload,
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return event

    def list_for_tenant(
        self, tenant_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> list[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .where(AuditEvent.tenant_id == tenant_id)
            .order_by(AuditEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())

    def count_for_tenant(self, tenant_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(AuditEvent).where(AuditEvent.tenant_id == tenant_id)
        return self.db.execute(stmt).scalar_one()

    def list_platform_events(self, limit: int = 50, offset: int = 0) -> list[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .where(AuditEvent.tenant_id.is_(None))
            .order_by(AuditEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(self.db.execute(stmt).scalars().all())
