from __future__ import annotations

from typing import List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.models.catalog import Application, JiraBoard, Squad


class CatalogRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db

    async def create_application(self, app: Application) -> Application | None:
        payload = app.model_dump(by_alias=True)
        try:
            res = await self.db.applications.insert_one(payload)
        except DuplicateKeyError:
            return None
        payload["_id"] = res.inserted_id
        return Application.model_validate(payload)

    async def list_applications(self) -> List[Application]:
        items: List[Application] = []
        async for doc in self.db.applications.find().sort("application_id"):
            items.append(Application.model_validate(doc))
        return items

    async def get_application(self, id_or_key: str) -> Application | None:
        # Try by ObjectId then by application_id
        doc = None
        try:
            doc = await self.db.applications.find_one({"_id": ObjectId(id_or_key)})
        except Exception:
            pass
        if not doc:
            doc = await self.db.applications.find_one({"application_id": id_or_key})
        return Application.model_validate(doc) if doc else None

    async def update_application(self, oid: str, patch: dict) -> Application | None:
        sets = {k: v for k, v in patch.items() if v is not None}
        if not sets:
            doc = await self.db.applications.find_one({"_id": ObjectId(oid)})
            return Application.model_validate(doc) if doc else None
        res = await self.db.applications.update_one({"_id": ObjectId(oid)}, {"$set": sets})
        if res.matched_count == 0:
            return None
        doc = await self.db.applications.find_one({"_id": ObjectId(oid)})
        return Application.model_validate(doc) if doc else None

    async def delete_application(self, oid: str) -> int:
        res = await self.db.applications.delete_one({"_id": ObjectId(oid)})
        return res.deleted_count

    async def create_squad(self, squad: Squad) -> Squad | None:
        payload = squad.model_dump(by_alias=True)
        try:
            res = await self.db.squads.insert_one(payload)
        except DuplicateKeyError:
            return None
        payload["_id"] = res.inserted_id
        return Squad.model_validate(payload)

    async def list_squads(self) -> List[Squad]:
        items: List[Squad] = []
        async for doc in self.db.squads.find().sort("squad_id"):
            items.append(Squad.model_validate(doc))
        return items

    async def get_squad(self, id_or_key: str) -> Squad | None:
        doc = None
        try:
            doc = await self.db.squads.find_one({"_id": ObjectId(id_or_key)})
        except Exception:
            pass
        if not doc:
            doc = await self.db.squads.find_one({"squad_id": id_or_key})
        return Squad.model_validate(doc) if doc else None

    async def update_squad(self, oid: str, patch: dict) -> Squad | None:
        sets = {k: v for k, v in patch.items() if v is not None}
        if not sets:
            doc = await self.db.squads.find_one({"_id": ObjectId(oid)})
            return Squad.model_validate(doc) if doc else None
        res = await self.db.squads.update_one({"_id": ObjectId(oid)}, {"$set": sets})
        if res.matched_count == 0:
            return None
        doc = await self.db.squads.find_one({"_id": ObjectId(oid)})
        return Squad.model_validate(doc) if doc else None

    async def delete_squad(self, oid: str) -> int:
        res = await self.db.squads.delete_one({"_id": ObjectId(oid)})
        return res.deleted_count

    async def create_board(self, board: JiraBoard) -> JiraBoard | None:
        payload = board.model_dump(by_alias=True)
        try:
            res = await self.db.jiraboards.insert_one(payload)
        except DuplicateKeyError:
            return None
        payload["_id"] = res.inserted_id
        return JiraBoard.model_validate(payload)

    async def list_boards(self) -> List[JiraBoard]:
        items: List[JiraBoard] = []
        async for doc in self.db.jiraboards.find().sort("board_id"):
            items.append(JiraBoard.model_validate(doc))
        return items

    async def get_board(self, id_or_key: str) -> JiraBoard | None:
        doc = None
        try:
            doc = await self.db.jiraboards.find_one({"_id": ObjectId(id_or_key)})
        except Exception:
            pass
        if not doc:
            doc = await self.db.jiraboards.find_one({"board_id": id_or_key})
        return JiraBoard.model_validate(doc) if doc else None

    async def update_board(self, oid: str, patch: dict) -> JiraBoard | None:
        sets = {k: v for k, v in patch.items() if v is not None}
        if not sets:
            doc = await self.db.jiraboards.find_one({"_id": ObjectId(oid)})
            return JiraBoard.model_validate(doc) if doc else None
        res = await self.db.jiraboards.update_one({"_id": ObjectId(oid)}, {"$set": sets})
        if res.matched_count == 0:
            return None
        doc = await self.db.jiraboards.find_one({"_id": ObjectId(oid)})
        return JiraBoard.model_validate(doc) if doc else None

    async def delete_board(self, oid: str) -> int:
        res = await self.db.jiraboards.delete_one({"_id": ObjectId(oid)})
        return res.deleted_count
