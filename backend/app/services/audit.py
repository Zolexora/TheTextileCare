from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.repositories.audit import AuditRepository


class AuditService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.audit_repo = AuditRepository(db)

    def log_event(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        tenant_id: uuid.UUID | None = None,
        actor_user_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
    ) -> AuditEvent:
        return self.audit_repo.create(
            event_type=event_type,
            payload=payload,
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )

    def list_for_tenant(
        self, tenant_id: uuid.UUID, limit: int = 50, offset: int = 0
    ) -> tuple[list[AuditEvent], int]:
        items = self.audit_repo.list_for_tenant(tenant_id=tenant_id, limit=limit, offset=offset)
        total = self.audit_repo.count_for_tenant(tenant_id=tenant_id)
        return items, total

    def list_platform_events(self, limit: int = 50, offset: int = 0) -> list[AuditEvent]:
        return self.audit_repo.list_platform_events(limit=limit, offset=offset)
