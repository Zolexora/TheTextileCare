from __future__ import annotations

import uuid
from typing import Sequence

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.marketplace import (
    MarketplaceBranchResponse,
    MarketplaceCategoryResponse,
    MarketplaceSellerResponse,
    MarketplaceServiceResponse,
)
from app.schemas.pricing import PricingCalculationRequest, PricingCalculationResult
from app.services.marketplace import MarketplaceService

router = APIRouter(tags=['marketplace'])


@router.get('/sellers', response_model=list[MarketplaceSellerResponse])
def discover_sellers(
    search: str | None = None,
    city: str | None = None,
    limit: int = 20,
    offset: int = 0,
    db: Session = Depends(get_db)
) -> Sequence[MarketplaceSellerResponse]:
    svc = MarketplaceService(db)
    return svc.discover_sellers(search=search, city=city, limit=limit, offset=offset)


@router.get('/sellers/{seller_id}', response_model=MarketplaceSellerResponse)
def get_seller_profile(
    seller_id: uuid.UUID,
    db: Session = Depends(get_db)
) -> MarketplaceSellerResponse:
    svc = MarketplaceService(db)
    return svc.get_seller_profile(seller_id)


@router.get('/sellers/{seller_id}/branches', response_model=list[MarketplaceBranchResponse])
def get_seller_branches(
    seller_id: uuid.UUID,
    db: Session = Depends(get_db)
) -> Sequence[MarketplaceBranchResponse]:
    svc = MarketplaceService(db)
    return svc.list_branches(seller_id)


@router.get('/sellers/{seller_id}/categories', response_model=list[MarketplaceCategoryResponse])
def get_catalog_categories(
    seller_id: uuid.UUID,
    db: Session = Depends(get_db)
) -> Sequence[MarketplaceCategoryResponse]:
    svc = MarketplaceService(db)
    return svc.get_catalog_categories(seller_id)


@router.get('/sellers/{seller_id}/services', response_model=list[MarketplaceServiceResponse])
def get_catalog_services(
    seller_id: uuid.UUID,
    branch_id: uuid.UUID | None = None,
    db: Session = Depends(get_db)
) -> Sequence[MarketplaceServiceResponse]:
    svc = MarketplaceService(db)
    return svc.get_catalog_services(seller_id, branch_id)


@router.get('/sellers/{seller_id}/services/{service_id}', response_model=MarketplaceServiceResponse)
def get_service_details(
    seller_id: uuid.UUID,
    service_id: uuid.UUID,
    db: Session = Depends(get_db)
) -> MarketplaceServiceResponse:
    svc = MarketplaceService(db)
    return svc.get_service_details(seller_id, service_id)


@router.post('/pricing/preview', response_model=PricingCalculationResult)
def preview_pricing(
    request: PricingCalculationRequest,
    db: Session = Depends(get_db)
) -> PricingCalculationResult:
    svc = MarketplaceService(db)
    # The request body contains seller_id and branch_id
    # We pass it to the orchestrator which handles authorization check
    return svc.preview_pricing(request.seller_id, request)
