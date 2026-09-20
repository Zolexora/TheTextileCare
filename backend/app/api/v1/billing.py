"""Phase 7 — Billing Invoice API endpoints.

Seller routes  : GET/POST /api/v1/seller/billing/invoices/*
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.permissions.constants import PermissionName
from app.dependencies import get_db, require_permission
from app.core.tenant.context import TenantContext
from app.repositories.billing import BillingRepository
from app.schemas.billing import (
    BillingInvoiceListResponse,
    BillingInvoicePayRequest,
    BillingInvoiceResponse,
)
from app.services.billing import BillingService

router = APIRouter(tags=["billing"])

def _get_seller_id(ctx: TenantContext, db: Session) -> uuid.UUID:
    from sqlalchemy import select
    from app.models.seller import Seller
    seller = db.execute(select(Seller).where(Seller.tenant_id == ctx.tenant_id)).scalar_one_or_none()
    if not seller:
        raise ApiError(status_code=404, code="SELLER_NOT_FOUND", message="No seller found for this tenant.")
    return seller.id



@router.get("/invoices", response_model=BillingInvoiceListResponse)
def list_invoices(
    status: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    ctx: TenantContext = Depends(require_permission(PermissionName.BILLING_READ.value)),
    db: Session = Depends(get_db),
) -> BillingInvoiceListResponse:
    """List the seller's billing invoices."""
    repo = BillingRepository(db)
    items, total = repo.list_by_seller(
        seller_id=_get_seller_id(ctx, db),
        tenant_id=ctx.tenant_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return BillingInvoiceListResponse(
        items=[BillingInvoiceResponse.model_validate(inv) for inv in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/invoices/{invoice_id}", response_model=BillingInvoiceResponse)
def get_invoice(
    invoice_id: uuid.UUID,
    ctx: TenantContext = Depends(require_permission(PermissionName.BILLING_READ.value)),
    db: Session = Depends(get_db),
) -> BillingInvoiceResponse:
    """Get a specific billing invoice by ID."""
    from app.core.exceptions.base import ApiError

    repo = BillingRepository(db)
    invoice = repo.get_by_id(invoice_id=invoice_id, tenant_id=ctx.tenant_id)
    if not invoice or invoice.seller_id != _get_seller_id(ctx, db):
        raise ApiError(
            status_code=404,
            code="INVOICE_NOT_FOUND",
            message=f"Invoice {invoice_id} not found.",
        )
    return BillingInvoiceResponse.model_validate(invoice)


@router.post("/invoices/{invoice_id}/pay", response_model=BillingInvoiceResponse)
def pay_invoice(
    invoice_id: uuid.UUID,
    request: BillingInvoicePayRequest,
    ctx: TenantContext = Depends(require_permission(PermissionName.BILLING_READ.value)),
    db: Session = Depends(get_db),
) -> BillingInvoiceResponse:
    """Simulate payment of a billing invoice."""
    svc = BillingService(db)
    invoice = svc.mark_invoice_paid(
        invoice_id=invoice_id,
        seller_id=_get_seller_id(ctx, db),
        tenant_id=ctx.tenant_id,
    )
    return BillingInvoiceResponse.model_validate(invoice)
