from fastapi import APIRouter

from app.core.config import settings
from app.utils.time import utcnow

router = APIRouter()


@router.get("/health", summary="Health check")
async def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "env": settings.APP_ENV,
        "time": utcnow().isoformat().replace("+00:00", "Z"),
    }
