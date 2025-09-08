import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings
from app.core.security import hash_password
from app.utils.time import utcnow


async def main():
    client = AsyncIOMotorClient(settings.MONGO_URI)
    db = client[settings.MONGO_DB_NAME]

    await db.roles.delete_many({})
    await db.users.delete_many({})
    await db.applications.delete_many({})
    await db.releases.delete_many({})

    role = {
        "role_name": "Release Manager",
        "description": "Can manage releases",
        "is_approval_manager": True,
        "can_create_release": True,
        "can_edit_release_description": True,
        "can_manage_quality_gates": True,
        "can_manage_runbooks": True,
        "can_upload_attachments": True,
        "can_manage_roles": True,
        "can_invite_users": True,
        "can_view_all": True,
        "created_at": utcnow(),
    }
    r = await db.roles.insert_one(role)

    user = {
        "username": "admin",
        "full_name": "Admin User",
        "email": "admin@example.com",
        "password_hash": hash_password("admin123"),
        "role_ids": [r.inserted_id],
        "assigned_squad_ids": [],
        "created_at": utcnow(),
    }
    await db.users.insert_one(user)

    app = {
        "application_id": "APP1",
        "application_name": "Demo App",
        "technologies": ["python"],
        "description": "",
        "products": [],
    }
    await db.applications.insert_one(app)

    release = {
        "release_id": "REL-0001",
        "release_name": "Initial",
        "release_date": utcnow(),
        "scope_application_ids": [],
        "squad_ids": [],
        "products": [],
        "runbooks": [],
        "attachment_refs": [],
        "created_at": utcnow(),
    }
    await db.releases.insert_one(release)

    print("Seeded minimal data.")


if __name__ == "__main__":
    asyncio.run(main())
