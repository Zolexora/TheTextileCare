from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.users import UserRepository


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_repo = UserRepository(db)

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.user_repo.get_by_id(user_id)

    def get_by_auth_user_id(self, auth_user_id: str) -> User | None:
        return self.user_repo.get_by_auth_user_id(auth_user_id)

    def create_or_get(
        self,
        email: str,
        auth_user_id: str,
        name: str | None = None,
        status: str = 'ACTIVE',
    ) -> User:
        return self.user_repo.create_or_get(
            email=email,
            auth_user_id=auth_user_id,
            name=name,
            status=status,
        )
