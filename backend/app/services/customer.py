from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.customer import Customer, CustomerAddress, CustomerSeller
from app.repositories.customer import CustomerRepository
from app.services.audit import AuditService


class CustomerService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CustomerRepository(db)
        self.audit = AuditService(db)

    def get_or_create_profile(self, user_id: uuid.UUID, email: str | None = None, name: str | None = None) -> Customer:
        customer = self.repo.get_by_user_id(user_id)
        if not customer:
            customer = self.repo.create_customer(user_id=user_id, email=email, display_name=name)
            self.audit.log_event(
                event_type='CUSTOMER_CREATED',
                tenant_id=None,
                actor_user_id=user_id,
                entity_type='customer',
                entity_id=str(customer.id),
                payload={'user_id': str(user_id)}
            )
        return customer

    def update_profile(self, user_id: uuid.UUID, **kwargs) -> Customer:
        customer = self.get_or_create_profile(user_id)
        updated = self.repo.update_customer(customer.id, **kwargs)
        self.audit.log_event(
            event_type='CUSTOMER_UPDATED',
            tenant_id=None,
            actor_user_id=user_id,
            entity_type='customer',
            entity_id=str(updated.id),
            payload={'updates': list(kwargs.keys())}
        )
        return updated

    def list_addresses(self, user_id: uuid.UUID) -> Sequence[CustomerAddress]:
        customer = self.get_or_create_profile(user_id)
        return self.repo.list_addresses(customer.id)

    def create_address(self, user_id: uuid.UUID, **kwargs) -> CustomerAddress:
        customer = self.get_or_create_profile(user_id)
        address = self.repo.create_address(customer.id, **kwargs)
        self.audit.log_event(
            event_type='CUSTOMER_ADDRESS_CREATED',
            tenant_id=None,
            actor_user_id=user_id,
            entity_type='customer_address',
            entity_id=str(address.id),
            payload={'label': address.label}
        )
        return address

    def update_address(self, user_id: uuid.UUID, address_id: uuid.UUID, **kwargs) -> CustomerAddress:
        customer = self.get_or_create_profile(user_id)
        address = self.repo.update_address(customer.id, address_id, **kwargs)
        if not address:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
            
        self.audit.log_event(
            event_type='CUSTOMER_ADDRESS_UPDATED',
            tenant_id=None,
            actor_user_id=user_id,
            entity_type='customer_address',
            entity_id=str(address.id),
            payload={'updates': list(kwargs.keys())}
        )
        return address

    def delete_address(self, user_id: uuid.UUID, address_id: uuid.UUID) -> None:
        customer = self.get_or_create_profile(user_id)
        success = self.repo.delete_address(customer.id, address_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Address not found")
            
        self.audit.log_event(
            event_type='CUSTOMER_ADDRESS_DELETED',
            tenant_id=None,
            actor_user_id=user_id,
            entity_type='customer_address',
            entity_id=str(address_id),
            payload=None
        )

    def link_seller(self, user_id: uuid.UUID, seller_id: uuid.UUID) -> CustomerSeller:
        # NOTE: A real implementation might also check if the seller exists and is published, 
        # but the repository layer allows creation directly. We assume validation is done upstream.
        customer = self.get_or_create_profile(user_id)
        rel = self.repo.link_seller(customer.id, seller_id)
        self.audit.log_event(
            event_type='CUSTOMER_SELLER_LINKED',
            tenant_id=None, # Relationship spans tenant boundary, log at platform level
            actor_user_id=user_id,
            entity_type='customer_seller',
            entity_id=str(rel.id),
            payload={'seller_id': str(seller_id)}
        )
        return rel
