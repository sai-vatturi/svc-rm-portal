from __future__ import annotations

from typing import Any, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase


class ReleaseRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db

    async def get_by_id(self, id: str) -> Optional[dict]:
        return await self.db.releases.find_one({"_id": ObjectId(id)})

    async def update(self, id: str, update: dict[str, Any]) -> int:
        res = await self.db.releases.update_one({"_id": ObjectId(id)}, update)
        return res.modified_count
