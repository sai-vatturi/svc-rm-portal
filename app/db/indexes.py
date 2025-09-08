from __future__ import annotations

from typing import Any

from app.db.client import get_db


async def create_indexes() -> None:
    db = get_db()

    await db.roles.create_index("role_name", unique=True)

    await db.users.create_index("username", unique=True)
    await db.users.create_index("email", unique=True)

    await db.applications.create_index("application_id", unique=True)

    await db.squads.create_index("squad_id", unique=True)

    await db.jiraboards.create_index("board_id", unique=True)

    await db.releases.create_index("release_id", unique=True)

    await db.attachments.create_index("sha256", unique=True)
