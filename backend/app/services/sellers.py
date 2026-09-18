from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy.orm import Session

from app.core.exceptions.base import ApiError
from app.models.seller import Seller, Branch, StaffProfile, SellerSettings, BusinessHour
from app.repositories.sellers import SellerRepository, BranchRepository, StaffProfileRepository, SellerSettingsRepository, BusinessHourRepository
from app.repositories.memberships import MembershipRepository
from app.services.audit import AuditService


class SellerService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.seller_repo = SellerRepository(db)
        self.branch_repo = BranchRepository(db)
        self.staff_repo = StaffProfileRepository(db)
        self.settings_repo = SellerSettingsRepository(db)
        self.hours_repo = BusinessHourRepository(db)
        self.membership_repo = MembershipRepository(db)
        self.audit_service = AuditService(db)

    def get_seller_by_tenant(self, tenant_id: uuid.UUID) -> Seller:
        seller = self.seller_repo.get_by_tenant_id(tenant_id)
        if not seller:
            raise ApiError(code='SELLER_NOT_FOUND', message='Seller not found for this tenant.', status_code=404)
        return seller

    def create_seller(self, tenant_id: uuid.UUID, data: dict, actor_user_id: uuid.UUID) -> Seller:
        if self.seller_repo.get_by_tenant_id(tenant_id):
            raise ApiError(code='SELLER_EXISTS', message='Seller already exists for this tenant.', status_code=400)
            
        seller = Seller(tenant_id=tenant_id, status='PENDING', **data)
        self.seller_repo.create(seller)

        settings = SellerSettings(seller_id=seller.id)
        self.settings_repo.create(settings)

        self.audit_service.log_event(
            event_type='SELLER_CREATED',
            payload={'seller_id': str(seller.id), 'business_name': data.get('business_name')},
            actor_user_id=actor_user_id,
            tenant_id=tenant_id
        )
        return seller

    def update_seller(self, tenant_id: uuid.UUID, data: dict, actor_user_id: uuid.UUID) -> Seller:
        seller = self.get_seller_by_tenant(tenant_id)
        
        changes = {}
        for key, value in data.items():
            if value is not None and getattr(seller, key) != value:
                changes[f'new_{key}'] = value
                setattr(seller, key, value)
            
        if changes:
            self.seller_repo.update(seller)
            event_type = 'SELLER_STATUS_CHANGED' if 'new_status' in changes else 'SELLER_UPDATED'
            self.audit_service.log_event(
                event_type=event_type,
                payload={'seller_id': str(seller.id), **changes},
                actor_user_id=actor_user_id,
                tenant_id=tenant_id
            )
            
        return seller

    def get_branches(self, tenant_id: uuid.UUID) -> Sequence[Branch]:
        return self.branch_repo.get_by_tenant_id(tenant_id)

    def get_branch(self, tenant_id: uuid.UUID, branch_id: uuid.UUID) -> Branch:
        branch = self.branch_repo.get_by_id(branch_id)
        if not branch or branch.tenant_id != tenant_id:
            raise ApiError(code='BRANCH_NOT_FOUND', message='Branch not found.', status_code=404)
        return branch

    def create_branch(self, tenant_id: uuid.UUID, data: dict, actor_user_id: uuid.UUID) -> Branch:
        seller = self.get_seller_by_tenant(tenant_id)
        if self.branch_repo.get_by_code(seller.id, data['code']):
            raise ApiError(code='BRANCH_CODE_EXISTS', message='Branch with this code already exists.', status_code=400)
            
        branch = Branch(tenant_id=tenant_id, seller_id=seller.id, status='ACTIVE', **data)
        self.branch_repo.create(branch)
        
        self.audit_service.log_event(
            event_type='BRANCH_CREATED',
            payload={'branch_id': str(branch.id), 'code': data['code']},
            actor_user_id=actor_user_id,
            tenant_id=tenant_id
        )
        return branch

    def update_branch(self, tenant_id: uuid.UUID, branch_id: uuid.UUID, data: dict, actor_user_id: uuid.UUID) -> Branch:
        branch = self.get_branch(tenant_id, branch_id)
        
        changes = {}
        for key, value in data.items():
            if value is not None and getattr(branch, key) != value:
                changes[f'new_{key}'] = value
                setattr(branch, key, value)
            
        if changes:
            self.branch_repo.update(branch)
            event_type = 'BRANCH_STATUS_CHANGED' if 'new_status' in changes else 'BRANCH_UPDATED'
            self.audit_service.log_event(
                event_type=event_type,
                payload={'branch_id': str(branch.id), **changes},
                actor_user_id=actor_user_id,
                tenant_id=tenant_id
            )
            
        return branch

    def get_staff_profiles(self, tenant_id: uuid.UUID) -> Sequence[StaffProfile]:
        return self.staff_repo.get_by_tenant_id(tenant_id)

    def invite_staff(self, tenant_id: uuid.UUID, data: dict, actor_user_id: uuid.UUID) -> StaffProfile:
        seller = self.seller_repo.get_by_tenant_id(tenant_id)
        # Even if seller doesn't exist, we can attach staff to tenant? The spec said "A staff profile must reference an existing platform user. UNIQUE(tenant_id, user_id)". Let's bind to tenant and optionally seller.
        seller_id = seller.id if seller else None
        
        user_id = data['user_id']
        membership = self.membership_repo.get_by_tenant_and_user(tenant_id=tenant_id, user_id=user_id)
        if not membership:
            raise ApiError(code='USER_NOT_IN_TENANT', message='User must be a member of the tenant to be added as staff.', status_code=400)
            
        if self.staff_repo.get_by_tenant_and_user(tenant_id, user_id):
            raise ApiError(code='STAFF_EXISTS', message='User is already staff.', status_code=400)
            
        profile = StaffProfile(tenant_id=tenant_id, seller_id=seller_id, user_id=user_id, status='ACTIVE', employee_code=data.get('employee_code'), display_name=data.get('display_name'), phone=data.get('phone'))
        self.staff_repo.create(profile)
        
        self.audit_service.log_event(
            event_type='STAFF_INVITED',
            payload={'staff_profile_id': str(profile.id), 'user_id': str(user_id)},
            actor_user_id=actor_user_id,
            tenant_id=tenant_id
        )
        return profile

    def update_staff(self, tenant_id: uuid.UUID, profile_id: uuid.UUID, data: dict, actor_user_id: uuid.UUID) -> StaffProfile:
        profile = self.staff_repo.get_by_id(profile_id)
        if not profile or profile.tenant_id != tenant_id:
            raise ApiError(code='STAFF_NOT_FOUND', message='Staff profile not found.', status_code=404)
            
        changes = {}
        for key, value in data.items():
            if value is not None and getattr(profile, key) != value:
                changes[f'new_{key}'] = value
                setattr(profile, key, value)
            
        if changes:
            self.staff_repo.update(profile)
            event_type = 'STAFF_UPDATED'
            if 'new_status' in changes and data.get('status') == 'SUSPENDED':
                event_type = 'STAFF_SUSPENDED'
                
            self.audit_service.log_event(
                event_type=event_type,
                payload={'staff_profile_id': str(profile.id), **changes},
                actor_user_id=actor_user_id,
                tenant_id=tenant_id
            )
            
        return profile

    def remove_staff(self, tenant_id: uuid.UUID, profile_id: uuid.UUID, actor_user_id: uuid.UUID) -> None:
        profile = self.staff_repo.get_by_id(profile_id)
        if not profile or profile.tenant_id != tenant_id:
            raise ApiError(code='STAFF_NOT_FOUND', message='Staff profile not found.', status_code=404)
            
        profile_id_str = str(profile.id)
        user_id_str = str(profile.user_id)
        self.db.delete(profile)
        self.db.flush()
        
        self.audit_service.log_event(
            event_type='STAFF_REMOVED',
            payload={'staff_profile_id': profile_id_str, 'user_id': user_id_str},
            actor_user_id=actor_user_id,
            tenant_id=tenant_id
        )

    def get_settings(self, tenant_id: uuid.UUID) -> SellerSettings:
        seller = self.get_seller_by_tenant(tenant_id)
        settings = self.settings_repo.get_by_seller_id(seller.id)
        if not settings:
            settings = SellerSettings(seller_id=seller.id)
            self.settings_repo.create(settings)
        return settings

    def update_settings(self, tenant_id: uuid.UUID, data: dict, actor_user_id: uuid.UUID) -> SellerSettings:
        settings = self.get_settings(tenant_id)
        
        changes = {}
        for key, value in data.items():
            if value is not None and getattr(settings, key) != value:
                changes[f'new_{key}'] = value
                setattr(settings, key, value)
            
        if changes:
            self.settings_repo.update(settings)
            self.audit_service.log_event(
                event_type='SELLER_SETTINGS_UPDATED',
                payload={'seller_id': str(settings.seller_id), **changes},
                actor_user_id=actor_user_id,
                tenant_id=tenant_id
            )
            
        return settings

    def get_business_hours(self, tenant_id: uuid.UUID, branch_id: uuid.UUID) -> Sequence[BusinessHour]:
        branch = self.get_branch(tenant_id, branch_id)
        return self.hours_repo.get_by_branch_id(branch.id)

    def set_business_hour(self, tenant_id: uuid.UUID, branch_id: uuid.UUID, data: dict, actor_user_id: uuid.UUID) -> BusinessHour:
        branch = self.get_branch(tenant_id, branch_id)
        
        hour = self.hours_repo.get_by_branch_and_day(branch.id, data['day_of_week'])
        if hour:
            for key, value in data.items():
                if value is not None:
                    setattr(hour, key, value)
            self.hours_repo.update(hour)
        else:
            hour = BusinessHour(tenant_id=tenant_id, branch_id=branch.id, **data)
            self.hours_repo.create(hour)
            
        self.audit_service.log_event(
            event_type='BUSINESS_HOUR_UPDATED',
            payload={'branch_id': str(branch.id), 'day_of_week': data['day_of_week']},
            actor_user_id=actor_user_id,
            tenant_id=tenant_id
        )
        return hour
