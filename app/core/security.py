from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.repositories.rbac_repo import RbacRepository
from app.db.client import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    now = datetime.now(tz=timezone.utc)
    payload: Dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "type": token_type,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def create_access_token(subject: str) -> str:
    return create_token(subject, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), token_type="access")


def create_refresh_token(subject: str) -> str:
    return create_token(subject, timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES), token_type="refresh")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
    except JWTError:
        return None


class CurrentPrincipal:
    def __init__(self, user, role_names: list[str], permissions: dict[str, bool]) -> None:  # type: ignore[no-untyped-def]
        self.user = user
        self.role_names = role_names
        self.permissions = permissions


async def get_current_user(authorization: str | None = Header(default=None)) -> CurrentPrincipal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    repo = RbacRepository(get_db())
    user = await repo.find_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    roles = await repo.get_roles_by_ids(user.role_ids)
    role_names = [r.role_name for r in roles]

    # Aggregate permissions across roles (OR)
    flags = [
        "is_approval_manager",
        "can_create_release",
        "can_edit_release_description",
        "can_define_fixed_versions",
        "can_manage_runbooks",
        "can_manage_quality_gates",
        "can_upload_attachments",
        "can_manage_roles",
        "can_invite_users",
        "can_view_all",
    ]
    if not settings.RBAC_ENFORCEMENT_ENABLED:
        # Grant everything in permissive phase
        perms: dict[str, bool] = {f: True for f in flags}
    else:
        perms = {f: False for f in flags}
        for r in roles:
            for f in flags:
                if getattr(r, f, False):
                    perms[f] = True

    return CurrentPrincipal(user=user, role_names=role_names, permissions=perms)


def require_permissions(*required_flags: str):
    async def _checker(principal: CurrentPrincipal = Depends(get_current_user)) -> CurrentPrincipal:
        if settings.RBAC_ENFORCEMENT_ENABLED:
            missing = [f for f in required_flags if not principal.permissions.get(f, False)]
            if missing:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: missing permissions")
        return principal

    return _checker
