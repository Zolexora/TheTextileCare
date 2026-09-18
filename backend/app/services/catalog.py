import uuid
from typing import Sequence
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.catalog import Catalog, Category, Service, ServiceItem, ServiceAddon
from app.models.seller import Seller
from app.repositories.catalog import (
    CatalogRepository,
    CategoryRepository,
    ServiceRepository,
    ServiceItemRepository,
    ServiceAddonRepository
)
from app.schemas.catalog import (
    CatalogCreate, CatalogUpdate,
    CategoryCreate, CategoryUpdate,
    ServiceCreate, ServiceUpdate,
    ServiceItemCreate, ServiceItemUpdate,
    ServiceAddonCreate, ServiceAddonUpdate
)
from app.services.audit import AuditService

class CatalogService:
    def __init__(self, db: Session):
        self.db = db
        self.catalog_repo = CatalogRepository(db)
        self.category_repo = CategoryRepository(db)
        self.service_repo = ServiceRepository(db)
        self.item_repo = ServiceItemRepository(db)
        self.addon_repo = ServiceAddonRepository(db)
        self.audit_service = AuditService(db)

    # --- CATALOG ---
    def get_catalog(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID) -> Catalog:
        catalog = self.catalog_repo.get_by_id(tenant_id, catalog_id)
        if not catalog:
            raise HTTPException(status_code=404, detail="Catalog not found")
        return catalog

    def get_catalogs_by_seller(self, tenant_id: uuid.UUID, seller_id: uuid.UUID) -> Sequence[Catalog]:
        return self.catalog_repo.get_by_seller(tenant_id, seller_id)

    def create_catalog(self, tenant_id: uuid.UUID, user_id: uuid.UUID, data: CatalogCreate) -> Catalog:
        seller = self.db.query(Seller).filter(Seller.id == data.seller_id, Seller.tenant_id == tenant_id).first()
        if not seller:
            raise HTTPException(status_code=404, detail="Seller not found")
            
        catalog = Catalog(
            tenant_id=tenant_id,
            seller_id=data.seller_id,
            name=data.name,
            description=data.description,
            created_by=user_id,
            updated_by=user_id
        )
        try:
            catalog = self.catalog_repo.create(catalog)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=400, detail="Catalog already exists for this seller")

        self.audit_service.log_event(event_type="CATALOG_CREATED", tenant_id=tenant_id, actor_user_id=user_id, payload={"message": f"Catalog {catalog.id} created"})
        return catalog

    def update_catalog(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID, user_id: uuid.UUID, data: CatalogUpdate) -> Catalog:
        catalog = self.get_catalog(tenant_id, catalog_id)
        if data.name is not None:
            catalog.name = data.name
        if data.description is not None:
            catalog.description = data.description
            
        catalog.updated_by = user_id
        self.db.commit()
        self.audit_service.log_event(event_type="CATALOG_UPDATED", tenant_id=tenant_id, actor_user_id=user_id, payload={"message": f"Catalog {catalog.id} updated"})
        return catalog

    def set_catalog_status(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID, user_id: uuid.UUID, status: str) -> Catalog:
        catalog = self.get_catalog(tenant_id, catalog_id)
        if status == "ACTIVE":
            services = self.service_repo.get_by_catalog(tenant_id, catalog_id)
            if not any(s.status == "ACTIVE" for s in services):
                raise HTTPException(status_code=400, detail="Cannot activate catalog without active services")
                
        catalog.status = status
        catalog.updated_by = user_id
        self.db.commit()
        self.audit_service.log_event(event_type=f"CATALOG_{status}", tenant_id=tenant_id, actor_user_id=user_id, payload={"message": f"Catalog {catalog.id} status changed to {status}"})
        return catalog

    # --- CATEGORY ---
    def get_category(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID, category_id: uuid.UUID) -> Category:
        category = self.category_repo.get_by_id(tenant_id, category_id)
        if not category or category.catalog_id != catalog_id:
            raise HTTPException(status_code=404, detail="Category not found")
        return category

    def get_categories(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID) -> Sequence[Category]:
        # Validate catalog exists and belongs to tenant
        self.get_catalog(tenant_id, catalog_id)
        return self.category_repo.get_by_catalog(tenant_id, catalog_id)

    def create_category(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID, user_id: uuid.UUID, data: CategoryCreate) -> Category:
        self.get_catalog(tenant_id, catalog_id)
        
        if data.parent_id:
            parent = self.category_repo.get_by_id(tenant_id, data.parent_id)
            if not parent or parent.catalog_id != catalog_id:
                raise HTTPException(status_code=400, detail="Invalid parent category")
                
        category = Category(
            tenant_id=tenant_id,
            catalog_id=catalog_id,
            **data.model_dump(),
            created_by=user_id,
            updated_by=user_id
        )
        try:
            category = self.category_repo.create(category)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=400, detail="Category slug already exists in this catalog")
            
        self.audit_service.log_event(event_type="CATEGORY_CREATED", tenant_id=tenant_id, actor_user_id=user_id, payload={"message": f"Category {category.id} created"})
        return category

    def update_category(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID, category_id: uuid.UUID, user_id: uuid.UUID, data: CategoryUpdate) -> Category:
        category = self.get_category(tenant_id, catalog_id, category_id)
        
        if data.parent_id is not None:
            if data.parent_id == category_id:
                raise HTTPException(status_code=400, detail="Category cannot be its own parent")
            parent = self.category_repo.get_by_id(tenant_id, data.parent_id)
            if not parent or parent.catalog_id != catalog_id:
                raise HTTPException(status_code=400, detail="Invalid parent category")
            category.parent_id = data.parent_id

        for k, v in data.model_dump(exclude_unset=True).items():
            if k != 'parent_id':
                setattr(category, k, v)
                
        category.updated_by = user_id
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=400, detail="Category slug already exists in this catalog")

        self.audit_service.log_event(event_type="CATEGORY_UPDATED", tenant_id=tenant_id, actor_user_id=user_id, payload={"message": f"Category {category.id} updated"})
        return category

    def set_category_status(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID, category_id: uuid.UUID, user_id: uuid.UUID, status: str) -> Category:
        category = self.get_category(tenant_id, catalog_id, category_id)
        category.status = status
        category.updated_by = user_id
        self.db.commit()
        self.audit_service.log_event(event_type=f"CATEGORY_{status}", tenant_id=tenant_id, actor_user_id=user_id, payload={"message": f"Category {category.id} status changed to {status}"})
        return category

    # --- SERVICE ---
    def get_service(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID, service_id: uuid.UUID) -> Service:
        service = self.service_repo.get_by_id(tenant_id, service_id)
        if not service or service.catalog_id != catalog_id:
            raise HTTPException(status_code=404, detail="Service not found")
        return service
        
    def get_services(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID) -> Sequence[Service]:
        self.get_catalog(tenant_id, catalog_id)
        return self.service_repo.get_by_catalog(tenant_id, catalog_id)

    def create_service(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID, user_id: uuid.UUID, data: ServiceCreate) -> Service:
        self.get_catalog(tenant_id, catalog_id)
        
        if data.category_id:
            category = self.category_repo.get_by_id(tenant_id, data.category_id)
            if not category or category.catalog_id != catalog_id:
                raise HTTPException(status_code=400, detail="Invalid category")
                
        service = Service(
            tenant_id=tenant_id,
            catalog_id=catalog_id,
            **data.model_dump(),
            created_by=user_id,
            updated_by=user_id
        )
        try:
            service = self.service_repo.create(service)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=400, detail="Service slug already exists in this catalog")
            
        self.audit_service.log_event(event_type="SERVICE_CREATED", tenant_id=tenant_id, actor_user_id=user_id, payload={"message": f"Service {service.id} created"})
        return service

    def update_service(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID, service_id: uuid.UUID, user_id: uuid.UUID, data: ServiceUpdate) -> Service:
        service = self.get_service(tenant_id, catalog_id, service_id)
        
        if data.category_id is not None:
            category = self.category_repo.get_by_id(tenant_id, data.category_id)
            if not category or category.catalog_id != catalog_id:
                raise HTTPException(status_code=400, detail="Invalid category")
            service.category_id = data.category_id

        for k, v in data.model_dump(exclude_unset=True).items():
            if k != 'category_id':
                setattr(service, k, v)
                
        service.updated_by = user_id
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=400, detail="Service slug already exists in this catalog")

        self.audit_service.log_event(event_type="SERVICE_UPDATED", tenant_id=tenant_id, actor_user_id=user_id, payload={"message": f"Service {service.id} updated"})
        return service

    def set_service_status(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID, service_id: uuid.UUID, user_id: uuid.UUID, status: str) -> Service:
        service = self.get_service(tenant_id, catalog_id, service_id)
        service.status = status
        service.updated_by = user_id
        self.db.commit()
        self.audit_service.log_event(event_type=f"SERVICE_{status}", tenant_id=tenant_id, actor_user_id=user_id, payload={"message": f"Service {service.id} status changed to {status}"})
        return service

    # --- SERVICE ITEM ---
    def get_service_item(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID, service_id: uuid.UUID, item_id: uuid.UUID) -> ServiceItem:
        self.get_service(tenant_id, catalog_id, service_id)
        item = self.item_repo.get_by_id(tenant_id, item_id)
        if not item or item.service_id != service_id:
            raise HTTPException(status_code=404, detail="Service item not found")
        return item
        
    def get_service_items(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID, service_id: uuid.UUID) -> Sequence[ServiceItem]:
        self.get_service(tenant_id, catalog_id, service_id)
        return self.item_repo.get_by_service(tenant_id, service_id)

    def create_service_item(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID, service_id: uuid.UUID, user_id: uuid.UUID, data: ServiceItemCreate) -> ServiceItem:
        self.get_service(tenant_id, catalog_id, service_id)
        
        item = ServiceItem(
            tenant_id=tenant_id,
            service_id=service_id,
            **data.model_dump()
        )
        try:
            item = self.item_repo.create(item)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=400, detail="Service item code already exists for this service")
            
        self.audit_service.log_event(event_type="SERVICE_ITEM_CREATED", tenant_id=tenant_id, actor_user_id=user_id, payload={"message": f"Service item {item.id} created"})
        return item
        
    def update_service_item(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID, service_id: uuid.UUID, item_id: uuid.UUID, user_id: uuid.UUID, data: ServiceItemUpdate) -> ServiceItem:
        item = self.get_service_item(tenant_id, catalog_id, service_id, item_id)
        
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(item, k, v)
            
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=400, detail="Service item code already exists for this service")

        self.audit_service.log_event(event_type="SERVICE_ITEM_UPDATED", tenant_id=tenant_id, actor_user_id=user_id, payload={"message": f"Service item {item.id} updated"})
        return item
        
    def set_service_item_status(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID, service_id: uuid.UUID, item_id: uuid.UUID, user_id: uuid.UUID, status: str) -> ServiceItem:
        item = self.get_service_item(tenant_id, catalog_id, service_id, item_id)
        item.status = status
        self.db.commit()
        self.audit_service.log_event(event_type=f"SERVICE_ITEM_{status}", tenant_id=tenant_id, actor_user_id=user_id, payload={"message": f"Service item {item.id} status changed to {status}"})
        return item

    # --- ADDON ---
    def get_addon(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID, service_id: uuid.UUID, addon_id: uuid.UUID) -> ServiceAddon:
        self.get_service(tenant_id, catalog_id, service_id)
        addon = self.addon_repo.get_by_id(tenant_id, addon_id)
        if not addon or addon.service_id != service_id:
            raise HTTPException(status_code=404, detail="Addon not found")
        return addon
        
    def get_addons(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID, service_id: uuid.UUID) -> Sequence[ServiceAddon]:
        self.get_service(tenant_id, catalog_id, service_id)
        return self.addon_repo.get_by_service(tenant_id, service_id)

    def create_addon(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID, service_id: uuid.UUID, user_id: uuid.UUID, data: ServiceAddonCreate) -> ServiceAddon:
        self.get_service(tenant_id, catalog_id, service_id)
        
        addon = ServiceAddon(
            tenant_id=tenant_id,
            service_id=service_id,
            **data.model_dump()
        )
        try:
            addon = self.addon_repo.create(addon)
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=400, detail="Addon code already exists for this service")
            
        self.audit_service.log_event(event_type="ADDON_CREATED", tenant_id=tenant_id, actor_user_id=user_id, payload={"message": f"Addon {addon.id} created"})
        return addon
        
    def update_addon(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID, service_id: uuid.UUID, addon_id: uuid.UUID, user_id: uuid.UUID, data: ServiceAddonUpdate) -> ServiceAddon:
        addon = self.get_addon(tenant_id, catalog_id, service_id, addon_id)
        
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(addon, k, v)
            
        try:
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(status_code=400, detail="Addon code already exists for this service")

        self.audit_service.log_event(event_type="ADDON_UPDATED", tenant_id=tenant_id, actor_user_id=user_id, payload={"message": f"Addon {addon.id} updated"})
        return addon
        
    def set_addon_status(self, tenant_id: uuid.UUID, catalog_id: uuid.UUID, service_id: uuid.UUID, addon_id: uuid.UUID, user_id: uuid.UUID, status: str) -> ServiceAddon:
        addon = self.get_addon(tenant_id, catalog_id, service_id, addon_id)
        addon.status = status
        self.db.commit()
        self.audit_service.log_event(event_type=f"ADDON_{status}", tenant_id=tenant_id, actor_user_id=user_id, payload={"message": f"Addon {addon.id} status changed to {status}"})
        return addon

