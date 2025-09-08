import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.utils.time import utcnow


async def main():
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    # Add some demo squads and boards
    squad_id = (await db.squads.insert_one({
        "squad_id": "SQ-PLATFORM",
        "squad_name": "Platform Squad",
        "squad_jira_board_ids": [],
        "member_ids": [],
    })).inserted_id

    board_id = (await db.jiraboards.insert_one({
        "board_id": "JIRA-PLAT",
        "board_name": "Platform Board",
        "board_link": None,
        "board_type": "scrum",
    })).inserted_id

    print("Seeded demo squads and boards.")


if __name__ == "__main__":
    asyncio.run(main())
