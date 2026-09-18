import uuid
from typing import Sequence
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db import get_db
from app.dependencies import require_permission
from app.core.permissions.constants import PermissionName
from app.core.tenant.context import TenantContext
from app.schemas.catalog import (
    CatalogCreate, CatalogResponse, CatalogUpdate,
    CategoryCreate, CategoryResponse, CategoryUpdate,
    ServiceCreate, ServiceResponse, ServiceUpdate,
    ServiceItemCreate, ServiceItemResponse, ServiceItemUpdate,
    ServiceAddonCreate, ServiceAddonResponse, ServiceAddonUpdate
)
from app.services.catalog import CatalogService

router = APIRouter()

# --- CATALOG ---
@router.post("", response_model=CatalogResponse, status_code=status.HTTP_201_CREATED)
def create_catalog(
    data: CatalogCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_MANAGE)),
):
    service = CatalogService(db)
    return service.create_catalog(ctx.tenant.id, ctx.user.id, data)

@router.get("/seller/{seller_id}", response_model=list[CatalogResponse])
def get_seller_catalogs(
    seller_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_READ)),
):
    service = CatalogService(db)
    return service.get_catalogs_by_seller(ctx.tenant.id, seller_id)

@router.get("/{catalog_id}", response_model=CatalogResponse)
def get_catalog(
    catalog_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_READ)),
):
    service = CatalogService(db)
    return service.get_catalog(ctx.tenant.id, catalog_id)

@router.patch("/{catalog_id}", response_model=CatalogResponse)
def update_catalog(
    catalog_id: uuid.UUID,
    data: CatalogUpdate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_MANAGE)),
):
    service = CatalogService(db)
    return service.update_catalog(ctx.tenant.id, catalog_id, ctx.user.id, data)

@router.post("/{catalog_id}/activate", response_model=CatalogResponse)
def activate_catalog(
    catalog_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_PUBLISH)),
):
    service = CatalogService(db)
    return service.set_catalog_status(ctx.tenant.id, catalog_id, ctx.user.id, "ACTIVE")

@router.post("/{catalog_id}/deactivate", response_model=CatalogResponse)
def deactivate_catalog(
    catalog_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_PUBLISH)),
):
    service = CatalogService(db)
    return service.set_catalog_status(ctx.tenant.id, catalog_id, ctx.user.id, "INACTIVE")

# --- CATEGORY ---
@router.post("/{catalog_id}/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    catalog_id: uuid.UUID,
    data: CategoryCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_CATEGORIES_MANAGE)),
):
    service = CatalogService(db)
    return service.create_category(ctx.tenant.id, catalog_id, ctx.user.id, data)

@router.get("/{catalog_id}/categories", response_model=list[CategoryResponse])
def get_categories(
    catalog_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_CATEGORIES_READ)),
):
    service = CatalogService(db)
    return service.get_categories(ctx.tenant.id, catalog_id)

@router.get("/{catalog_id}/categories/{category_id}", response_model=CategoryResponse)
def get_category(
    catalog_id: uuid.UUID,
    category_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_CATEGORIES_READ)),
):
    service = CatalogService(db)
    return service.get_category(ctx.tenant.id, catalog_id, category_id)

@router.patch("/{catalog_id}/categories/{category_id}", response_model=CategoryResponse)
def update_category(
    catalog_id: uuid.UUID,
    category_id: uuid.UUID,
    data: CategoryUpdate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_CATEGORIES_MANAGE)),
):
    service = CatalogService(db)
    return service.update_category(ctx.tenant.id, catalog_id, category_id, ctx.user.id, data)

@router.post("/{catalog_id}/categories/{category_id}/deactivate", response_model=CategoryResponse)
def deactivate_category(
    catalog_id: uuid.UUID,
    category_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_CATEGORIES_MANAGE)),
):
    service = CatalogService(db)
    return service.set_category_status(ctx.tenant.id, catalog_id, category_id, ctx.user.id, "INACTIVE")

# --- SERVICE ---
@router.post("/{catalog_id}/services", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED)
def create_service(
    catalog_id: uuid.UUID,
    data: ServiceCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_SERVICES_MANAGE)),
):
    service = CatalogService(db)
    return service.create_service(ctx.tenant.id, catalog_id, ctx.user.id, data)

@router.get("/{catalog_id}/services", response_model=list[ServiceResponse])
def get_services(
    catalog_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_SERVICES_READ)),
):
    service = CatalogService(db)
    return service.get_services(ctx.tenant.id, catalog_id)

