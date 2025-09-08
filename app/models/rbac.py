from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, EmailStr, Field
from pydantic.config import ConfigDict


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
            "roles": ["Release Manager"]
        }
    })

    id: str
    username: str
    full_name: Optional[str] = None
    email: EmailStr
    roles: List[str] = []
