from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user, require_permissions
from app.models.rbac import Role, User, UserCreate
from app.repositories.rbac_repo import RbacRepository
from app.db.client import get_db
from app.services.rbac_service import AuthService
from app.utils.time import utcnow

router = APIRouter()


def repo() -> RbacRepository:
    return RbacRepository(get_db())


def auth_service() -> AuthService:
    return AuthService()


@router.post("/rbac/roles", response_model=Role, summary="Create role")
async def create_role(payload: Role, _: dict = Depends(require_permissions("can_manage_roles"))):
    r = await repo().create_role(payload)
    return r


@router.get("/rbac/roles", response_model=list[Role], summary="List roles")
async def list_roles():
    return await repo().list_roles()


@router.post("/rbac/users", response_model=User, summary="Create user with roles")
async def create_user(payload: UserCreate, _ = Depends(require_permissions("can_manage_roles")), svc: AuthService = Depends(auth_service)):
    user = await svc.register_user(payload)
    return user


@router.get("/rbac/users/{user_id}", response_model=User, summary="Get user by id")
async def get_user(user_id: str):
    u = await repo().find_user_by_id(user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return u


@router.get("/rbac/me", summary="Current user profile")
async def me(principal = Depends(get_current_user)):
    user = principal.user
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "email": user.email,
        "roles": principal.role_names,
        "permissions": principal.permissions,
    }
