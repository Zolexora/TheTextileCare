from __future__ import annotations

import uuid
from typing import Sequence

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.permissions.constants import PermissionName
from app.core.tenant.context import TenantContext
from app.db import get_db
from app.dependencies import require_permission, require_scoped_tenant_context
from app.schemas.seller import (
    SellerCreate, SellerUpdate, SellerResponse,
    BranchCreate, BranchUpdate, BranchResponse,
    StaffProfileCreate, StaffProfileUpdate, StaffProfileResponse,
    SellerSettingsUpdate, SellerSettingsResponse,
    BusinessHourCreate, BusinessHourUpdate, BusinessHourResponse
)
from app.services.sellers import SellerService

router = APIRouter(prefix='/sellers', tags=['sellers'])


@router.post('', response_model=SellerResponse, status_code=status.HTTP_201_CREATED)
async def create_seller(
    data: SellerCreate,
    ctx: TenantContext = Depends(require_permission(PermissionName.SELLER_MANAGE)),
    db: Session = Depends(get_db),
) -> SellerResponse:
    seller_service = SellerService(db)
    return seller_service.create_seller(
        tenant_id=ctx.tenant.id,
        data=data.model_dump(exclude_unset=True),
        actor_user_id=ctx.user.id
    )


@router.get('', response_model=SellerResponse)
async def get_seller(
    ctx: TenantContext = Depends(require_permission(PermissionName.SELLER_READ)),
    db: Session = Depends(get_db),
) -> SellerResponse:
    seller_service = SellerService(db)
    return seller_service.get_seller_by_tenant(ctx.tenant.id)


@router.patch('', response_model=SellerResponse)
async def update_seller(
    data: SellerUpdate,
    ctx: TenantContext = Depends(require_permission(PermissionName.SELLER_MANAGE)),
    db: Session = Depends(get_db),
) -> SellerResponse:
    seller_service = SellerService(db)
    return seller_service.update_seller(
        tenant_id=ctx.tenant.id,
        data=data.model_dump(exclude_unset=True),
        actor_user_id=ctx.user.id
    )


@router.get('/branches', response_model=list[BranchResponse])
async def list_branches(
    ctx: TenantContext = Depends(require_permission(PermissionName.SELLER_BRANCHES_READ)),
    db: Session = Depends(get_db),
) -> Sequence[BranchResponse]:
    seller_service = SellerService(db)
    return seller_service.get_branches(ctx.tenant.id)


@router.post('/branches', response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
async def create_branch(
    data: BranchCreate,
    ctx: TenantContext = Depends(require_permission(PermissionName.SELLER_BRANCHES_MANAGE)),
    db: Session = Depends(get_db),
) -> BranchResponse:
    seller_service = SellerService(db)
    return seller_service.create_branch(
        tenant_id=ctx.tenant.id,
        data=data.model_dump(exclude_unset=True),
        actor_user_id=ctx.user.id
    )


@router.patch('/branches/{branch_id}', response_model=BranchResponse)
async def update_branch(
    branch_id: uuid.UUID,
    data: BranchUpdate,
    ctx: TenantContext = Depends(require_permission(PermissionName.SELLER_BRANCHES_MANAGE)),
    db: Session = Depends(get_db),
) -> BranchResponse:
    seller_service = SellerService(db)
    return seller_service.update_branch(
        tenant_id=ctx.tenant.id,
        branch_id=branch_id,
        data=data.model_dump(exclude_unset=True),
        actor_user_id=ctx.user.id
    )


@router.get('/staff', response_model=list[StaffProfileResponse])
async def list_staff(
    ctx: TenantContext = Depends(require_permission(PermissionName.SELLER_STAFF_READ)),
    db: Session = Depends(get_db),
) -> Sequence[StaffProfileResponse]:
    seller_service = SellerService(db)
    return seller_service.get_staff_profiles(ctx.tenant.id)


@router.post('/staff', response_model=StaffProfileResponse, status_code=status.HTTP_201_CREATED)
async def invite_staff(
    data: StaffProfileCreate,
    ctx: TenantContext = Depends(require_permission(PermissionName.SELLER_STAFF_MANAGE)),
    db: Session = Depends(get_db),
) -> StaffProfileResponse:
    seller_service = SellerService(db)
    return seller_service.invite_staff(
        tenant_id=ctx.tenant.id,
        data=data.model_dump(exclude_unset=True),
        actor_user_id=ctx.user.id
    )


@router.patch('/staff/{profile_id}', response_model=StaffProfileResponse)
async def update_staff(
    profile_id: uuid.UUID,
    data: StaffProfileUpdate,
    ctx: TenantContext = Depends(require_permission(PermissionName.SELLER_STAFF_MANAGE)),
    db: Session = Depends(get_db),
) -> StaffProfileResponse:
    seller_service = SellerService(db)
    return seller_service.update_staff(
        tenant_id=ctx.tenant.id,
        profile_id=profile_id,
        data=data.model_dump(exclude_unset=True),
        actor_user_id=ctx.user.id
    )


@router.delete('/staff/{profile_id}', status_code=status.HTTP_204_NO_CONTENT)
async def remove_staff(
    profile_id: uuid.UUID,
    ctx: TenantContext = Depends(require_permission(PermissionName.SELLER_STAFF_MANAGE)),
    db: Session = Depends(get_db),
) -> None:
    seller_service = SellerService(db)
    seller_service.remove_staff(
        tenant_id=ctx.tenant.id,
        profile_id=profile_id,
        actor_user_id=ctx.user.id
    )


@router.get('/settings', response_model=SellerSettingsResponse)
async def get_settings(
    ctx: TenantContext = Depends(require_permission(PermissionName.SELLER_SETTINGS_READ)),
    db: Session = Depends(get_db),
) -> SellerSettingsResponse:
    seller_service = SellerService(db)
    return seller_service.get_settings(ctx.tenant.id)


@router.patch('/settings', response_model=SellerSettingsResponse)
async def update_settings(
    data: SellerSettingsUpdate,
    ctx: TenantContext = Depends(require_permission(PermissionName.SELLER_SETTINGS_MANAGE)),
    db: Session = Depends(get_db),
) -> SellerSettingsResponse:
    seller_service = SellerService(db)
    return seller_service.update_settings(
        tenant_id=ctx.tenant.id,
        data=data.model_dump(exclude_unset=True),
        actor_user_id=ctx.user.id
    )

@router.get('/branches/{branch_id}/business-hours', response_model=list[BusinessHourResponse])
async def get_business_hours(
    branch_id: uuid.UUID,
    ctx: TenantContext = Depends(require_permission(PermissionName.SELLER_SETTINGS_READ)),
    db: Session = Depends(get_db),
) -> Sequence[BusinessHourResponse]:
    seller_service = SellerService(db)
    return seller_service.get_business_hours(ctx.tenant.id, branch_id)

@router.post('/branches/{branch_id}/business-hours', response_model=BusinessHourResponse)
async def set_business_hour(
    branch_id: uuid.UUID,
    data: BusinessHourCreate,
    ctx: TenantContext = Depends(require_permission(PermissionName.SELLER_SETTINGS_MANAGE)),
    db: Session = Depends(get_db),
) -> BusinessHourResponse:
    seller_service = SellerService(db)
    return seller_service.set_business_hour(
        tenant_id=ctx.tenant.id,
        branch_id=branch_id,
        data=data.model_dump(exclude_unset=True),
        actor_user_id=ctx.user.id
    )
