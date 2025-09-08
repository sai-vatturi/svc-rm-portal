from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.config import settings
from app.core.errors import ErrorCodes, error_response
from app.core.security import decode_token, create_access_token, create_refresh_token
from app.models.rbac import TokenPair, UserCreate, UserLogin, User
from app.services.rbac_service import AuthService

router = APIRouter()


def get_auth_service() -> AuthService:
    return AuthService()


@router.post("/register", response_model=User, summary="Register user (admin/seed only)")
async def register_user(payload: UserCreate, svc: AuthService = Depends(get_auth_service)):
    if not settings.ADMIN_REGISTRATION_ENABLED:
        return error_response(status_code=403, code=ErrorCodes.FORBIDDEN, message="Registration disabled")
    user = await svc.register_user(payload)
    # Return created user (admin-only endpoint). In a real system, exclude password_hash from schema.
    return user


@router.post("/login", response_model=TokenPair, summary="Login and get tokens")
async def login(payload: UserLogin, svc: AuthService = Depends(get_auth_service)):
    username = payload.username
    password = payload.password
    if not username or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="username and password required")

    tokens = await svc.authenticate(username, password)
    if not tokens:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return tokens


@router.post("/refresh", response_model=TokenPair, summary="Refresh access token")
async def refresh(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")
    return TokenPair(access_token=create_access_token(user_id), refresh_token=create_refresh_token(user_id))
