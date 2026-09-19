"""PricingRepository for TTC Phase 5 Pricing Engine Foundation.

Encapsulates all database operations for PriceBook and PriceRule entities
using SQLAlchemy 2.0 select/execute statements with strict multi-tenant isolation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Sequence

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.pricing import PriceBook, PriceBookScope, PriceBookStatus, PriceRule
from app.repositories.base import BaseRepository
from app.schemas.pricing import PriceBookUpdate, PriceRuleUpdate


class PricingRepository(BaseRepository):
    """Repository managing PriceBook and PriceRule persistence with strict tenant isolation."""

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    # ========================================================================
    # PriceBook Operations
    # ========================================================================

    def get_book(
        self,
        tenant_id: uuid.UUID,
        book_id: uuid.UUID,
        include_platform_defaults: bool = False,
    ) -> PriceBook | None:
        """Retrieve a price book by ID ensuring tenant isolation."""
        stmt = select(PriceBook).where(PriceBook.id == book_id)

        if include_platform_defaults:
            stmt = stmt.where(
                or_(
                    PriceBook.tenant_id == tenant_id,
                    and_(
                        PriceBook.tenant_id.is_(None),
                        PriceBook.scope == PriceBookScope.PLATFORM_DEFAULT,
                    ),
                )
            )
        else:
            stmt = stmt.where(PriceBook.tenant_id == tenant_id)

        return self.db.execute(stmt).scalar_one_or_none()

    def list_books(
        self,
        tenant_id: uuid.UUID,
        scope: PriceBookScope | None = None,
        seller_id: uuid.UUID | None = None,
        branch_id: uuid.UUID | None = None,
        is_active: bool | None = None,
        status: PriceBookStatus | None = None,
        include_platform_defaults: bool = True,
    ) -> Sequence[PriceBook]:
        """List price books matching tenant and optional scope/entity filters."""
        stmt = select(PriceBook)

        if include_platform_defaults:
            tenant_condition = or_(
                PriceBook.tenant_id == tenant_id,
                and_(
                    PriceBook.tenant_id.is_(None),
                    PriceBook.scope == PriceBookScope.PLATFORM_DEFAULT,
                ),
            )
        else:
            tenant_condition = (PriceBook.tenant_id == tenant_id)

        stmt = stmt.where(tenant_condition)

        if scope is not None:
            stmt = stmt.where(PriceBook.scope == scope)

        if seller_id is not None:
            if include_platform_defaults:
                stmt = stmt.where(
                    or_(
                        PriceBook.seller_id == seller_id,
                        PriceBook.scope == PriceBookScope.PLATFORM_DEFAULT,
                    )
                )
            else:
                stmt = stmt.where(PriceBook.seller_id == seller_id)

        if branch_id is not None:
            stmt = stmt.where(PriceBook.branch_id == branch_id)

        if is_active is not None:
            stmt = stmt.where(PriceBook.is_active == is_active)

        if status is not None:
            stmt = stmt.where(PriceBook.status == status)

        stmt = stmt.order_by(PriceBook.priority.desc(), PriceBook.created_at.desc())
        return self.db.execute(stmt).scalars().all()

    def create_book(self, tenant_id: uuid.UUID, book: PriceBook) -> PriceBook:
        """Persist a new price book for the tenant."""
        if book.scope != PriceBookScope.PLATFORM_DEFAULT or book.tenant_id is None:
            book.tenant_id = tenant_id
        self.db.add(book)
        self.db.flush()
        return book

    def update_book(
        self,
        tenant_id: uuid.UUID,
        book_id: uuid.UUID,
        data: dict[str, Any] | PriceBookUpdate,
    ) -> PriceBook | None:
        """Update a tenant's price book metadata. Rejects cross-tenant mutation."""
        book = self.get_book(tenant_id, book_id, include_platform_defaults=False)
        if not book:
            return None

        update_dict = data.model_dump(exclude_unset=True) if isinstance(data, PriceBookUpdate) else dict(data)

        immutable_fields = {"id", "tenant_id", "scope", "seller_id", "branch_id"}

        for field, value in update_dict.items():
            if field not in immutable_fields and hasattr(book, field):
                setattr(book, field, value)

        self.db.flush()
        return book

    def delete_book(self, tenant_id: uuid.UUID, book_id: uuid.UUID) -> bool:
        """Delete a tenant's price book and all its cascaded rules."""
        book = self.get_book(tenant_id, book_id, include_platform_defaults=False)
        if not book:
            return False

        self.db.delete(book)
        self.db.flush()
        return True

    # ========================================================================
    # PriceRule Operations
    # ========================================================================

    def get_rule(
        self,
        tenant_id: uuid.UUID,
        rule_id: uuid.UUID,
        include_platform_defaults: bool = False,
    ) -> PriceRule | None:
        """Retrieve a single price rule ensuring tenant isolation."""
        stmt = (
            select(PriceRule)
            .options(joinedload(PriceRule.price_book))
            .where(PriceRule.id == rule_id)
        )

        if include_platform_defaults:
            stmt = stmt.where(
                or_(
                    PriceRule.tenant_id == tenant_id,
                    PriceRule.tenant_id.is_(None),
                )
            )
        else:
            stmt = stmt.where(PriceRule.tenant_id == tenant_id)

        return self.db.execute(stmt).scalar_one_or_none()

    def list_rules_for_book(
        self,
        tenant_id: uuid.UUID,
        book_id: uuid.UUID,
        is_active: bool | None = None,
        include_platform_defaults: bool = True,
    ) -> Sequence[PriceRule]:
        """List all rules associated with a price book."""
        book = self.get_book(tenant_id, book_id, include_platform_defaults=include_platform_defaults)
        if not book:
            return []

        stmt = select(PriceRule).where(PriceRule.price_book_id == book_id)

        if is_active is not None:
            stmt = stmt.where(PriceRule.is_active == is_active)

        stmt = stmt.order_by(PriceRule.priority.desc(), PriceRule.created_at.asc())
        return self.db.execute(stmt).scalars().all()

    def create_rule(
        self,
        tenant_id: uuid.UUID,
        book_id: uuid.UUID,
        rule: PriceRule,
    ) -> PriceRule | None:
        """Create a price rule under a price book owned by the tenant."""
        book = self.get_book(tenant_id, book_id, include_platform_defaults=False)
        if not book:
            return None

        rule.tenant_id = tenant_id
        rule.price_book_id = book_id
        self.db.add(rule)
        self.db.flush()
        return rule

    def update_rule(
        self,
        tenant_id: uuid.UUID,
        rule_id: uuid.UUID,
        data: dict[str, Any] | PriceRuleUpdate,
    ) -> PriceRule | None:
        """Update a price rule belonging to the tenant."""
        rule = self.get_rule(tenant_id, rule_id, include_platform_defaults=False)
        if not rule:
            return None

        update_dict = data.model_dump(exclude_unset=True) if isinstance(data, PriceRuleUpdate) else dict(data)

        immutable_fields = {"id", "tenant_id", "price_book_id"}

        for field, value in update_dict.items():
            if field not in immutable_fields and hasattr(rule, field):
                setattr(rule, field, value)
                # Keep is_active in sync with status if status is updated
                if field == "status" and "is_active" not in update_dict:
                    if str(value).upper() == "INACTIVE":
                        rule.is_active = False
                    elif str(value).upper() == "ACTIVE":
                        rule.is_active = True

        self.db.flush()
        return rule

    def delete_rule(self, tenant_id: uuid.UUID, rule_id: uuid.UUID) -> bool:
        """Delete a price rule belonging to the tenant."""
        rule = self.get_rule(tenant_id, rule_id, include_platform_defaults=False)
        if not rule:
            return False

        self.db.delete(rule)
        self.db.flush()
        return True

    # ========================================================================
    # Calculation Engine Rule Retrieval
    # ========================================================================

    def get_active_rules_for_calculation(
        self,
        tenant_id: uuid.UUID,
        seller_id: uuid.UUID,
        branch_id: uuid.UUID | None = None,
        as_of: datetime | None = None,
    ) -> Sequence[PriceRule]:
        """Fetch all eligible active rules across Branch, Seller, and Platform Default scopes.

        Used directly by PricingCalculatorService for deterministic precedence evaluation.
        Eagerly loads `price_book` to prevent N+1 queries during precedence scoring.
        """
        ref_time = as_of or datetime.now(timezone.utc)

        scope_conditions = [
            # 1. Seller scope book matching the seller
            and_(
                PriceBook.scope == PriceBookScope.SELLER,
                PriceBook.seller_id == seller_id,
            ),
            # 2. Platform default book
            (PriceBook.scope == PriceBookScope.PLATFORM_DEFAULT),
        ]

        # 3. Branch scope book if branch_id is provided
        if branch_id is not None:
            scope_conditions.append(
                and_(
                    PriceBook.scope == PriceBookScope.BRANCH,
                    PriceBook.seller_id == seller_id,
                    PriceBook.branch_id == branch_id,
                )
            )

        stmt = (
            select(PriceRule)
            .join(PriceBook, PriceRule.price_book_id == PriceBook.id)
            .options(joinedload(PriceRule.price_book))
            .where(
                PriceBook.is_active.is_(True),
                PriceBook.status == PriceBookStatus.ACTIVE,
                PriceRule.is_active.is_(True),
                PriceRule.status == "ACTIVE",
                # Tenant isolation: tenant's books OR platform defaults
                or_(
                    PriceBook.tenant_id == tenant_id,
                    and_(
                        PriceBook.tenant_id.is_(None),
                        PriceBook.scope == PriceBookScope.PLATFORM_DEFAULT,
                    ),
                ),
                or_(*scope_conditions),
                # Temporal filtering on PriceRule
                or_(PriceRule.effective_from.is_(None), PriceRule.effective_from <= ref_time),
                or_(PriceRule.effective_to.is_(None), PriceRule.effective_to >= ref_time),
            )
            .order_by(
                PriceBook.priority.desc(),
                PriceRule.priority.desc(),
                PriceRule.created_at.desc(),
            )
        )

        return self.db.execute(stmt).scalars().all()
