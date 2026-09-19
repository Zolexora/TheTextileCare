from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select, update, func
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from app.models.customer import Customer, CustomerAddress, CustomerSeller
from app.repositories.base import BaseRepository


class CustomerRepository(BaseRepository):
    
    def get_by_user_id(self, user_id: uuid.UUID) -> Customer | None:
        """Get customer profile by platform user_id."""
        stmt = select(Customer).where(Customer.user_id == user_id)
        return self.db.execute(stmt).scalar_one_or_none()
    
    def create_customer(self, user_id: uuid.UUID, **kwargs) -> Customer:
        """Create a new customer profile."""
        customer = Customer(user_id=user_id, **kwargs)
        self.db.add(customer)
        self.db.flush()
        return customer
    
    def update_customer(self, customer_id: uuid.UUID, **kwargs) -> Customer:
        """Update an existing customer profile."""
        if not kwargs:
            return self.get_by_id(customer_id)
        
        stmt = update(Customer).where(Customer.id == customer_id).values(**kwargs)
        self.db.execute(stmt)
        self.db.flush()
        return self.get_by_id(customer_id)

    def get_by_id(self, customer_id: uuid.UUID) -> Customer | None:
        stmt = select(Customer).where(Customer.id == customer_id)
        return self.db.execute(stmt).scalar_one_or_none()

    # Address Management
    def list_addresses(self, customer_id: uuid.UUID) -> Sequence[CustomerAddress]:
        stmt = select(CustomerAddress).where(
            CustomerAddress.customer_id == customer_id
        ).order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at.desc())
        return self.db.execute(stmt).scalars().all()
    
    def get_address(self, customer_id: uuid.UUID, address_id: uuid.UUID) -> CustomerAddress | None:
        stmt = select(CustomerAddress).where(
            CustomerAddress.customer_id == customer_id,
            CustomerAddress.id == address_id
        )
        return self.db.execute(stmt).scalar_one_or_none()
    
    def create_address(self, customer_id: uuid.UUID, **kwargs) -> CustomerAddress:
        if kwargs.get('is_default'):
            self._clear_default_address(customer_id)
        
        # If this is their first address, make it default automatically
        if not kwargs.get('is_default'):
            count_stmt = select(func.count()).select_from(CustomerAddress).where(CustomerAddress.customer_id == customer_id)
            count = self.db.execute(count_stmt).scalar()
            if count == 0:
                kwargs['is_default'] = True

        address = CustomerAddress(customer_id=customer_id, **kwargs)
        self.db.add(address)
        self.db.flush()
        return address
    
    def update_address(self, customer_id: uuid.UUID, address_id: uuid.UUID, **kwargs) -> CustomerAddress | None:
        address = self.get_address(customer_id, address_id)
        if not address:
            return None
            
        if kwargs.get('is_default') and not address.is_default:
            self._clear_default_address(customer_id)
            
        for k, v in kwargs.items():
            setattr(address, k, v)
            
        self.db.flush()
        return address
        
    def delete_address(self, customer_id: uuid.UUID, address_id: uuid.UUID) -> bool:
        address = self.get_address(customer_id, address_id)
        if not address:
            return False
            
        was_default = address.is_default
        self.db.delete(address)
        self.db.flush()
        
        # Re-assign default if we deleted the default one
        if was_default:
            first_remaining = self.db.execute(
                select(CustomerAddress)
                .where(CustomerAddress.customer_id == customer_id)
                .order_by(CustomerAddress.created_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            if first_remaining:
                first_remaining.is_default = True
                self.db.flush()
                
        return True

    def _clear_default_address(self, customer_id: uuid.UUID) -> None:
        stmt = update(CustomerAddress).where(
            CustomerAddress.customer_id == customer_id,
            CustomerAddress.is_default == True
        ).values(is_default=False)
        self.db.execute(stmt)

    # Customer-Seller Relationships
    def get_seller_relationship(self, customer_id: uuid.UUID, seller_id: uuid.UUID) -> CustomerSeller | None:
        stmt = select(CustomerSeller).where(
            CustomerSeller.customer_id == customer_id,
            CustomerSeller.seller_id == seller_id
        )
        return self.db.execute(stmt).scalar_one_or_none()
        
    def link_seller(self, customer_id: uuid.UUID, seller_id: uuid.UUID) -> CustomerSeller:
        rel = self.get_seller_relationship(customer_id, seller_id)
        if rel:
            rel.last_interaction_at = func.now()
            self.db.flush()
            return rel
            
        rel = CustomerSeller(customer_id=customer_id, seller_id=seller_id)
        self.db.add(rel)
        self.db.flush()
        return rel
