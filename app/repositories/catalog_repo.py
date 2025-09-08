from __future__ import annotations

from typing import List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.catalog import Application, JiraBoard, Squad


class CatalogRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db

    async def create_application(self, app: Application) -> Application:
        payload = app.model_dump(by_alias=True)
        res = await self.db.applications.insert_one(payload)
        payload["_id"] = res.inserted_id
        return Application.model_validate(payload)

    async def list_applications(self) -> List[Application]:
        items: List[Application] = []
        async for doc in self.db.applications.find().sort("application_id"):
            items.append(Application.model_validate(doc))
        return items

    async def create_squad(self, squad: Squad) -> Squad:
        payload = squad.model_dump(by_alias=True)
        res = await self.db.squads.insert_one(payload)
        payload["_id"] = res.inserted_id
        return Squad.model_validate(payload)

    async def list_squads(self) -> List[Squad]:
        items: List[Squad] = []
        async for doc in self.db.squads.find().sort("squad_id"):
            items.append(Squad.model_validate(doc))
        return items

    async def create_board(self, board: JiraBoard) -> JiraBoard:
        payload = board.model_dump(by_alias=True)
        res = await self.db.jiraboards.insert_one(payload)
        payload["_id"] = res.inserted_id
        return JiraBoard.model_validate(payload)

    async def list_boards(self) -> List[JiraBoard]:
        items: List[JiraBoard] = []
        async for doc in self.db.jiraboards.find().sort("board_id"):
            items.append(JiraBoard.model_validate(doc))
        return items
