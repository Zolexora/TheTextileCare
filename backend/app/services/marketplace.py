from __future__ import annotations

import uuid
from typing import Sequence
from decimal import Decimal

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.seller import Seller, Branch
from app.models.catalog import Catalog, Category, Service
from app.repositories.marketplace import MarketplaceRepository
from app.services.pricing import PricingService
from app.schemas.pricing import PricingCalculationRequest, PricingCalculationResult


class MarketplaceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = MarketplaceRepository(db)
        self.pricing_service = PricingService(db)

    def _ensure_seller(self, seller_id: uuid.UUID) -> Seller:
        seller = self.repo.get_published_seller(seller_id)
        if not seller:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seller not found or not published")
        return seller

    def _ensure_branch(self, seller_id: uuid.UUID, branch_id: uuid.UUID) -> Branch:
        branch = self.repo.get_published_branch(seller_id, branch_id)
        if not branch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found or not published")
        return branch

    def _ensure_catalog(self, seller_id: uuid.UUID) -> Catalog:
        catalog = self.repo.get_active_catalog(seller_id)
        if not catalog:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seller has no active catalog")
        return catalog

    def discover_sellers(self, search: str | None = None, city: str | None = None, limit: int = 20, offset: int = 0) -> Sequence[Seller]:
        return self.repo.list_published_sellers(search=search, city=city, limit=limit, offset=offset)

    def get_seller_profile(self, seller_id: uuid.UUID) -> Seller:
        return self._ensure_seller(seller_id)

    def list_branches(self, seller_id: uuid.UUID) -> Sequence[Branch]:
        self._ensure_seller(seller_id)
        return self.repo.list_published_branches(seller_id)

    def get_catalog_categories(self, seller_id: uuid.UUID) -> Sequence[Category]:
        self._ensure_seller(seller_id)
        catalog = self._ensure_catalog(seller_id)
        return self.repo.list_active_categories(catalog.id)

    def get_catalog_services(self, seller_id: uuid.UUID, branch_id: uuid.UUID | None = None) -> Sequence[Service]:
        self._ensure_seller(seller_id)
        if branch_id:
            self._ensure_branch(seller_id, branch_id)
            
        catalog = self._ensure_catalog(seller_id)
        return self.repo.list_active_services(catalog.id, branch_id)

    def get_service_details(self, seller_id: uuid.UUID, service_id: uuid.UUID) -> Service:
        self._ensure_seller(seller_id)
        catalog = self._ensure_catalog(seller_id)
        service = self.repo.get_active_service(catalog.id, service_id)
        if not service:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found or not active")
        return service

    def preview_pricing(
        self,
        seller_id: uuid.UUID,
        request: PricingCalculationRequest
    ) -> PricingCalculationResult:
        """
        Orchestrate pricing preview.
        Validates all public eligibility before invoking the core Pricing Engine.
        """
        seller = self._ensure_seller(seller_id)
        catalog = self._ensure_catalog(seller_id)
        
        if request.branch_id:
            self._ensure_branch(seller_id, request.branch_id)
            
        # Validate that all requested services and items are active and belong to this catalog
        for req_item in request.items:
            svc = self.repo.get_active_service(catalog.id, req_item.service_id)
            if not svc:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
                    detail=f"Service {req_item.service_id} is invalid or inactive"
                )
                
            if req_item.service_item_id:
                valid_items = {i.id for i in svc.items}
                if req_item.service_item_id not in valid_items:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
                        detail=f"Service item {req_item.service_item_id} is invalid or inactive"
                    )
                    
            if req_item.addon_ids:
                valid_addons = {a.id for a in svc.addons}
                for aid in req_item.addon_ids:
                    if aid not in valid_addons:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, 
                            detail=f"Addon {aid} is invalid or inactive"
                        )
        
        # If everything is public and valid, we can delegate to the Phase 5 engine!
        # The PricingService uses tenant_id for its lookups. We get it from the seller.
        return self.pricing_service.calculate(
            tenant_id=seller.tenant_id,
            request=request
        )
