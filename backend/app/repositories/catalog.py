import uuid
from typing import Sequence
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.catalog import Catalog, Category, Service, ServiceItem, ServiceAddon

class CatalogRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID) -> Catalog | None:
        stmt = select(Catalog).where(
            Catalog.id == catalog_id,
            Catalog.tenant_id == tenant_id
        )
        return self.db.execute(stmt).scalar_one_or_none()
        
    def get_by_seller(self, tenant_id: uuid.UUID, seller_id: uuid.UUID) -> Sequence[Catalog]:
        stmt = select(Catalog).where(
            Catalog.seller_id == seller_id,
            Catalog.tenant_id == tenant_id
        ).order_by(Catalog.created_at.desc())
        return self.db.execute(stmt).scalars().all()

    def create(self, catalog: Catalog) -> Catalog:
        self.db.add(catalog)
        self.db.flush()
        return catalog


class CategoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, tenant_id: uuid.UUID, category_id: uuid.UUID) -> Category | None:
        stmt = select(Category).where(
            Category.id == category_id,
            Category.tenant_id == tenant_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_catalog(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID) -> Sequence[Category]:
        stmt = select(Category).where(
            Category.catalog_id == catalog_id,
            Category.tenant_id == tenant_id
        ).order_by(Category.sort_order.asc(), Category.name.asc())
        return self.db.execute(stmt).scalars().all()

    def create(self, category: Category) -> Category:
        self.db.add(category)
        self.db.flush()
        return category


class ServiceRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, tenant_id: uuid.UUID, service_id: uuid.UUID) -> Service | None:
        stmt = select(Service).where(
            Service.id == service_id,
            Service.tenant_id == tenant_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_catalog(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID) -> Sequence[Service]:
        stmt = select(Service).where(
            Service.catalog_id == catalog_id,
            Service.tenant_id == tenant_id
        ).order_by(Service.sort_order.asc(), Service.name.asc())
        return self.db.execute(stmt).scalars().all()

    def create(self, service: Service) -> Service:
        self.db.add(service)
        self.db.flush()
        return service


class ServiceItemRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, tenant_id: uuid.UUID, item_id: uuid.UUID) -> ServiceItem | None:
        stmt = select(ServiceItem).where(
            ServiceItem.id == item_id,
            ServiceItem.tenant_id == tenant_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_service(self, tenant_id: uuid.UUID, service_id: uuid.UUID) -> Sequence[ServiceItem]:
        stmt = select(ServiceItem).where(
            ServiceItem.service_id == service_id,
            ServiceItem.tenant_id == tenant_id
        ).order_by(ServiceItem.sort_order.asc(), ServiceItem.name.asc())
        return self.db.execute(stmt).scalars().all()

    def create(self, item: ServiceItem) -> ServiceItem:
        self.db.add(item)
        self.db.flush()
        return item


class ServiceAddonRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, tenant_id: uuid.UUID, addon_id: uuid.UUID) -> ServiceAddon | None:
        stmt = select(ServiceAddon).where(
            ServiceAddon.id == addon_id,
            ServiceAddon.tenant_id == tenant_id
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_service(self, tenant_id: uuid.UUID, service_id: uuid.UUID) -> Sequence[ServiceAddon]:
        stmt = select(ServiceAddon).where(
            ServiceAddon.service_id == service_id,
            ServiceAddon.tenant_id == tenant_id
        ).order_by(ServiceAddon.sort_order.asc(), ServiceAddon.name.asc())
        return self.db.execute(stmt).scalars().all()

    def create(self, addon: ServiceAddon) -> ServiceAddon:
        self.db.add(addon)
        self.db.flush()
        return addon
