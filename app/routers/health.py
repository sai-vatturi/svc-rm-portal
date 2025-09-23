from fastapi import APIRouter

from app.core.config import settings
from app.utils.time import utcnow
from app.db.client import get_db

router = APIRouter()


@router.get("/health", summary="Health check")
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "time": utcnow().isoformat().replace("+00:00", "Z"),
    }


@router.get("/health/details", summary="Extended health details")
async def health_details():
    db_status = "unknown"
    index_status = {}
    try:
        db = get_db()
        # simple ping
        await db.command("ping")
        db_status = "up"
        # sample index info for core collections
        for coll in [
            "users",
            "roles",
            "applications",
            "squads",
            "jiraboards",
            "releases",
            "attachments",
        ]:
            try:
                info = await db[coll].index_information()
                index_status[coll] = list(info.keys())
            except Exception:  # pragma: no cover
                index_status[coll] = []
    except Exception:  # pragma: no cover
        db_status = "down"
    return {
        "status": "ok" if db_status == "up" else "degraded",
        "db": db_status,
        "indexes": index_status,
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "time": utcnow().isoformat().replace("+00:00", "Z"),
    }
