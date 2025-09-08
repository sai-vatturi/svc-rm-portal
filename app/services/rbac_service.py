from __future__ import annotations

from typing import Optional

from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.db.client import get_db
from app.models.rbac import TokenPair, User, UserCreate
from app.repositories.rbac_repo import RbacRepository
from app.utils.time import utcnow


class AuthService:
    def __init__(self) -> None:
        # Defer DB access until methods are called
        pass

    def _repo(self) -> RbacRepository:
        return RbacRepository(get_db())

    async def register_user(self, payload: UserCreate) -> User:
        user = User(
            username=payload.username,
            full_name=payload.full_name,
            email=payload.email,
            password_hash=hash_password(payload.password),
            role_ids=payload.role_ids,
            assigned_squad_ids=[],
            created_at=utcnow(),
        )
        return await self._repo().create_user(user)

    async def authenticate(self, username: str, password: str) -> Optional[TokenPair]:
        user = await self._repo().find_user_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        access = create_access_token(str(user.id))
        refresh = create_refresh_token(str(user.id))
        return TokenPair(access_token=access, refresh_token=refresh)
