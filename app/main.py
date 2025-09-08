from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

from app.core.config import settings
from app.core.logging import configure_logging
from app.core.errors import error_handler, http_exception_handler, validation_exception_handler
from app.db.client import connect_to_mongo, close_mongo_connection
from app.db.indexes import create_indexes
from app.routers.health import router as health_router
from app.routers.auth import router as auth_router
from app.routers.catalog import router as catalog_router
from app.routers.release import router as release_router
from app.routers.attachments import router as attachments_router
from app.routers.rbac import router as rbac_router


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description="Release Management Portal API",
        contact={
            "name": "RM API Team",
            "url": "https://example.com",
            "email": "devnull@example.com",
        },
        license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Error handlers
    app.add_exception_handler(Exception, error_handler)
    app.add_exception_handler(ValueError, error_handler)
    from fastapi import HTTPException
    from fastapi.exceptions import RequestValidationError

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Routers
    app.include_router(health_router, prefix="", tags=["Health"])
    app.include_router(auth_router, prefix="/auth", tags=["Auth"])
    app.include_router(rbac_router, prefix="", tags=["RBAC"])  # /rbac
    app.include_router(catalog_router, prefix="/catalog", tags=["Catalog"])
    app.include_router(release_router, prefix="", tags=["Releases"])  # paths already include /releases
    app.include_router(attachments_router, prefix="", tags=["Attachments"])  # /attachments

    skip_db = os.getenv("SKIP_DB") == "1" or os.getenv("PYTEST_CURRENT_TEST") is not None

    @app.on_event("startup")
    async def on_startup() -> None:
        if not skip_db:
            await connect_to_mongo()
            await create_indexes()

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        if not skip_db:
            await close_mongo_connection()

    return app


app = create_app()
