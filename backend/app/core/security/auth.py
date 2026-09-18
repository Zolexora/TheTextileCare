from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.exceptions.base import ApiError
from app.models.user import User
from app.repositories.users import UserRepository

settings = get_settings()


def extract_identity_from_token(token: str) -> dict[str, Any] | None:
    try:
        # Try decoding with secret
        payload = jwt.decode(token, settings.auth_secret, algorithms=['HS256'])
        return payload
    except JWTError:
        # In test / dev environments, allow unverified payload or mock tokens
        if settings.app_env in {'development', 'test'}:
            try:
                # Try decode without signature verification
                payload = jwt.get_unverified_claims(token)
                return payload
            except (JWTError, ValueError):
                # If it's a simple test token like "auth-test@example.com"
                if token.startswith('auth-') or '@' in token:
                    return {'sub': token, 'email': token.replace('auth-', '')}
        return None


def get_current_user(request: Request, db: Session) -> User:
    auth_header = request.headers.get('Authorization') or request.headers.get('authorization')
    auth_user_id: str | None = None
    email: str | None = None
    name: str | None = None
    explicit_user_id: uuid.UUID | None = None

    if auth_header and auth_header.startswith('Bearer '):
        token = auth_header[7:].strip()
        payload = extract_identity_from_token(token)
        if not payload:
            raise ApiError(
                status_code=401,
                code='INVALID_TOKEN',
                message='Invalid or expired authentication token.',
            )
        auth_user_id = str(payload.get('sub') or payload.get('id') or payload.get('user_id'))
        email = payload.get('email')
        name = payload.get('name') or payload.get('user_metadata', {}).get('name')
        if not email and '@' in auth_user_id:
            email = auth_user_id

    # Allow X-User-Id / X-Auth-User-Id in development or test environments
    if not auth_user_id and settings.app_env in {'development', 'test'}:
        x_user_id = request.headers.get('X-User-Id') or request.headers.get('x-user-id')
        x_auth_id = request.headers.get('X-Auth-User-Id') or request.headers.get('x-auth-user-id')
        x_email = request.headers.get('X-User-Email') or request.headers.get('x-user-email')

        if x_user_id:
            try:
                explicit_user_id = uuid.UUID(x_user_id)
            except ValueError:
                auth_user_id = x_user_id
        elif x_auth_id:
            auth_user_id = x_auth_id
        elif x_email:
            email = x_email
            auth_user_id = f'auth-{x_email}'

    if not auth_user_id and not explicit_user_id and not email:
        raise ApiError(
            status_code=401,
            code='UNAUTHORIZED',
            message='Authentication credentials were not provided.',
        )

    user_repo = UserRepository(db)
    user: User | None = None

    if explicit_user_id:
        user = user_repo.get_by_id(explicit_user_id)
        if not user:
            # Check if explicit_user_id is auth_user_id
            user = user_repo.get_by_auth_user_id(str(explicit_user_id))

    if not user and auth_user_id:
        user = user_repo.get_by_auth_user_id(auth_user_id)

    if not user and email:
        user = user_repo.get_by_email(email)

    if not user:
        # Auto-provision platform user record if we have an authenticated identity
        if auth_user_id or email:
            resolved_email = email or f'{auth_user_id}@example.com'
            resolved_auth_id = auth_user_id or f'auth-{resolved_email}'
            user = user_repo.create_or_get(
                email=resolved_email,
                auth_user_id=resolved_auth_id,
                name=name,
                status='ACTIVE',
            )
        else:
            raise ApiError(
                status_code=401,
                code='USER_NOT_FOUND',
                message='User identity could not be verified.',
            )

    if user.status != 'ACTIVE':
        raise ApiError(
            status_code=403,
            code='USER_SUSPENDED',
            message='User account is suspended or inactive.',
        )

    return user
