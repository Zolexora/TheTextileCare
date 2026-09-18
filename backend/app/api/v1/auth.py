from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import require_authenticated_user
from app.models.user import User
from app.repositories.memberships import MembershipRepository
from app.repositories.tenants import TenantRepository
from app.schemas.auth import AuthMeResponse
from app.schemas.membership import MembershipResponse
from app.schemas.tenant import TenantResponse
from app.schemas.user import UserResponse

router = APIRouter(prefix='/auth', tags=['auth'])


@router.get('/me', response_model=AuthMeResponse, summary='Get current authenticated user identity')
async def get_me(
    current_user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> AuthMeResponse:
    tenant_repo = TenantRepository(db)
    membership_repo = MembershipRepository(db)

    tenants = tenant_repo.list_for_user(current_user.id)
    memberships = membership_repo.list_for_user(current_user.id)

    membership_responses = [
        MembershipResponse(
            id=m.id,
            tenant_id=m.tenant_id,
            user_id=m.user_id,
            role_id=m.role_id,
            role=m.role.name,
            status=m.status,
            email=current_user.email,
            name=current_user.name,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
        for m in memberships
    ]

    return AuthMeResponse(
        user=UserResponse.model_validate(current_user),
        tenants=[TenantResponse.model_validate(t) for t in tenants],
        memberships=membership_responses,
    )
