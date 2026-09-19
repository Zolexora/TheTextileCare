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
from app.api.v1.customer import router as customer_router
from app.api.v1.marketplace import router as marketplace_router
from app.api.v1.orders import customer_router as orders_customer_router
from app.api.v1.orders import seller_router as orders_seller_router
# Phase 7
from app.api.v1.commercial import router as commercial_router
from app.api.v1.billing import router as billing_router
from app.api.v1.payment import router as payment_router
from app.api.v1.pickup import seller_router as pickup_seller_router
from app.api.v1.pickup import customer_router as pickup_customer_router

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
router.include_router(customer_router, prefix='/api/v1/customer')
router.include_router(marketplace_router, prefix='/api/v1/marketplace')
router.include_router(orders_customer_router, prefix='/api/v1/orders')
router.include_router(orders_seller_router, prefix='/api/v1/seller/orders')
# Phase 7 routers
router.include_router(commercial_router, prefix='/api/v1/seller/commercial')
router.include_router(billing_router, prefix='/api/v1/seller/billing')
router.include_router(payment_router, prefix='/api/v1/seller/payments')
router.include_router(pickup_seller_router, prefix='/api/v1/seller/pickups')
router.include_router(pickup_customer_router, prefix='/api/v1/customer/pickups')
