from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions.base import ApiError
from app.core.permissions.constants import PLATFORM_ROLES, RoleName
from app.models.membership import Membership
from app.models.user import User
from app.repositories.memberships import MembershipRepository
from app.repositories.roles import RoleRepository
from app.repositories.users import UserRepository
from app.services.audit import AuditService


class MembershipService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.membership_repo = MembershipRepository(db)
        self.role_repo = RoleRepository(db)
        self.user_repo = UserRepository(db)
        self.audit_service = AuditService(db)

    def list_members(self, tenant_id: uuid.UUID) -> list[Membership]:
        return self.membership_repo.list_for_tenant(tenant_id)

    def add_member(
        self,
        tenant_id: uuid.UUID,
        role_name: str,
        actor_user: User,
        user_id: uuid.UUID | None = None,
        email: str | None = None,
        actor_role_name: str | None = None,
    ) -> Membership:
        # Platform role protection
        if role_name in PLATFORM_ROLES:
            raise ApiError(
                status_code=403,
                code='PLATFORM_ROLE_ESCALATION_DENIED',
                message='Cannot assign platform roles through tenant membership management.',
            )

        # Only PLATFORM_ADMIN can assign TENANT_OWNER
        if (
            role_name == RoleName.TENANT_OWNER.value
            and actor_role_name != RoleName.PLATFORM_ADMIN.value
        ):
            raise ApiError(
                status_code=403,
                code='PRIVILEGE_ESCALATION_DENIED',
                message='Cannot assign TENANT_OWNER role. Tenant ownership cannot be escalated.',
            )

        # TENANT_ADMIN cannot assign TENANT_ADMIN unless PLATFORM_ADMIN or TENANT_OWNER
        if role_name == RoleName.TENANT_ADMIN.value and actor_role_name not in {
            RoleName.PLATFORM_ADMIN.value,
            RoleName.TENANT_OWNER.value,
        }:
            raise ApiError(
                status_code=403,
                code='PRIVILEGE_ESCALATION_DENIED',
                message='Only Tenant Owners or Platform Admins can assign Tenant Admin role.',
            )

        # Resolve user
        target_user: User | None = None
        if user_id:
            target_user = self.user_repo.get_by_id(user_id)
        elif email:
            target_user = self.user_repo.get_by_email(email)
            if not target_user:
                # Provision placeholder user for invite
                target_user = self.user_repo.create(
                    email=email,
                    auth_user_id=f'auth-{email}',
                    status='ACTIVE',
                )

        if not target_user:
            raise ApiError(
                status_code=404,
                code='USER_NOT_FOUND',
                message='Target user could not be found or identified.',
            )

        # Check existing membership
        existing = self.membership_repo.get_by_tenant_and_user(tenant_id, target_user.id)
        if existing:
            raise ApiError(
                status_code=409,
                code='MEMBERSHIP_ALREADY_EXISTS',
                message='User already has a membership in this tenant.',
            )

        role = self.role_repo.get_by_name(role_name)
        if not role:
            raise ApiError(
                status_code=400,
                code='ROLE_NOT_FOUND',
                message=f"Role '{role_name}' does not exist.",
            )

        membership = self.membership_repo.create(
            tenant_id=tenant_id,
            user_id=target_user.id,
            role_name=role_name,
            status='ACTIVE',
        )

        self.audit_service.log_event(
            event_type='MEMBERSHIP_CREATED',
            payload={
                'membership_id': str(membership.id),
                'user_id': str(target_user.id),
                'email': target_user.email,
                'role': role_name,
            },
            tenant_id=tenant_id,
            actor_user_id=actor_user.id,
            entity_type='membership',
            entity_id=str(membership.id),
        )

        return membership

    def update_member(
        self,
        tenant_id: uuid.UUID,
        member_identifier: uuid.UUID,
        actor_user: User,
        actor_role_name: str | None = None,
        role_name: str | None = None,
        status: str | None = None,
    ) -> Membership:
        # 1. Look up membership strictly in the current tenant (by membership_id or user_id)
        membership = self.membership_repo.get_by_identifier_in_tenant(tenant_id, member_identifier)
        if not membership:
            raise ApiError(
                status_code=404,
                code='MEMBERSHIP_NOT_FOUND',
                message='Membership not found in the current tenant.',
            )

        # 2. Self-role modification protection
        if role_name is not None and membership.user_id == actor_user.id:
            raise ApiError(
                status_code=403,
                code='SELF_ROLE_MODIFICATION_DENIED',
                message='Cannot modify your own membership role.',
            )

        # 3. Platform role protection
        if role_name is not None and role_name in PLATFORM_ROLES:
            raise ApiError(
                status_code=403,
                code='PLATFORM_ROLE_ESCALATION_DENIED',
                message='Cannot assign platform roles through tenant membership management.',
            )

        # 4. Privilege escalation: cannot grant TENANT_OWNER via standard member update
        if (
            role_name == RoleName.TENANT_OWNER.value
            and actor_role_name != RoleName.PLATFORM_ADMIN.value
        ):
            raise ApiError(
                status_code=403,
                code='PRIVILEGE_ESCALATION_DENIED',
                message='Cannot assign TENANT_OWNER role. Tenant ownership cannot be escalated.',
            )

        # 5. TENANT_ADMIN cannot modify a TENANT_OWNER membership
        if membership.role.name == RoleName.TENANT_OWNER.value and actor_role_name not in {
            RoleName.PLATFORM_ADMIN.value,
            RoleName.TENANT_OWNER.value,
        }:
            raise ApiError(
                status_code=403,
                code='PRIVILEGE_ESCALATION_DENIED',
                message='Tenant administrators cannot modify Tenant Owner memberships.',
            )

        # 6. Tenant Owner Protection: check if demoting or deactivating the last owner
        is_owner = membership.role.name == RoleName.TENANT_OWNER.value
        demoting_owner = (
            is_owner and role_name is not None and role_name != RoleName.TENANT_OWNER.value
        )
        deactivating_owner = is_owner and status is not None and status != 'ACTIVE'

        if demoting_owner or deactivating_owner:
            owner_count = self.membership_repo.count_active_owners(tenant_id)
            if owner_count <= 1:
                raise ApiError(
                    status_code=400,
                    code='LAST_OWNER_PROTECTION',
                    message='Cannot remove or demote the last tenant owner. A tenant must always have a valid owner.',
                )

        updates = {}
        old_role = membership.role.name
        if role_name is not None and role_name != old_role:
            target_role = self.role_repo.get_by_name(role_name)
            if not target_role:
                raise ApiError(
                    status_code=400,
                    code='ROLE_NOT_FOUND',
                    message=f"Role '{role_name}' does not exist.",
                )
            updates['role_id'] = target_role.id

        old_status = membership.status
        if status is not None and status != old_status:
            valid_statuses = {'ACTIVE', 'SUSPENDED', 'INACTIVE'}
            if status not in valid_statuses:
                raise ApiError(
                    status_code=400,
                    code='INVALID_STATUS',
                    message=f'Status must be one of {valid_statuses}',
                )
            updates['status'] = status

        if updates:
            membership = self.membership_repo.update(membership, **updates)

            if 'role_id' in updates:
                self.audit_service.log_event(
                    event_type='MEMBERSHIP_ROLE_CHANGED',
                    payload={
                        'membership_id': str(membership.id),
                        'user_id': str(membership.user_id),
                        'old_role': old_role,
                        'new_role': role_name,
                    },
                    tenant_id=tenant_id,
                    actor_user_id=actor_user.id,
                    entity_type='membership',
                    entity_id=str(membership.id),
                )

            if 'status' in updates:
                event_type = (
                    'MEMBERSHIP_SUSPENDED' if status == 'SUSPENDED' else 'MEMBERSHIP_UPDATED'
                )
                self.audit_service.log_event(
                    event_type=event_type,
                    payload={
                        'membership_id': str(membership.id),
                        'user_id': str(membership.user_id),
                        'old_status': old_status,
                        'new_status': status,
                    },
                    tenant_id=tenant_id,
                    actor_user_id=actor_user.id,
                    entity_type='membership',
                    entity_id=str(membership.id),
                )

        return membership

    def remove_member(
        self,
        tenant_id: uuid.UUID,
        member_identifier: uuid.UUID,
        actor_user: User,
        actor_role_name: str | None = None,
    ) -> None:
        membership = self.membership_repo.get_by_identifier_in_tenant(tenant_id, member_identifier)
        if not membership:
            raise ApiError(
                status_code=404,
                code='MEMBERSHIP_NOT_FOUND',
                message='Membership not found in the current tenant.',
            )

        # TENANT_ADMIN cannot delete a TENANT_OWNER
        if membership.role.name == RoleName.TENANT_OWNER.value and actor_role_name not in {
            RoleName.PLATFORM_ADMIN.value,
            RoleName.TENANT_OWNER.value,
        }:
            raise ApiError(
                status_code=403,
                code='PRIVILEGE_ESCALATION_DENIED',
                message='Tenant administrators cannot remove a Tenant Owner.',
            )

        # Tenant Owner Protection
        if membership.role.name == RoleName.TENANT_OWNER.value:
            owner_count = self.membership_repo.count_active_owners(tenant_id)
            if owner_count <= 1:
                raise ApiError(
                    status_code=400,
                    code='LAST_OWNER_PROTECTION',
                    message='Cannot remove or demote the last tenant owner. A tenant must always have a valid owner.',
                )

        membership_id_str = str(membership.id)
        user_id_str = str(membership.user_id)
        role_str = membership.role.name

        self.membership_repo.delete(membership)

        self.audit_service.log_event(
            event_type='MEMBERSHIP_REMOVED',
            payload={
                'membership_id': membership_id_str,
                'user_id': user_id_str,
                'role': role_str,
            },
            tenant_id=tenant_id,
            actor_user_id=actor_user.id,
            entity_type='membership',
            entity_id=membership_id_str,
        )
