from __future__ import annotations

from typing import List, Optional, Tuple

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.attachment import Attachment


class AttachmentRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db

    def _normalize(self, doc: dict | None) -> dict | None:
        if not doc:
            return doc
        if "_id" in doc and isinstance(doc["_id"], ObjectId):
            doc["_id"] = str(doc["_id"])
        return doc

    async def upsert_by_sha(self, att: Attachment) -> Attachment:
        payload = att.model_dump(by_alias=True)
        existing = await self.db.attachments.find_one({"sha256": payload["sha256"]})
        if existing:
            existing = self._normalize(existing)  # type: ignore[assignment]
            return Attachment.model_validate(existing)
        res = await self.db.attachments.insert_one(payload)
        payload["_id"] = str(res.inserted_id)
        return Attachment.model_validate(payload)

    async def list_paginated(self, limit: int, last_id: ObjectId | None = None, q: str | None = None) -> Tuple[List[Attachment], ObjectId | None]:
        filters: dict = {}
        if q:
            filters = {"$or": [{"file_name": {"$regex": q, "$options": "i"}}, {"sha256": {"$regex": q, "$options": "i"}}]}
        if last_id:
            filters.update({"_id": {"$lt": last_id}})
        cursor = self.db.attachments.find(filters).sort("_id", -1).limit(limit)
        items: List[Attachment] = []
        last: ObjectId | None | str = None
        async for doc in cursor:
            oid_val = doc["_id"]
            items.append(Attachment.model_validate(self._normalize(doc)))
            last = oid_val
        if isinstance(last, str):
            try:
                last = ObjectId(last)
            except Exception:
                last = None
        return items, last
