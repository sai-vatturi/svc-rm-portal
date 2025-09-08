from __future__ import annotations

from typing import Optional, List, Any, Dict

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.rbac import Role, User
from app.utils.time import utcnow


class RbacRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    # --- helpers ---
    def _oid_to_str(self, v: Any) -> Any:
        return str(v) if isinstance(v, ObjectId) else v

    def _normalize_ids(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        if not doc:
            return doc
        if "_id" in doc:
            doc["_id"] = self._oid_to_str(doc["_id"])  # type: ignore[assignment]
        # Arrays that may contain ObjectIds
        if "role_ids" in doc and isinstance(doc["role_ids"], list):
            doc["role_ids"] = [self._oid_to_str(x) for x in doc["role_ids"]]
        if "assigned_squad_ids" in doc and isinstance(doc["assigned_squad_ids"], list):
            doc["assigned_squad_ids"] = [self._oid_to_str(x) for x in doc["assigned_squad_ids"]]
        # Single references
        if "created_by" in doc:
            doc["created_by"] = self._oid_to_str(doc["created_by"])  # type: ignore[assignment]
        return doc

    def _to_user_model(self, doc: Dict[str, Any]) -> User:
        return User.model_validate(self._normalize_ids(doc))

    def _to_role_model(self, doc: Dict[str, Any]) -> Role:
        return Role.model_validate(self._normalize_ids(doc))

    # --- users ---
    async def create_user(self, user: User) -> User:
        payload = user.model_dump(by_alias=True)
        res = await self.db.users.insert_one(payload)
        payload["_id"] = str(res.inserted_id)
        return self._to_user_model(payload)

    async def find_user_by_username(self, username: str) -> Optional[User]:
        doc = await self.db.users.find_one({"username": username})
        return self._to_user_model(doc) if doc else None

    async def find_user_by_id(self, user_id: str) -> Optional[User]:
        doc = await self.db.users.find_one({"_id": ObjectId(user_id)})
        return self._to_user_model(doc) if doc else None

    # --- roles ---
    async def create_role(self, role: Role) -> Role:
        payload = role.model_dump(by_alias=True)
        res = await self.db.roles.insert_one(payload)
        payload["_id"] = str(res.inserted_id)
        return self._to_role_model(payload)

    async def list_role_names(self, role_ids: list[str]) -> list[str]:
        ids = [ObjectId(rid) for rid in role_ids]
        cursor = self.db.roles.find({"_id": {"$in": ids}}, {"role_name": 1})
        return [doc["role_name"] async for doc in cursor]

    async def get_roles_by_ids(self, role_ids: List[str]) -> List[Role]:
        ids = [ObjectId(rid) for rid in role_ids]
        cursor = self.db.roles.find({"_id": {"$in": ids}})
        roles: List[Role] = []
        async for doc in cursor:
            roles.append(self._to_role_model(doc))
        return roles

    async def list_roles(self) -> List[Role]:
        roles: List[Role] = []
        async for doc in self.db.roles.find().sort("role_name"):
            roles.append(self._to_role_model(doc))
        return roles

    async def get_role_by_id(self, role_id: str) -> Optional[Role]:
        doc = await self.db.roles.find_one({"_id": ObjectId(role_id)})
        return self._to_role_model(doc) if doc else None
