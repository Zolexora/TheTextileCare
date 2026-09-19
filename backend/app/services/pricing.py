"""Pricing Engine Service — TTC Phase 5.

Deterministic, tenant-isolated pricing calculation following the precedence chain:
    Platform Default → Seller → Branch → Rule

Uses Decimal arithmetic throughout. Never uses float for money.
Rounding: ROUND_HALF_UP, 2 decimal places.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from typing import Sequence

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.pricing import (
    ComponentType,
    PriceBook,
    PriceBookScope,
    PriceBookStatus,
    PriceRule,
    PriceRuleType,
    RateType,
)
from app.models.seller import Branch, Seller
from app.models.catalog import Service, ServiceAddon, ServiceItem
from app.repositories.pricing import PricingRepository
from app.schemas.pricing import (
    PriceBookCreate,
    PriceBookResponse,
    PriceBookUpdate,
    PriceRuleCreate,
    PriceRuleResponse,
    PriceRuleUpdate,
    PricingCalculationComponentBreakdown,
    PricingCalculationItemRequest,
    PricingCalculationItemResult,
    PricingCalculationRequest,
    PricingCalculationResult,
)
from app.services.audit import AuditService

SCALE = Decimal("0.01")


def _round(v: Decimal) -> Decimal:
    """Round a Decimal to 2 decimal places using ROUND_HALF_UP."""
    return v.quantize(SCALE, rounding=ROUND_HALF_UP)


class PricingService:
    """Service layer for managing and calculating pricing in TTC."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = PricingRepository(db)
        self.audit = AuditService(db)

    # =========================================================================
    # Price Book Management
    # =========================================================================

    def create_price_book(
        self,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        data: PriceBookCreate,
    ) -> PriceBook:
        self._validate_seller(tenant_id, data.seller_id)
        if data.branch_id:
            self._validate_branch(tenant_id, data.seller_id, data.branch_id)

        book = PriceBook(
            tenant_id=tenant_id,
            seller_id=data.seller_id,
            branch_id=data.branch_id,
            name=data.name,
            description=data.description,
            scope=data.scope,
            currency=data.currency,
            priority=data.priority,
            is_default=data.is_default,
            is_active=data.is_active,
            status=PriceBookStatus.DRAFT,
        )
        self.repo.create_book(tenant_id, book)
        self.db.commit()
        self.audit.log_event(
            event_type="PRICE_BOOK_CREATED",
            tenant_id=tenant_id,
            actor_user_id=user_id,
            entity_type="PriceBook",
            entity_id=str(book.id),
        )
        return book

    def get_price_book(self, tenant_id: uuid.UUID, book_id: uuid.UUID) -> PriceBook:
        book = self.repo.get_book(tenant_id, book_id, include_platform_defaults=True)
        if not book:
            raise HTTPException(status_code=404, detail="Price book not found")
        return book

    def list_price_books(
        self,
        tenant_id: uuid.UUID,
        seller_id: uuid.UUID | None = None,
        branch_id: uuid.UUID | None = None,
    ) -> Sequence[PriceBook]:
        return self.repo.list_books(
            tenant_id=tenant_id,
            seller_id=seller_id,
            branch_id=branch_id,
            include_platform_defaults=True,
        )

    def update_price_book(
        self,
        tenant_id: uuid.UUID,
        book_id: uuid.UUID,
        user_id: uuid.UUID,
        data: PriceBookUpdate,
    ) -> PriceBook:
        book = self.repo.update_book(tenant_id, book_id, data)
        if not book:
            raise HTTPException(status_code=404, detail="Price book not found")
        self.db.commit()
        self.audit.log_event(
            event_type="PRICE_BOOK_UPDATED",
            tenant_id=tenant_id,
            actor_user_id=user_id,
            entity_type="PriceBook",
            entity_id=str(book_id),
        )
        return book

    def activate_price_book(
        self, tenant_id: uuid.UUID, book_id: uuid.UUID, user_id: uuid.UUID
    ) -> PriceBook:
        book = self.repo.get_book(tenant_id, book_id, include_platform_defaults=False)
        if not book:
            raise HTTPException(status_code=404, detail="Price book not found")
        if book.status == PriceBookStatus.ACTIVE:
            return book
        book.status = PriceBookStatus.ACTIVE
        book.is_active = True
        self.db.commit()
        self.audit.log_event(
            event_type="PRICE_BOOK_ACTIVATED",
            tenant_id=tenant_id,
            actor_user_id=user_id,
            entity_type="PriceBook",
            entity_id=str(book_id),
        )
        return book

    def deactivate_price_book(
        self, tenant_id: uuid.UUID, book_id: uuid.UUID, user_id: uuid.UUID
    ) -> PriceBook:
        book = self.repo.get_book(tenant_id, book_id, include_platform_defaults=False)
        if not book:
            raise HTTPException(status_code=404, detail="Price book not found")
        book.status = PriceBookStatus.INACTIVE
        book.is_active = False
        self.db.commit()
        self.audit.log_event(
            event_type="PRICE_BOOK_DEACTIVATED",
            tenant_id=tenant_id,
            actor_user_id=user_id,
            entity_type="PriceBook",
            entity_id=str(book_id),
        )
        return book

    # =========================================================================
    # Price Rule Management
    # =========================================================================

    def create_price_rule(
        self,
        tenant_id: uuid.UUID,
        book_id: uuid.UUID,
        user_id: uuid.UUID,
        data: PriceRuleCreate,
    ) -> PriceRule:
        book = self.repo.get_book(tenant_id, book_id)
        if not book:
            raise HTTPException(status_code=404, detail="Price book not found")

        # Validate catalog references belong to the same tenant
        if data.service_id:
            self._validate_service(tenant_id, data.service_id)
        if data.service_item_id:
            self._validate_service_item(tenant_id, data.service_id, data.service_item_id)
        if data.service_addon_id:
            self._validate_addon(tenant_id, data.service_id, data.service_addon_id)

        rule = PriceRule(
            price_book_id=book_id,
            name=data.name,
            description=data.description,
            service_id=data.service_id,
            service_item_id=data.service_item_id,
            service_addon_id=data.service_addon_id,
            rule_type=data.rule_type,
            component_type=data.component_type,
            rate_type=data.rate_type,
            rate=data.rate,
            status=data.status,
            is_active=data.is_active,
            priority=data.priority,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
        )
        result = self.repo.create_rule(tenant_id, book_id, rule)
        if not result:
            raise HTTPException(status_code=404, detail="Price book not found")
        self.db.commit()
        self.audit.log_event(
            event_type="PRICE_RULE_CREATED",
            tenant_id=tenant_id,
            actor_user_id=user_id,
            entity_type="PriceRule",
            entity_id=str(result.id),
        )
        return result

    def get_price_rule(
        self, tenant_id: uuid.UUID, rule_id: uuid.UUID
    ) -> PriceRule:
        rule = self.repo.get_rule(tenant_id, rule_id, include_platform_defaults=True)
        if not rule:
            raise HTTPException(status_code=404, detail="Price rule not found")
        return rule

    def list_price_rules(
        self, tenant_id: uuid.UUID, book_id: uuid.UUID
    ) -> Sequence[PriceRule]:
        return self.repo.list_rules_for_book(tenant_id, book_id, include_platform_defaults=True)

    def update_price_rule(
        self,
        tenant_id: uuid.UUID,
        rule_id: uuid.UUID,
        user_id: uuid.UUID,
        data: PriceRuleUpdate,
    ) -> PriceRule:
        rule = self.repo.update_rule(tenant_id, rule_id, data)
        if not rule:
            raise HTTPException(status_code=404, detail="Price rule not found")
        self.db.commit()
        self.audit.log_event(
            event_type="PRICE_RULE_UPDATED",
            tenant_id=tenant_id,
            actor_user_id=user_id,
            entity_type="PriceRule",
            entity_id=str(rule_id),
        )
        return rule

    def activate_price_rule(
        self, tenant_id: uuid.UUID, rule_id: uuid.UUID, user_id: uuid.UUID
    ) -> PriceRule:
        rule = self.repo.get_rule(tenant_id, rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="Price rule not found")
        rule.status = "ACTIVE"
        rule.is_active = True
        self.db.commit()
        self.audit.log_event(
            event_type="PRICE_RULE_ACTIVATED",
            tenant_id=tenant_id,
            actor_user_id=user_id,
            entity_type="PriceRule",
            entity_id=str(rule_id),
        )
        return rule

    def deactivate_price_rule(
        self, tenant_id: uuid.UUID, rule_id: uuid.UUID, user_id: uuid.UUID
    ) -> PriceRule:
        rule = self.repo.get_rule(tenant_id, rule_id)
        if not rule:
            raise HTTPException(status_code=404, detail="Price rule not found")
        rule.status = "INACTIVE"
        rule.is_active = False
        self.db.commit()
        self.audit.log_event(
            event_type="PRICE_RULE_DEACTIVATED",
            tenant_id=tenant_id,
            actor_user_id=user_id,
            entity_type="PriceRule",
            entity_id=str(rule_id),
        )
        return rule

    # =========================================================================
    # Deterministic Calculation Engine
    # =========================================================================

    def calculate(
        self,
        tenant_id: uuid.UUID,
        request: PricingCalculationRequest,
    ) -> PricingCalculationResult:
        """Run the deterministic pricing pipeline.

        Pipeline:
            1. Validate tenant/seller/branch
            2. Fetch all eligible rules for the context
            3. For each item, score and select the best-matching rule
            4. Calculate base, surcharges, discounts, taxes per item
            5. Aggregate and return canonical breakdown
        """
        # Step 1: Validate seller/branch
        self._validate_seller(tenant_id, request.seller_id)
        if request.branch_id:
            self._validate_branch(tenant_id, request.seller_id, request.branch_id)

        # Step 2: Resolve calculation time
        calc_at = request.calculation_time or datetime.now(timezone.utc)

        # Step 3: Fetch all eligible active rules (filtered by effective dates in repo)
        all_rules = self.repo.get_active_rules_for_calculation(
            tenant_id=tenant_id,
            seller_id=request.seller_id,
            branch_id=request.branch_id,
            as_of=calc_at,
        )

        # Step 4: Calculate each item
        item_results: list[PricingCalculationItemResult] = []
        for item_req in request.items:
            result = self._calculate_item(tenant_id, item_req, all_rules)
            item_results.append(result)

        # Step 5: Aggregate
        subtotal = _round(sum(r.base_price for r in item_results))
        total_surcharges = _round(sum(r.surcharges for r in item_results))
        total_discounts = _round(sum(r.discounts for r in item_results))
        total_tax = _round(sum(r.tax for r in item_results))
        grand_total = _round(subtotal + total_surcharges - total_discounts + total_tax)

        # Invariant: grand_total >= 0
        if grand_total < Decimal("0"):
            grand_total = Decimal("0.00")

        return PricingCalculationResult(
            currency=request.currency,
            subtotal=subtotal,
            total_surcharges=total_surcharges,
            total_discounts=total_discounts,
            total_tax=total_tax,
            grand_total=grand_total,
            items=item_results,
        )

    def _calculate_item(
        self,
        tenant_id: uuid.UUID,
        item_req: PricingCalculationItemRequest,
        all_rules: Sequence[PriceRule],
    ) -> PricingCalculationItemResult:
        """Calculate a single line item using precedence-ordered rules."""
        # Score each rule for this item (higher = more specific)
        SCOPE_SCORE = {
            PriceBookScope.BRANCH: 30,
            PriceBookScope.SELLER: 20,
            PriceBookScope.PLATFORM_DEFAULT: 10,
        }

        def _specificity(rule: PriceRule) -> int:
            score = SCOPE_SCORE.get(rule.price_book.scope, 0)
            # More specific catalog targeting gets higher score
            if rule.service_item_id == item_req.service_item_id and item_req.service_item_id:
                score += 3
            elif rule.service_id == item_req.service_id and not rule.service_item_id:
                score += 2
            elif rule.service_id is None:
                score += 1
            return score

        # Filter only relevant rules for this item
        def _matches(rule: PriceRule) -> bool:
            # service match: rule targets this service or is global
            if rule.service_id and rule.service_id != item_req.service_id:
                return False
            # item match: if rule targets a specific item, must match
            if rule.service_item_id and rule.service_item_id != item_req.service_item_id:
                return False
            # addon match: skip addon rules in base item calculation
            if rule.service_addon_id:
                return False
            return True

        base_rules = [r for r in all_rules if _matches(r) and r.component_type == ComponentType.BASE_PRICE]
        surcharge_rules = [r for r in all_rules if _matches(r) and r.component_type == ComponentType.SURCHARGE]
        discount_rules = [r for r in all_rules if _matches(r) and r.component_type == ComponentType.DISCOUNT]
        tax_rules = [r for r in all_rules if _matches(r) and r.component_type == ComponentType.TAX]

        if not base_rules:
            raise HTTPException(
                status_code=422,
                detail=f"No active pricing rule found for service {item_req.service_id}"
                + (f" item {item_req.service_item_id}" if item_req.service_item_id else ""),
            )

        # Select best base rule (most specific + highest priority)
        best_base = max(
            base_rules,
            key=lambda r: (_specificity(r), r.priority, str(r.id)),
        )

        breakdown: list[PricingCalculationComponentBreakdown] = []
        applied_ids: list[uuid.UUID] = []

        # --- Base price ---
        base_amount = self._apply_rule(best_base, item_req)
        breakdown.append(PricingCalculationComponentBreakdown(
            name=best_base.name or "Base Price",
            component_type=ComponentType.BASE_PRICE,
            rate_type=best_base.rate_type,
            rate=best_base.rate,
            amount=base_amount,
        ))
        applied_ids.append(best_base.id)

        # --- Surcharges (additive, all matching rules applied) ---
        surcharge_total = Decimal("0.00")
        for rule in sorted(surcharge_rules, key=lambda r: (-_specificity(r), -r.priority)):
            amt = self._apply_component_rule(rule, base_amount)
            surcharge_total += amt
            breakdown.append(PricingCalculationComponentBreakdown(
                name=rule.name or "Surcharge",
                component_type=ComponentType.SURCHARGE,
                rate_type=rule.rate_type,
                rate=rule.rate,
                amount=amt,
            ))
            applied_ids.append(rule.id)

        # --- Discounts (subtractive, all matching rules applied, capped at subtotal) ---
        discount_total = Decimal("0.00")
        for rule in sorted(discount_rules, key=lambda r: (-_specificity(r), -r.priority)):
            amt = self._apply_component_rule(rule, base_amount)
            discount_total += amt
            breakdown.append(PricingCalculationComponentBreakdown(
                name=rule.name or "Discount",
                component_type=ComponentType.DISCOUNT,
                rate_type=rule.rate_type,
                rate=rule.rate,
                amount=amt,
            ))
            applied_ids.append(rule.id)

        # Cap discount at base_amount to prevent negative subtotals
        discount_total = min(discount_total, base_amount)

        # --- Taxable amount = base + surcharges - discounts ---
        taxable = _round(base_amount + surcharge_total - discount_total)

        # --- Tax (applied to taxable amount) ---
        tax_total = Decimal("0.00")
        for rule in sorted(tax_rules, key=lambda r: (-_specificity(r), -r.priority)):
            if rule.rate_type == RateType.PERCENTAGE:
                amt = _round(taxable * rule.rate / Decimal("100"))
            else:
                amt = _round(rule.rate)
            tax_total += amt
            breakdown.append(PricingCalculationComponentBreakdown(
                name=rule.name or "Tax",
                component_type=ComponentType.TAX,
                rate_type=rule.rate_type,
                rate=rule.rate,
                amount=amt,
            ))
            applied_ids.append(rule.id)

        line_total = _round(base_amount + surcharge_total - discount_total + tax_total)

        return PricingCalculationItemResult(
            service_id=item_req.service_id,
            service_item_id=item_req.service_item_id,
            unit_price=best_base.rate,
            quantity=item_req.quantity,
            weight=item_req.weight,
            base_price=base_amount,
            surcharges=_round(surcharge_total),
            discounts=_round(discount_total),
            tax=_round(tax_total),
            subtotal=base_amount,
            total=line_total,
            applied_rule_ids=applied_ids,
            breakdown=breakdown,
        )

    def _apply_rule(
        self, rule: PriceRule, item_req: PricingCalculationItemRequest
    ) -> Decimal:
        """Calculate base price amount for a rule and item request."""
        qty = item_req.quantity
        weight = item_req.weight or Decimal("0")

        if rule.rule_type == PriceRuleType.FIXED:
            return _round(rule.rate)
        elif rule.rule_type == PriceRuleType.PER_ITEM:
            return _round(rule.rate * qty)
        elif rule.rule_type == PriceRuleType.PER_UNIT:
            return _round(rule.rate * qty)
        elif rule.rule_type == PriceRuleType.PER_WEIGHT:
            return _round(rule.rate * weight)
        return _round(rule.rate)

    def _apply_component_rule(self, rule: PriceRule, base: Decimal) -> Decimal:
        """Calculate surcharge/discount/tax amount."""
        if rule.rate_type == RateType.PERCENTAGE:
            return _round(base * rule.rate / Decimal("100"))
        return _round(rule.rate)

    # =========================================================================
    # Validation Helpers
    # =========================================================================

    def _validate_seller(self, tenant_id: uuid.UUID, seller_id: uuid.UUID) -> Seller:
        seller = (
            self.db.query(Seller)
            .filter(Seller.id == seller_id, Seller.tenant_id == tenant_id)
            .first()
        )
        if not seller:
            raise HTTPException(status_code=404, detail="Seller not found")
        return seller

    def _validate_branch(
        self, tenant_id: uuid.UUID, seller_id: uuid.UUID, branch_id: uuid.UUID
    ) -> Branch:
        branch = (
            self.db.query(Branch)
            .filter(
                Branch.id == branch_id,
                Branch.seller_id == seller_id,
                Branch.tenant_id == tenant_id,
            )
            .first()
        )
        if not branch:
            raise HTTPException(status_code=404, detail="Branch not found or does not belong to seller")
        return branch

    def _validate_service(self, tenant_id: uuid.UUID, service_id: uuid.UUID) -> Service:
        svc = (
            self.db.query(Service)
            .filter(Service.id == service_id, Service.tenant_id == tenant_id)
            .first()
        )
        if not svc:
            raise HTTPException(status_code=404, detail="Service not found")
        return svc

    def _validate_service_item(
        self, tenant_id: uuid.UUID, service_id: uuid.UUID | None, item_id: uuid.UUID
    ) -> ServiceItem:
        q = self.db.query(ServiceItem).filter(
            ServiceItem.id == item_id, ServiceItem.tenant_id == tenant_id
        )
        if service_id:
            q = q.filter(ServiceItem.service_id == service_id)
        item = q.first()
        if not item:
            raise HTTPException(status_code=404, detail="Service item not found")
        return item

    def _validate_addon(
        self, tenant_id: uuid.UUID, service_id: uuid.UUID | None, addon_id: uuid.UUID
    ) -> ServiceAddon:
        q = self.db.query(ServiceAddon).filter(
            ServiceAddon.id == addon_id, ServiceAddon.tenant_id == tenant_id
        )
        if service_id:
            q = q.filter(ServiceAddon.service_id == service_id)
        addon = q.first()
        if not addon:
            raise HTTPException(status_code=404, detail="Addon not found")
        return addon
