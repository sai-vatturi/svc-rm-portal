from __future__ import annotations

from typing import Any

from bson import ObjectId

from app.db.client import get_db
from app.models.release import (
    Release,
    ReleaseChange,
    ReleaseMilestone,
    ReleaseProduct,
    ReleaseProductQualityGate,
)


class ReleaseService:
    """Business logic for Releases.

    Note: Routers currently perform most operations directly for MVP.
    This service provides a seam for future refactoring and complex workflows.
    """

    def __init__(self) -> None:
        self.db = get_db()

    async def get(self, id: str) -> Release | None:
        doc = await self.db.releases.find_one({"_id": ObjectId(id)})
        return Release.model_validate({**doc, "_id": str(doc["_id"])}) if doc else None

    async def add_product(self, id: str, product: ReleaseProduct) -> int:
        res = await self.db.releases.update_one({"_id": ObjectId(id)}, {"$push": {"products": product.model_dump(by_alias=True)}})
        return res.modified_count

    async def add_gate(self, id: str, product_id: str, gate: ReleaseProductQualityGate) -> int:
        res = await self.db.releases.update_one(
            {"_id": ObjectId(id)},
            {"$push": {"products.$[p].quality_gates": gate.model_dump(by_alias=True)}},
            array_filters=[{"p.product_id": product_id}],
        )
        return res.modified_count

    async def add_milestone(self, id: str, product_id: str, gate_name: str, milestone: ReleaseMilestone) -> int:
        res = await self.db.releases.update_one(
            {"_id": ObjectId(id)},
            {"$push": {"products.$[p].quality_gates.$[g].milestones": milestone.model_dump(by_alias=True)}},
            array_filters=[{"p.product_id": product_id}, {"g.gate_name": gate_name}],
        )
        return res.modified_count

    async def upsert_change(self, id: str, change: ReleaseChange) -> int:
        res = await self.db.releases.update_one({"_id": ObjectId(id)}, {"$set": {"chg": change.model_dump(by_alias=True)}})
        return res.modified_count
