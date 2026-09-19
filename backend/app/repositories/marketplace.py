from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.seller import Seller, Branch
from app.models.catalog import Catalog, Category, Service, ServiceItem, ServiceAddon, ServiceBranchAvailability
from app.repositories.base import BaseRepository


class MarketplaceRepository(BaseRepository):
    """Read-only discovery queries for the customer-facing marketplace."""

    def list_published_sellers(
        self,
        search: str | None = None,
        city: str | None = None,
        limit: int = 20,
        offset: int = 0
    ) -> Sequence[Seller]:
        """Discover active published sellers, optionally filtered."""
        stmt = select(Seller).where(
            Seller.marketplace_status == 'PUBLISHED',
            Seller.status == 'ACTIVE'
        )

        if search:
            # Simple ILIKE search for Phase 6
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Seller.display_name.ilike(search_term),
                    Seller.business_name.ilike(search_term),
                    Seller.description.ilike(search_term)
                )
            )
            
        if city:
            # Join with Branch to filter by city
            stmt = stmt.join(Branch, Seller.id == Branch.seller_id).where(
                Branch.city.ilike(f"%{city}%"),
                Branch.is_marketplace_visible == True,
                Branch.status == 'ACTIVE'
            )

        stmt = stmt.order_by(Seller.display_name.asc(), Seller.id.asc())
        stmt = stmt.limit(limit).offset(offset)
        return self.db.execute(stmt).scalars().unique().all()
        
    def get_published_seller(self, seller_id: uuid.UUID) -> Seller | None:
        stmt = select(Seller).where(
            Seller.id == seller_id,
            Seller.marketplace_status == 'PUBLISHED',
            Seller.status == 'ACTIVE'
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_published_branches(self, seller_id: uuid.UUID) -> Sequence[Branch]:
        """List active, marketplace-visible branches for a seller."""
        stmt = select(Branch).where(
            Branch.seller_id == seller_id,
            Branch.is_marketplace_visible == True,
            Branch.status == 'ACTIVE'
        ).order_by(Branch.name.asc(), Branch.id.asc())
        return self.db.execute(stmt).scalars().all()
        
    def get_published_branch(self, seller_id: uuid.UUID, branch_id: uuid.UUID) -> Branch | None:
        stmt = select(Branch).where(
            Branch.id == branch_id,
            Branch.seller_id == seller_id,
            Branch.is_marketplace_visible == True,
            Branch.status == 'ACTIVE'
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_active_catalog(self, seller_id: uuid.UUID) -> Catalog | None:
        """Get the active catalog for a seller."""
        # For Phase 6, we assume at most 1 active catalog per seller
        stmt = select(Catalog).where(
            Catalog.seller_id == seller_id,
            Catalog.status == 'ACTIVE'
        )
        return self.db.execute(stmt).scalar_one_or_none()
        
    def list_active_categories(self, catalog_id: uuid.UUID) -> Sequence[Category]:
        stmt = select(Category).where(
            Category.catalog_id == catalog_id,
            Category.status == 'ACTIVE'
        ).order_by(Category.sort_order.asc(), Category.name.asc())
        return self.db.execute(stmt).scalars().all()
        
    def list_active_services(self, catalog_id: uuid.UUID, branch_id: uuid.UUID | None = None) -> Sequence[Service]:
        """List active services in the catalog, optionally filtered by branch availability."""
        stmt = select(Service).where(
            Service.catalog_id == catalog_id,
            Service.status == 'ACTIVE'
        )
        
        if branch_id:
            # Ensure it is available at this branch
            stmt = stmt.join(
                ServiceBranchAvailability,
                Service.id == ServiceBranchAvailability.service_id
            ).where(
                ServiceBranchAvailability.branch_id == branch_id,
                ServiceBranchAvailability.is_available == True
            )
            
        stmt = stmt.options(selectinload(Service.items), selectinload(Service.addons))
        stmt = stmt.order_by(Service.sort_order.asc(), Service.name.asc())
        
        services = self.db.execute(stmt).scalars().all()
        
        # Filter active items and addons manually since selectinload fetches all
        for svc in services:
            svc.items = [i for i in svc.items if i.status == 'ACTIVE']
            svc.addons = [a for a in svc.addons if a.status == 'ACTIVE']
            
        return services

    def get_active_service(self, catalog_id: uuid.UUID, service_id: uuid.UUID) -> Service | None:
        stmt = select(Service).where(
            Service.id == service_id,
            Service.catalog_id == catalog_id,
            Service.status == 'ACTIVE'
        ).options(selectinload(Service.items), selectinload(Service.addons))
        svc = self.db.execute(stmt).scalar_one_or_none()
        
        if svc:
            svc.items = [i for i in svc.items if i.status == 'ACTIVE']
            svc.addons = [a for a in svc.addons if a.status == 'ACTIVE']
            
        return svc
