"""Pricing Engine REST API — TTC Phase 5.

Endpoints:
    POST   /api/v1/pricing/price-books
    GET    /api/v1/pricing/price-books
    GET    /api/v1/pricing/price-books/{book_id}
    PATCH  /api/v1/pricing/price-books/{book_id}
    POST   /api/v1/pricing/price-books/{book_id}/activate
    POST   /api/v1/pricing/price-books/{book_id}/deactivate

    POST   /api/v1/pricing/price-books/{book_id}/rules
    GET    /api/v1/pricing/price-books/{book_id}/rules
    GET    /api/v1/pricing/rules/{rule_id}
    PATCH  /api/v1/pricing/rules/{rule_id}
    POST   /api/v1/pricing/rules/{rule_id}/activate
    POST   /api/v1/pricing/rules/{rule_id}/deactivate

    POST   /api/v1/pricing/calculate
"""
from __future__ import annotations

import uuid
from typing import Sequence

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.permissions.constants import PermissionName
from app.core.tenant.context import TenantContext
from app.db import get_db
from app.dependencies import require_permission
from app.schemas.pricing import (
    PriceBookCreate,
    PriceBookResponse,
    PriceBookUpdate,
    PriceRuleCreate,
    PriceRuleResponse,
    PriceRuleUpdate,
    PricingCalculationRequest,
    PricingCalculationResult,
)
from app.services.pricing import PricingService

router = APIRouter()


# =============================================================================
# Price Books
# =============================================================================

@router.post(
    "/price-books",
    response_model=PriceBookResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_price_book(
    data: PriceBookCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.PRICING_MANAGE)),
):
    svc = PricingService(db)
    return svc.create_price_book(ctx.tenant.id, ctx.user.id, data)


@router.get("/price-books", response_model=list[PriceBookResponse])
def list_price_books(
    seller_id: uuid.UUID | None = None,
    branch_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.PRICING_READ)),
):
    svc = PricingService(db)
    return svc.list_price_books(ctx.tenant.id, seller_id=seller_id, branch_id=branch_id)


@router.get("/price-books/{book_id}", response_model=PriceBookResponse)
def get_price_book(
    book_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.PRICING_READ)),
):
    svc = PricingService(db)
    return svc.get_price_book(ctx.tenant.id, book_id)


@router.patch("/price-books/{book_id}", response_model=PriceBookResponse)
def update_price_book(
    book_id: uuid.UUID,
    data: PriceBookUpdate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.PRICING_MANAGE)),
):
    svc = PricingService(db)
    return svc.update_price_book(ctx.tenant.id, book_id, ctx.user.id, data)


@router.post("/price-books/{book_id}/activate", response_model=PriceBookResponse)
def activate_price_book(
    book_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.PRICING_MANAGE)),
):
    svc = PricingService(db)
    return svc.activate_price_book(ctx.tenant.id, book_id, ctx.user.id)


@router.post("/price-books/{book_id}/deactivate", response_model=PriceBookResponse)
def deactivate_price_book(
    book_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.PRICING_MANAGE)),
):
    svc = PricingService(db)
    return svc.deactivate_price_book(ctx.tenant.id, book_id, ctx.user.id)


# =============================================================================
# Price Rules (nested under price-books)
# =============================================================================

@router.post(
    "/price-books/{book_id}/rules",
    response_model=PriceRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_price_rule(
    book_id: uuid.UUID,
    data: PriceRuleCreate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.PRICING_MANAGE)),
):
    svc = PricingService(db)
    return svc.create_price_rule(ctx.tenant.id, book_id, ctx.user.id, data)


@router.get("/price-books/{book_id}/rules", response_model=list[PriceRuleResponse])
def list_price_rules(
    book_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.PRICING_READ)),
):
    svc = PricingService(db)
    return svc.list_price_rules(ctx.tenant.id, book_id)


# =============================================================================
# Price Rules (standalone access by rule_id)
# =============================================================================

@router.get("/rules/{rule_id}", response_model=PriceRuleResponse)
def get_price_rule(
    rule_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.PRICING_READ)),
):
    svc = PricingService(db)
    return svc.get_price_rule(ctx.tenant.id, rule_id)


@router.patch("/rules/{rule_id}", response_model=PriceRuleResponse)
def update_price_rule(
    rule_id: uuid.UUID,
    data: PriceRuleUpdate,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.PRICING_MANAGE)),
):
    svc = PricingService(db)
    return svc.update_price_rule(ctx.tenant.id, rule_id, ctx.user.id, data)


@router.post("/rules/{rule_id}/activate", response_model=PriceRuleResponse)
def activate_price_rule(
    rule_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.PRICING_MANAGE)),
):
    svc = PricingService(db)
    return svc.activate_price_rule(ctx.tenant.id, rule_id, ctx.user.id)


@router.post("/rules/{rule_id}/deactivate", response_model=PriceRuleResponse)
def deactivate_price_rule(
    rule_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.PRICING_MANAGE)),
):
    svc = PricingService(db)
    return svc.deactivate_price_rule(ctx.tenant.id, rule_id, ctx.user.id)


# =============================================================================
# Deterministic Calculation
# =============================================================================

@router.post("/calculate", response_model=PricingCalculationResult)
def calculate_pricing(
    data: PricingCalculationRequest,
    db: Session = Depends(get_db),
    ctx: TenantContext = Depends(require_permission(PermissionName.PRICING_READ)),
):
    """Run the deterministic pricing engine. Does not create an order."""
    svc = PricingService(db)
    return svc.calculate(ctx.tenant.id, data)
