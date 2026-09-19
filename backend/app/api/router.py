from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.memberships import router as memberships_router
from app.api.v1.roles import router as roles_router
from app.api.v1.tenants import router as tenants_router
from app.api.v1.sellers import router as sellers_router
from app.api.v1.configuration import router as configuration_router
from app.api.v1.catalog import router as catalog_router
from app.api.v1.pricing import router as pricing_router

router = APIRouter()

router.include_router(health_router, prefix='/api/v1')
router.include_router(auth_router, prefix='/api/v1')
router.include_router(tenants_router, prefix='/api/v1')
router.include_router(memberships_router, prefix='/api/v1')
router.include_router(roles_router, prefix='/api/v1')
router.include_router(audit_router, prefix='/api/v1')
router.include_router(sellers_router, prefix='/api/v1')
router.include_router(configuration_router, prefix='/api/v1')
router.include_router(catalog_router, prefix='/api/v1/catalog')
router.include_router(pricing_router, prefix='/api/v1/pricing')
