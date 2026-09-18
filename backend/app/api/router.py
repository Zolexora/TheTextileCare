from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.memberships import router as memberships_router
from app.api.v1.roles import router as roles_router
from app.api.v1.tenants import router as tenants_router

router = APIRouter()

router.include_router(health_router, prefix='/api/v1')
router.include_router(auth_router, prefix='/api/v1')
router.include_router(tenants_router, prefix='/api/v1')
router.include_router(memberships_router, prefix='/api/v1')
router.include_router(roles_router, prefix='/api/v1')
router.include_router(audit_router, prefix='/api/v1')
