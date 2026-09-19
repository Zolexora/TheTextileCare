from __future__ import annotations

import uuid
from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_db, require_authenticated_user
from app.models.user import User
from app.schemas.customer import (
    CustomerAddressCreate,
    CustomerAddressResponse,
    CustomerAddressUpdate,
    CustomerProfileResponse,
    CustomerProfileUpdate,
    CustomerSellerLinkResponse,
)
from app.services.customer import CustomerService

router = APIRouter(tags=['customer'])


@router.get('/profile', response_model=CustomerProfileResponse)
def get_customer_profile(
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
) -> CustomerProfileResponse:
    svc = CustomerService(db)
    return svc.get_or_create_profile(user.id, user.email, user.name)


@router.patch('/profile', response_model=CustomerProfileResponse)
def update_customer_profile(
    update: CustomerProfileUpdate,
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
) -> CustomerProfileResponse:
    svc = CustomerService(db)
    return svc.update_profile(user.id, **update.model_dump(exclude_unset=True))


@router.get('/addresses', response_model=list[CustomerAddressResponse])
def list_customer_addresses(
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
) -> Sequence[CustomerAddressResponse]:
    svc = CustomerService(db)
    return svc.list_addresses(user.id)


@router.post('/addresses', response_model=CustomerAddressResponse, status_code=status.HTTP_201_CREATED)
def create_customer_address(
    address: CustomerAddressCreate,
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
) -> CustomerAddressResponse:
    svc = CustomerService(db)
    return svc.create_address(user.id, **address.model_dump())


@router.patch('/addresses/{address_id}', response_model=CustomerAddressResponse)
def update_customer_address(
    address_id: uuid.UUID,
    update: CustomerAddressUpdate,
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
) -> CustomerAddressResponse:
    svc = CustomerService(db)
    return svc.update_address(user.id, address_id, **update.model_dump(exclude_unset=True))


@router.delete('/addresses/{address_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_customer_address(
    address_id: uuid.UUID,
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
) -> None:
    svc = CustomerService(db)
    svc.delete_address(user.id, address_id)


@router.post('/sellers/{seller_id}/link', response_model=CustomerSellerLinkResponse)
def link_customer_seller(
    seller_id: uuid.UUID,
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db)
) -> CustomerSellerLinkResponse:
    svc = CustomerService(db)
    return svc.link_seller(user.id, seller_id)
