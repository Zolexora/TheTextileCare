from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.permissions.constants import PermissionName
from app.db import get_db
from app.dependencies import require_permission
from app.schemas.role import PermissionResponse, RoleResponse
from app.services.roles import RoleService

router = APIRouter(prefix='/roles', tags=['roles'])


@router.get(
    '', response_model=list[RoleResponse], summary='List available platform and tenant roles'
)
async def list_roles(
    _context=Depends(require_permission(PermissionName.ROLE_READ.value)),
    db: Session = Depends(get_db),
) -> list[RoleResponse]:
    role_service = RoleService(db)
    roles = role_service.list_roles()
    result = []
    for r in roles:
        result.append(
            RoleResponse(
                id=r.id,
                name=r.name,
                description=r.description,
                is_platform_role=r.is_platform_role,
                created_at=r.created_at,
                permissions=[PermissionResponse.model_validate(p) for p in r.permissions],
            )
        )
    return result
