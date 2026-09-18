from __future__ import annotations

import re
import uuid

from sqlalchemy.orm import Session

from app.core.exceptions.base import ApiError
from app.core.permissions.constants import RoleName
from app.models.membership import Membership
from app.models.tenant import Tenant
from app.models.user import User
from app.repositories.memberships import MembershipRepository
from app.repositories.tenants import TenantRepository
from app.services.audit import AuditService


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')


class TenantService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.tenant_repo = TenantRepository(db)
        self.membership_repo = MembershipRepository(db)
        self.audit_service = AuditService(db)

    def create_tenant(
        self,
        name: str,
        slug: str | None = None,
        creator_user: User | None = None,
    ) -> tuple[Tenant, Membership | None]:
        actual_slug = slugify(slug or name)
        if not actual_slug:
            raise ApiError(
                status_code=400, code='INVALID_SLUG', message='A valid slug is required.'
            )

        existing = self.tenant_repo.get_by_slug(actual_slug)
        if existing:
            raise ApiError(
                status_code=409,
                code='SLUG_ALREADY_EXISTS',
                message=f"Tenant slug '{actual_slug}' is already in use.",
            )

        tenant = self.tenant_repo.create(name=name, slug=actual_slug, status='ACTIVE')

        # Log tenant created audit event
        self.audit_service.log_event(
            event_type='TENANT_CREATED',
            payload={'tenant_id': str(tenant.id), 'name': tenant.name, 'slug': tenant.slug},
            tenant_id=tenant.id,
            actor_user_id=creator_user.id if creator_user else None,
            entity_type='tenant',
            entity_id=str(tenant.id),
        )

        membership: Membership | None = None
        if creator_user:
            membership = self.membership_repo.create(
                tenant_id=tenant.id,
                user_id=creator_user.id,
                role_name=RoleName.TENANT_OWNER.value,
                status='ACTIVE',
            )
            self.audit_service.log_event(
                event_type='MEMBERSHIP_CREATED',
                payload={
                    'membership_id': str(membership.id),
                    'user_id': str(creator_user.id),
                    'role': RoleName.TENANT_OWNER.value,
                },
                tenant_id=tenant.id,
                actor_user_id=creator_user.id,
                entity_type='membership',
                entity_id=str(membership.id),
            )

        return tenant, membership

    def get_by_id(self, tenant_id: uuid.UUID) -> Tenant | None:
        return self.tenant_repo.get_by_id(tenant_id)

    def get_by_slug(self, slug: str) -> Tenant | None:
        return self.tenant_repo.get_by_slug(slug)

    def list_user_tenants(self, user_id: uuid.UUID) -> list[Tenant]:
        return self.tenant_repo.list_for_user(user_id)

    def list_all(self, limit: int = 50, offset: int = 0) -> tuple[list[Tenant], int]:
        items = self.tenant_repo.list_all(limit=limit, offset=offset)
        total = self.tenant_repo.count_all()
        return items, total

    def update_tenant(
        self,
        tenant_id: uuid.UUID,
        actor_user: User | None = None,
        name: str | None = None,
        status: str | None = None,
    ) -> Tenant:
        tenant = self.tenant_repo.get_by_id(tenant_id)
        if not tenant:
            raise ApiError(status_code=404, code='TENANT_NOT_FOUND', message='Tenant not found.')

        updates = {}
        if name is not None:
            updates['name'] = name
        if status is not None:
            valid_statuses = {'ACTIVE', 'SUSPENDED', 'INACTIVE'}
            if status not in valid_statuses:
                raise ApiError(
                    status_code=400,
                    code='INVALID_STATUS',
                    message=f'Status must be one of {valid_statuses}',
                )
            updates['status'] = status

        if updates:
            tenant = self.tenant_repo.update(tenant, **updates)
            self.audit_service.log_event(
                event_type='TENANT_UPDATED',
                payload={'updates': updates},
                tenant_id=tenant.id,
                actor_user_id=actor_user.id if actor_user else None,
                entity_type='tenant',
                entity_id=str(tenant.id),
            )

        return tenant
