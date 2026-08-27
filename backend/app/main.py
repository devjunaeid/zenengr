from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.cache import init_cache
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.db.session import async_session_factory
from app.services.roles import sync_system_roles_and_permissions


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_cache()
    try:
        async with async_session_factory() as session:
            await sync_system_roles_and_permissions(session)
    except Exception:
        pass
    yield


def create_app() -> FastAPI:
    init_cache()
    settings = get_settings()
    app = FastAPI(title="ZenEngr API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_error_handlers(app)

    @app.get("/", tags=["Health"])
    @app.get("/healthz", tags=["Health"])
    async def health_check() -> dict[str, str]:
        return {
            "status": "healthy",
            "app": "ZenEngr API",
            "environment": settings.environment,
            "version": "0.1.0",
        }

    app.include_router(api_router)

    # Serve public files from the storage local backend namespace (legacy
    # static path; branding logos now use the /api/v1/public/... endpoint).
    # uploads_dir is kept as the backfill source for pre-storage logos.
    uploads_dir = Path(settings.uploads_dir)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    public_dir = Path(settings.storage_local_dir) / "public"
    public_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(public_dir)), name="uploads")

    return app


app = create_app()
