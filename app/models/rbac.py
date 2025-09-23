from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict

from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field
from pydantic.config import ConfigDict


# Central permission descriptor map (can be served to frontend)
PERMISSION_DESCRIPTORS: Dict[str, str] = {
    "is_approval_manager": "Can approve releases and gate outcomes.",
    "can_create_release": "Create new releases.",
    "can_edit_release_description": "Edit release description/metadata.",
    "can_define_fixed_versions": "Define or edit fixed version mappings.",
    "can_manage_runbooks": "Create/update/delete runbook steps.",
    "can_manage_quality_gates": "Add or modify quality gates.",
    "can_upload_attachments": "Upload and delete attachments.",
    "can_manage_roles": "Create/update/delete roles & manage permissions.",
    "can_invite_users": "Invite/register new users (admin bootstrap).",
    "can_view_all": "Override scoping – view all entities.",
}


class Role(BaseModel):
    model_config = ConfigDict(populate_by_name=True, json_encoders={ObjectId: str})

    id: Optional[str] = Field(default=None, alias="_id")
    role_name: str
    description: Optional[str] = None
    is_approval_manager: bool = False
    can_create_release: bool = False
    can_edit_release_description: bool = False
    can_define_fixed_versions: bool = False
    can_manage_runbooks: bool = False
    can_manage_quality_gates: bool = False
    can_upload_attachments: bool = False
    can_manage_roles: bool = False
    can_invite_users: bool = False
    can_view_all: bool = False
    created_by: Optional[str] = None
    created_at: datetime


class User(BaseModel):
    model_config = ConfigDict(populate_by_name=True, json_encoders={ObjectId: str})

    id: Optional[str] = Field(default=None, alias="_id")
    username: str
    full_name: Optional[str] = None
    email: EmailStr
    password_hash: str
    role_ids: List[str] = []
    assigned_squad_ids: List[str] = []
    created_at: datetime


class UserCreate(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "username": "jdoe",
            "full_name": "Jane Doe",
            "email": "jdoe@example.com",
            "password": "StrongP@ssw0rd",
            "role_ids": []
        }
    })

    username: str
    full_name: Optional[str] = None
    email: EmailStr
    password: str
    role_ids: List[str] = []


class UserLogin(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {"username": "admin", "password": "admin123"}
    })

    username: str
    password: str


class TokenPair(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer"
        }
    })

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserPublic(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "64f9b8c1f1e4a9fd1a2b3c4d",
            "username": "admin",
            "full_name": "Admin User",
            "email": "admin@example.com",
            "roles": ["Release Manager"],
            "assigned_squad_ids": []
        }
    })

    id: str
    username: str
    full_name: Optional[str] = None
    email: EmailStr
    roles: List[str] = []
    assigned_squad_ids: List[str] = []


class RoleUpdate(BaseModel):
    """Fields allowed for partial update of a role."""
    description: Optional[str] = None
    is_approval_manager: Optional[bool] = None
    can_create_release: Optional[bool] = None
    can_edit_release_description: Optional[bool] = None
    can_define_fixed_versions: Optional[bool] = None
    can_manage_runbooks: Optional[bool] = None
    can_manage_quality_gates: Optional[bool] = None
    can_upload_attachments: Optional[bool] = None
    can_manage_roles: Optional[bool] = None
    can_invite_users: Optional[bool] = None
    can_view_all: Optional[bool] = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "description": "Broader admin permissions",
            "can_manage_quality_gates": True,
            "can_manage_roles": True
        }
    })


class UserUpdate(BaseModel):
    """Fields allowed for partial update of a user."""
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role_ids: Optional[List[str]] = None
    assigned_squad_ids: Optional[List[str]] = None

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "full_name": "Jane Q. Doe",
            "role_ids": ["64f9b8c1f1e4a9fd1a2b3c4d"],
            "assigned_squad_ids": ["64f9b8c1f1e4a9fd1a2b3c4e"]
        }
    })


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class PasswordReset(BaseModel):
    new_password: str
