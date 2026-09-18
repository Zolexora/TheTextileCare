from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy.orm import Session

from app.core.exceptions.base import ApiError
from app.models.seller import Seller, Branch, StaffProfile, SellerSettings
from app.repositories.sellers import SellerRepository, BranchRepository, StaffProfileRepository, SellerSettingsRepository
from app.repositories.memberships import MembershipRepository
from app.services.audit import AuditService


class SellerService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.seller_repo = SellerRepository(db)
        self.branch_repo = BranchRepository(db)
        self.staff_repo = StaffProfileRepository(db)
        self.settings_repo = SellerSettingsRepository(db)
        self.membership_repo = MembershipRepository(db)
        self.audit_service = AuditService(db)

    def get_seller_by_tenant(self, tenant_id: uuid.UUID) -> Seller:
        seller = self.seller_repo.get_by_tenant_id(tenant_id)
        if not seller:
            raise ApiError(code='SELLER_NOT_FOUND', message='Seller not found for this tenant.', status_code=404)
        return seller

    def create_seller(self, tenant_id: uuid.UUID, name: str, actor_id: uuid.UUID) -> Seller:
        if self.seller_repo.get_by_tenant_id(tenant_id):
            raise ApiError(code='SELLER_EXISTS', message='Seller already exists for this tenant.', status_code=400)
            
        seller = Seller(tenant_id=tenant_id, name=name, status='ACTIVE')
        self.seller_repo.create(seller)

        settings = SellerSettings(seller_id=seller.id, currency='USD')
        self.settings_repo.create(settings)

        self.audit_service.log_event(
            event_type='SELLER_CREATED',
            payload={'seller_id': str(seller.id), 'name': name},
            actor_user_id=actor_id,
            tenant_id=tenant_id
        )
        return seller

    def update_seller(self, tenant_id: uuid.UUID, name: str | None, status: str | None, actor_id: uuid.UUID) -> Seller:
        seller = self.get_seller_by_tenant(tenant_id)
        
        changes = {}
        if name and seller.name != name:
            changes['old_name'] = seller.name
            changes['new_name'] = name
            seller.name = name
            
        if status and seller.status != status:
            changes['old_status'] = seller.status
            changes['new_status'] = status
            seller.status = status
            
        if changes:
            self.seller_repo.update(seller)
            event_type = 'SELLER_STATUS_CHANGED' if 'new_status' in changes else 'SELLER_UPDATED'
            self.audit_service.log_event(
                event_type=event_type,
                payload={'seller_id': str(seller.id), **changes},
                actor_user_id=actor_id,
                tenant_id=tenant_id
            )
            
        return seller

    def get_branches(self, tenant_id: uuid.UUID) -> Sequence[Branch]:
        seller = self.get_seller_by_tenant(tenant_id)
        return self.branch_repo.get_by_seller_id(seller.id)

    def get_branch(self, tenant_id: uuid.UUID, branch_id: uuid.UUID) -> Branch:
        seller = self.get_seller_by_tenant(tenant_id)
        branch = self.branch_repo.get_by_id(branch_id)
        if not branch or branch.seller_id != seller.id:
            raise ApiError(code='BRANCH_NOT_FOUND', message='Branch not found.', status_code=404)
        return branch

    def create_branch(self, tenant_id: uuid.UUID, name: str, code: str, timezone: str, actor_id: uuid.UUID) -> Branch:
        seller = self.get_seller_by_tenant(tenant_id)
        if self.branch_repo.get_by_code(seller.id, code):
            raise ApiError(code='BRANCH_CODE_EXISTS', message='Branch with this code already exists.', status_code=400)
            
        branch = Branch(seller_id=seller.id, name=name, code=code, timezone=timezone, status='ACTIVE')
        self.branch_repo.create(branch)
        
        self.audit_service.log_event(
            event_type='BRANCH_CREATED',
            payload={'branch_id': str(branch.id), 'code': code},
            actor_user_id=actor_id,
            tenant_id=tenant_id
        )
        return branch

    def update_branch(self, tenant_id: uuid.UUID, branch_id: uuid.UUID, name: str | None, status: str | None, timezone: str | None, actor_id: uuid.UUID) -> Branch:
        branch = self.get_branch(tenant_id, branch_id)
        
        changes = {}
        if name and branch.name != name:
            changes['new_name'] = name
            branch.name = name
        if status and branch.status != status:
            changes['new_status'] = status
            branch.status = status
        if timezone and branch.timezone != timezone:
            changes['new_timezone'] = timezone
            branch.timezone = timezone
            
        if changes:
            self.branch_repo.update(branch)
            event_type = 'BRANCH_STATUS_CHANGED' if 'new_status' in changes else 'BRANCH_UPDATED'
            self.audit_service.log_event(
                event_type=event_type,
                payload={'branch_id': str(branch.id), **changes},
                actor_user_id=actor_id,
                tenant_id=tenant_id
            )
            
        return branch

    def get_staff_profiles(self, tenant_id: uuid.UUID) -> Sequence[StaffProfile]:
        seller = self.get_seller_by_tenant(tenant_id)
        return self.staff_repo.get_by_seller_id(seller.id)

    def invite_staff(self, tenant_id: uuid.UUID, user_id: uuid.UUID, job_title: str | None, actor_id: uuid.UUID) -> StaffProfile:
        seller = self.get_seller_by_tenant(tenant_id)
        
        # Verify user is in tenant
        membership = self.membership_repo.get_by_tenant_and_user(tenant_id=tenant_id, user_id=user_id)
        if not membership:
            raise ApiError(code='USER_NOT_IN_TENANT', message='User must be a member of the tenant to be added as staff.', status_code=400)
            
        if self.staff_repo.get_by_seller_and_user(seller.id, user_id):
            raise ApiError(code='STAFF_EXISTS', message='User is already staff.', status_code=400)
            
        profile = StaffProfile(seller_id=seller.id, user_id=user_id, job_title=job_title, status='ACTIVE')
        self.staff_repo.create(profile)
        
        self.audit_service.log_event(
            event_type='STAFF_INVITED',
            payload={'staff_profile_id': str(profile.id), 'user_id': str(user_id)},
            actor_user_id=actor_id,
            tenant_id=tenant_id
        )
        return profile

    def update_staff(self, tenant_id: uuid.UUID, profile_id: uuid.UUID, job_title: str | None, status: str | None, actor_id: uuid.UUID) -> StaffProfile:
        seller = self.get_seller_by_tenant(tenant_id)
        profile = self.staff_repo.get_by_id(profile_id)
        if not profile or profile.seller_id != seller.id:
            raise ApiError(code='STAFF_NOT_FOUND', message='Staff profile not found.', status_code=404)
            
        changes = {}
        if job_title and profile.job_title != job_title:
            changes['new_job_title'] = job_title
            profile.job_title = job_title
        if status and profile.status != status:
            changes['new_status'] = status
            profile.status = status
            
        if changes:
            self.staff_repo.update(profile)
            event_type = 'STAFF_SUSPENDED' if status == 'SUSPENDED' else 'STAFF_ROLE_CHANGED'
            # (Note: actually it could be STAFF_UPDATED, but the prompt says STAFF_ROLE_CHANGED and STAFF_SUSPENDED, I'll log based on that)
            if 'new_status' in changes and status == 'SUSPENDED':
                event_type = 'STAFF_SUSPENDED'
            elif 'new_job_title' in changes:
                event_type = 'STAFF_ROLE_CHANGED'
            else:
                event_type = 'STAFF_ROLE_CHANGED'
                
            self.audit_service.log_event(
                event_type=event_type,
                payload={'staff_profile_id': str(profile.id), **changes},
                actor_user_id=actor_id,
                tenant_id=tenant_id
            )
            
        return profile

    def remove_staff(self, tenant_id: uuid.UUID, profile_id: uuid.UUID, actor_id: uuid.UUID) -> None:
        seller = self.get_seller_by_tenant(tenant_id)
        profile = self.staff_repo.get_by_id(profile_id)
        if not profile or profile.seller_id != seller.id:
            raise ApiError(code='STAFF_NOT_FOUND', message='Staff profile not found.', status_code=404)
            
        # In a real app we might delete or soft-delete. Let's delete.
        profile_id_str = str(profile.id)
        user_id_str = str(profile.user_id)
        self.db.delete(profile)
        self.db.flush()
        
        self.audit_service.log_event(
            event_type='STAFF_REMOVED',
            payload={'staff_profile_id': profile_id_str, 'user_id': user_id_str},
            actor_user_id=actor_id,
            tenant_id=tenant_id
        )

    def get_settings(self, tenant_id: uuid.UUID) -> SellerSettings:
        seller = self.get_seller_by_tenant(tenant_id)
        settings = self.settings_repo.get_by_seller_id(seller.id)
        if not settings:
            # Should exist from seller creation, but just in case
            settings = SellerSettings(seller_id=seller.id, currency='USD')
            self.settings_repo.create(settings)
        return settings

    def update_settings(self, tenant_id: uuid.UUID, currency: str | None, tax_rate: float | None, business_hours: dict | None, actor_id: uuid.UUID) -> SellerSettings:
        settings = self.get_settings(tenant_id)
        
        changes = {}
        if currency and settings.currency != currency:
            changes['new_currency'] = currency
            settings.currency = currency
        if tax_rate is not None and settings.tax_rate != tax_rate:
            changes['new_tax_rate'] = tax_rate
            settings.tax_rate = tax_rate
        if business_hours is not None:
            changes['business_hours_updated'] = True
            settings.business_hours = business_hours
            
        if changes:
            self.settings_repo.update(settings)
            self.audit_service.log_event(
                event_type='SELLER_SETTINGS_UPDATED',
                payload={'seller_id': str(settings.seller_id), **changes},
                actor_user_id=actor_id,
                tenant_id=tenant_id
            )
            
        return settings
