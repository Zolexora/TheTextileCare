"""Phase 7 — Commercial Configuration API endpoints.

Seller routes  : GET/PUT /api/v1/seller/commercial/config
Admin routes   : POST /api/v1/seller/commercial/admin/evaluate-restriction/{seller_id}
"""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.permissions.constants import PermissionName
from app.dependencies import get_db, require_permission
from app.core.tenant.context import TenantContext
from app.schemas.commercial import (
    CommercialConfigResponse,
    CommercialConfigUpdate,
    SellerRestrictionEvaluationResponse,
)
from app.services.commercial import CommercialService

router = APIRouter(tags=["commercial"])

def _get_seller_id(ctx: TenantContext, db: Session) -> uuid.UUID:
    from sqlalchemy import select
    from app.models.seller import Seller
    seller = db.execute(select(Seller).where(Seller.tenant_id == ctx.tenant_id)).scalar_one_or_none()
    if not seller:
        raise ApiError(status_code=404, code="SELLER_NOT_FOUND", message="No seller found for this tenant.")
    return seller.id



@router.get("/config", response_model=CommercialConfigResponse)
def get_commercial_config(
    ctx: TenantContext = Depends(require_permission(PermissionName.COMMERCIAL_READ.value)),
    db: Session = Depends(get_db),
) -> CommercialConfigResponse:
    """Return the seller's commercial configuration (creates defaults if absent)."""
    svc = CommercialService(db)
    config = svc.get_or_create_commercial_config(
        seller_id=_get_seller_id(ctx, db),
        tenant_id=ctx.tenant_id,
    )
    return CommercialConfigResponse.model_validate(config)


@router.put("/config", response_model=CommercialConfigResponse)
def update_commercial_config(
    request: CommercialConfigUpdate,
    ctx: TenantContext = Depends(require_permission(PermissionName.COMMERCIAL_MANAGE.value)),
    db: Session = Depends(get_db),
) -> CommercialConfigResponse:
    """Update the seller's commercial configuration."""
    svc = CommercialService(db)
    config = svc.update_commercial_config(
        seller_id=_get_seller_id(ctx, db),
        tenant_id=ctx.tenant_id,
        update_data=request,
    )
    return CommercialConfigResponse.model_validate(config)


@router.post(
    "/admin/evaluate-restriction/{seller_id}",
    response_model=SellerRestrictionEvaluationResponse,
)
def evaluate_seller_restriction(
    seller_id: uuid.UUID,
    as_of_date: date | None = Query(default=None),
    ctx: TenantContext = Depends(require_permission(PermissionName.COMMERCIAL_MANAGE.value)),
    db: Session = Depends(get_db),
) -> SellerRestrictionEvaluationResponse:
    """Platform admin: evaluate and apply restriction level for a specific seller."""
    svc = CommercialService(db)
    return svc.evaluate_seller_restriction(seller_id=seller_id, as_of_date=as_of_date)
