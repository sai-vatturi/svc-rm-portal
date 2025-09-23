from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from fastapi.openapi.utils import get_openapi

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


# Tag metadata for nicer grouped docs
TAGS_METADATA = [
    {"name": "Auth", "description": "Authentication & token lifecycle (login / refresh)."},
    {"name": "RBAC", "description": "Role-based access control: roles & users."},
    {"name": "Catalog", "description": "Applications, squads, JIRA boards registry."},
    {"name": "Releases", "description": "Release entities, quality gates, milestones, runbooks."},
    {"name": "Attachments", "description": "Attachment metadata & association to releases."},
    {"name": "Health", "description": "Service health & diagnostics."},
]

# Public (no auth) routes for which we will not inject security requirements
OPEN_ENDPOINTS = {"/health", "/auth/login", "/auth/refresh", "/auth/register", "/openapi.json"}


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        description=(
            "Release Management Portal API.\n\n"
            "Use the /auth/login endpoint to obtain a JWT access & refresh token pair. "
            "Click the green 'Authorize' button, paste the access token as: **Bearer <token>** (the prefix is added automatically if omitted).\n\n"
            "Access tokens expire quickly; use /auth/refresh with your refresh token to get a new pair."
        ),
        contact={
            "name": "RM API Team",
            "url": "https://example.com",
            "email": "devnull@example.com",
        },
        license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        openapi_tags=TAGS_METADATA,
        swagger_ui_parameters={
            # Keep entered bearer token so user does not re-enter for every refresh
            "persistAuthorization": True,
            "displayRequestDuration": True,
            "filter": True,  # client-side filter box
        },
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

    # Custom OpenAPI generation to inject security scheme & apply to secured endpoints
    def custom_openapi():  # type: ignore[no-untyped-def]
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,    
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        components = schema.setdefault("components", {})
        security_schemes = components.setdefault("securitySchemes", {})
        security_schemes["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Paste your access token. Obtain via /auth/login."
        }
        # Add servers section (helpful in exported clients)
        schema["servers"] = [
            {"url": "http://localhost:8000", "description": "Local development"},
        ]
        # Inject security requirement for every operation except open endpoints
        for path, methods in schema.get("paths", {}).items():
            if path in OPEN_ENDPOINTS:
                continue
            for method_name, operation in methods.items():
                if not isinstance(operation, dict):
                    continue
                # Only set if not already explicitly set
                operation.setdefault("security", [{"BearerAuth": []}])
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[assignment]

    return app


app = create_app()