@router.get("/{catalog_id}/services/{service_id}", response_model=ServiceResponse)
def get_service(
    catalog_id: uuid.UUID,
    service_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_SERVICES_READ)),
):
    service = CatalogService(db)
    return service.get_service(ctx.tenant.id, catalog_id, service_id)

@router.patch("/{catalog_id}/services/{service_id}", response_model=ServiceResponse)
def update_service(
    catalog_id: uuid.UUID,
    service_id: uuid.UUID,
    data: ServiceUpdate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_SERVICES_MANAGE)),
):
    service = CatalogService(db)
    return service.update_service(ctx.tenant.id, catalog_id, service_id, ctx.user.id, data)

@router.post("/{catalog_id}/services/{service_id}/deactivate", response_model=ServiceResponse)
def deactivate_service(
    catalog_id: uuid.UUID,
    service_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_SERVICES_MANAGE)),
):
    service = CatalogService(db)
    return service.set_service_status(ctx.tenant.id, catalog_id, service_id, ctx.user.id, "INACTIVE")


# --- SERVICE ITEMS ---
@router.post("/{catalog_id}/services/{service_id}/items", response_model=ServiceItemResponse, status_code=status.HTTP_201_CREATED)
def create_service_item(
    catalog_id: uuid.UUID,
    service_id: uuid.UUID,
    data: ServiceItemCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_ITEMS_MANAGE)),
):
    service = CatalogService(db)
    return service.create_service_item(ctx.tenant.id, catalog_id, service_id, ctx.user.id, data)

@router.get("/{catalog_id}/services/{service_id}/items", response_model=list[ServiceItemResponse])
def get_service_items(
    catalog_id: uuid.UUID,
    service_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_ITEMS_READ)),
):
    service = CatalogService(db)
    return service.get_service_items(ctx.tenant.id, catalog_id, service_id)

@router.patch("/{catalog_id}/services/{service_id}/items/{item_id}", response_model=ServiceItemResponse)
def update_service_item(
    catalog_id: uuid.UUID,
    service_id: uuid.UUID,
    item_id: uuid.UUID,
    data: ServiceItemUpdate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_ITEMS_MANAGE)),
):
    service = CatalogService(db)
    return service.update_service_item(ctx.tenant.id, catalog_id, service_id, item_id, ctx.user.id, data)

@router.post("/{catalog_id}/services/{service_id}/items/{item_id}/deactivate", response_model=ServiceItemResponse)
def deactivate_service_item(
    catalog_id: uuid.UUID,
    service_id: uuid.UUID,
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_ITEMS_MANAGE)),
):
    service = CatalogService(db)
    return service.set_service_item_status(ctx.tenant.id, catalog_id, service_id, item_id, ctx.user.id, "INACTIVE")

# --- ADDONS ---
@router.post("/{catalog_id}/services/{service_id}/addons", response_model=ServiceAddonResponse, status_code=status.HTTP_201_CREATED)
def create_service_addon(
    catalog_id: uuid.UUID,
    service_id: uuid.UUID,
    data: ServiceAddonCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_ADDONS_MANAGE)),
):
    service = CatalogService(db)
    return service.create_addon(ctx.tenant.id, catalog_id, service_id, ctx.user.id, data)

@router.get("/{catalog_id}/services/{service_id}/addons", response_model=list[ServiceAddonResponse])
def get_service_addons(
    catalog_id: uuid.UUID,
    service_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_ADDONS_READ)),
):
    service = CatalogService(db)
    return service.get_addons(ctx.tenant.id, catalog_id, service_id)

@router.patch("/{catalog_id}/services/{service_id}/addons/{addon_id}", response_model=ServiceAddonResponse)
def update_service_addon(
    catalog_id: uuid.UUID,
    service_id: uuid.UUID,
    addon_id: uuid.UUID,
    data: ServiceAddonUpdate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_ADDONS_MANAGE)),
):
    service = CatalogService(db)
    return service.update_addon(ctx.tenant.id, catalog_id, service_id, addon_id, ctx.user.id, data)

@router.post("/{catalog_id}/services/{service_id}/addons/{addon_id}/deactivate", response_model=ServiceAddonResponse)
def deactivate_service_addon(
    catalog_id: uuid.UUID,
    service_id: uuid.UUID,
    addon_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.CATALOG_ADDONS_MANAGE)),
):
    service = CatalogService(db)
    return service.set_addon_status(ctx.tenant.id, catalog_id, service_id, addon_id, ctx.user.id, "INACTIVE")
