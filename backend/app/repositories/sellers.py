from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.seller import Seller, Branch, StaffProfile, SellerSettings, BusinessHour
from app.repositories.base import BaseRepository


class SellerRepository(BaseRepository):
    def get_by_id(self, seller_id: uuid.UUID) -> Seller | None:
        return self.db.execute(select(Seller).where(Seller.id == seller_id)).scalars().first()

    def get_by_tenant_id(self, tenant_id: uuid.UUID) -> Seller | None:
        return self.db.execute(select(Seller).where(Seller.tenant_id == tenant_id)).scalars().first()

    def create(self, seller: Seller) -> Seller:
        self.db.add(seller)
        self.db.flush()
        return seller

    def update(self, seller: Seller) -> Seller:
        self.db.add(seller)
        self.db.flush()
        return seller


class BranchRepository(BaseRepository):
    def get_by_id(self, branch_id: uuid.UUID) -> Branch | None:
        return self.db.execute(select(Branch).where(Branch.id == branch_id)).scalars().first()

    def get_by_tenant_id(self, tenant_id: uuid.UUID) -> Sequence[Branch]:
        return self.db.execute(select(Branch).where(Branch.tenant_id == tenant_id)).scalars().all()

    def get_by_seller_id(self, seller_id: uuid.UUID) -> Sequence[Branch]:
        return self.db.execute(select(Branch).where(Branch.seller_id == seller_id)).scalars().all()

    def get_by_code(self, seller_id: uuid.UUID, code: str) -> Branch | None:
        return self.db.execute(
            select(Branch).where(Branch.seller_id == seller_id, Branch.code == code)
        ).scalars().first()

    def create(self, branch: Branch) -> Branch:
        self.db.add(branch)
        self.db.flush()
        return branch

    def update(self, branch: Branch) -> Branch:
        self.db.add(branch)
        self.db.flush()
        return branch


class StaffProfileRepository(BaseRepository):
    def get_by_id(self, profile_id: uuid.UUID) -> StaffProfile | None:
        return self.db.execute(select(StaffProfile).where(StaffProfile.id == profile_id)).scalars().first()

    def get_by_tenant_and_user(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> StaffProfile | None:
        return self.db.execute(
            select(StaffProfile).where(StaffProfile.tenant_id == tenant_id, StaffProfile.user_id == user_id)
        ).scalars().first()

    def get_by_tenant_id(self, tenant_id: uuid.UUID) -> Sequence[StaffProfile]:
        return self.db.execute(select(StaffProfile).where(StaffProfile.tenant_id == tenant_id)).scalars().all()

    def create(self, profile: StaffProfile) -> StaffProfile:
        self.db.add(profile)
        self.db.flush()
        return profile

    def update(self, profile: StaffProfile) -> StaffProfile:
        self.db.add(profile)
        self.db.flush()
        return profile


class SellerSettingsRepository(BaseRepository):
    def get_by_seller_id(self, seller_id: uuid.UUID) -> SellerSettings | None:
        return self.db.execute(select(SellerSettings).where(SellerSettings.seller_id == seller_id)).scalars().first()

    def create(self, settings: SellerSettings) -> SellerSettings:
        self.db.add(settings)
        self.db.flush()
        return settings

    def update(self, settings: SellerSettings) -> SellerSettings:
        self.db.add(settings)
        self.db.flush()
        return settings


class BusinessHourRepository(BaseRepository):
    def get_by_branch_id(self, branch_id: uuid.UUID) -> Sequence[BusinessHour]:
        return self.db.execute(select(BusinessHour).where(BusinessHour.branch_id == branch_id)).scalars().all()

    def get_by_branch_and_day(self, branch_id: uuid.UUID, day_of_week: int) -> BusinessHour | None:
        return self.db.execute(
            select(BusinessHour).where(BusinessHour.branch_id == branch_id, BusinessHour.day_of_week == day_of_week)
        ).scalars().first()

    def get_by_id(self, hour_id: uuid.UUID) -> BusinessHour | None:
        return self.db.execute(select(BusinessHour).where(BusinessHour.id == hour_id)).scalars().first()

    def create(self, business_hour: BusinessHour) -> BusinessHour:
        self.db.add(business_hour)
        self.db.flush()
        return business_hour

    def update(self, business_hour: BusinessHour) -> BusinessHour:
        self.db.add(business_hour)
        self.db.flush()
        return business_hour
