from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.config import settings
from app.core.errors import ErrorCodes, error_response
from app.core.security import decode_token, create_access_token, create_refresh_token, get_current_user, hash_password, verify_password
from app.models.rbac import TokenPair, UserCreate, UserLogin, User, UserPublic, PasswordChange, PasswordReset
from app.services.rbac_service import AuthService
from app.repositories.rbac_repo import RbacRepository
from app.db.client import get_db

router = APIRouter()


def get_auth_service() -> AuthService:
    return AuthService()


def repo() -> RbacRepository:
    return RbacRepository(get_db())


@router.post("/register", response_model=UserPublic, summary="Register user (admin/seed only)")
async def register_user(payload: UserCreate, svc: AuthService = Depends(get_auth_service)):
    if not settings.ADMIN_REGISTRATION_ENABLED:
        return error_response(status_code=403, code=ErrorCodes.FORBIDDEN, message="Registration disabled")
    user = await svc.register_user(payload)
    roles = []
    return UserPublic(id=str(user.id), username=user.username, full_name=user.full_name, email=user.email, roles=roles, assigned_squad_ids=user.assigned_squad_ids)


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


@router.post("/logout", summary="Logout (stateless placeholder)")
async def logout():
    # With stateless JWT, logout is client-side (discard tokens). Placeholder for future blacklist.
    return {"message": "Logged out (client should discard tokens)."}


@router.post("/change-password", summary="Change password for current user")
async def change_password(payload: PasswordChange, principal = Depends(get_current_user)):
    user = principal.user
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Old password incorrect")
    new_hash = hash_password(payload.new_password)
    await repo().update_user(str(user.id), type("Patch", (), {"model_dump": lambda self, **_: {"password_hash": new_hash}})())  # minimal patch injection
    return {"message": "Password changed"}


@router.post("/reset-password/{user_id}", summary="Admin reset another user's password")
async def reset_password(user_id: str, payload: PasswordReset, principal = Depends(get_current_user)):
    # Basic permission gate: require manage roles
    if not principal.permissions.get("can_manage_roles"):
        raise HTTPException(status_code=403, detail="Forbidden")
    new_hash = hash_password(payload.new_password)
    updated = await repo().update_user(user_id, type("Patch", (), {"model_dump": lambda self, **_: {"password_hash": new_hash}})())
    if not updated:
        raise HTTPException(status_code=404, detail="Not found")
    return {"message": "Password reset"}
