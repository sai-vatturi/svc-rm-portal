from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user, require_permissions
from app.models.rbac import Role, User, UserCreate, RoleUpdate, UserUpdate, UserPublic, PERMISSION_DESCRIPTORS
from app.repositories.rbac_repo import RbacRepository
from app.db.client import get_db
from app.services.rbac_service import AuthService

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


@router.get("/rbac/roles/{role_id}", response_model=Role, summary="Get role by id")
async def get_role(role_id: str):
    r = await repo().get_role_by_id(role_id)
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return r


@router.patch("/rbac/roles/{role_id}", response_model=Role, summary="Update role (partial)")
async def update_role(role_id: str, patch: RoleUpdate, _=Depends(require_permissions("can_manage_roles"))):
    r = await repo().update_role(role_id, patch)
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return r


@router.delete("/rbac/roles/{role_id}", summary="Delete role")
async def delete_role(role_id: str, _=Depends(require_permissions("can_manage_roles"))):
    deleted = await repo().delete_role(role_id)
    if deleted == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return {"deleted": deleted}


@router.post("/rbac/users", response_model=User, summary="Create user with roles")
async def create_user(payload: UserCreate, _ = Depends(require_permissions("can_manage_roles")), svc: AuthService = Depends(auth_service)):
    user = await svc.register_user(payload)
    return user


@router.get("/rbac/users", response_model=list[User], summary="List users (limited)")
async def list_users(skip: int = 0, limit: int = 50, _=Depends(require_permissions("can_manage_roles"))):
    users = await repo().list_users(skip=skip, limit=limit)
    return users


@router.get("/rbac/users/{user_id}", response_model=User, summary="Get user by id")
async def get_user(user_id: str, _=Depends(require_permissions("can_manage_roles"))):
    u = await repo().find_user_by_id(user_id)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return u


@router.patch("/rbac/users/{user_id}", response_model=User, summary="Update user (partial)")
async def update_user(user_id: str, patch: UserUpdate, _=Depends(require_permissions("can_manage_roles"))):
    u = await repo().update_user(user_id, patch)
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return u


@router.delete("/rbac/users/{user_id}", summary="Delete user")
async def delete_user(user_id: str, _=Depends(require_permissions("can_manage_roles"))):
    deleted = await repo().delete_user(user_id)
    if deleted == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return {"deleted": deleted}


@router.get("/rbac/permissions-matrix", summary="List permission flags and descriptions")
async def permissions_matrix(_=Depends(require_permissions("can_manage_roles"))):
    return PERMISSION_DESCRIPTORS


@router.post("/rbac/users/{user_id}/roles/{role_id}", summary="Assign role to user")
async def assign_role(user_id: str, role_id: str, _=Depends(require_permissions("can_manage_roles"))):
    user = await repo().find_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if role_id not in user.role_ids:
        user.role_ids.append(role_id)
        await repo().update_user(user_id, type("Patch", (), {"model_dump": lambda self, **_: {"role_ids": user.role_ids}})())
    return {"roles": user.role_ids}


@router.delete("/rbac/users/{user_id}/roles/{role_id}", summary="Remove role from user")
async def remove_role(user_id: str, role_id: str, _=Depends(require_permissions("can_manage_roles"))):
    user = await repo().find_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if role_id in user.role_ids:
        user.role_ids = [r for r in user.role_ids if r != role_id]
        await repo().update_user(user_id, type("Patch", (), {"model_dump": lambda self, **_: {"role_ids": user.role_ids}})())
    return {"roles": user.role_ids}


@router.get("/rbac/me", response_model=UserPublic, summary="Current user profile")
async def me(principal = Depends(get_current_user)):
    user = principal.user
    return UserPublic(
        id=str(user.id),
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        roles=principal.role_names,
        assigned_squad_ids=user.assigned_squad_ids,
    )
