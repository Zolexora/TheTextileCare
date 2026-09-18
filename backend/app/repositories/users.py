from __future__ import annotations

import uuid

from sqlalchemy import select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_auth_user_id(self, auth_user_id: str) -> User | None:
        stmt = select(User).where(User.auth_user_id == auth_user_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(
        self,
        email: str,
        auth_user_id: str,
        name: str | None = None,
        status: str = 'ACTIVE',
    ) -> User:
        user = User(
            email=email,
            auth_user_id=auth_user_id,
            name=name,
            status=status,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_or_get(
        self,
        email: str,
        auth_user_id: str,
        name: str | None = None,
        status: str = 'ACTIVE',
    ) -> User:
        user = self.get_by_auth_user_id(auth_user_id)
        if user:
            return user
        user = self.get_by_email(email)
        if user:
            # Sync auth_user_id if needed
            if user.auth_user_id != auth_user_id:
                user.auth_user_id = auth_user_id
                self.db.commit()
                self.db.refresh(user)
            return user
        return self.create(email=email, auth_user_id=auth_user_id, name=name, status=status)

    def update(self, user: User, **kwargs) -> User:
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        self.db.commit()
        self.db.refresh(user)
        return user
