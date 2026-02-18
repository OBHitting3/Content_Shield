"""FastAPI application factory for Joshua 7."""

from __future__ import annotations

from fastapi import FastAPI

from joshua7 import __version__
from joshua7.api.routes import router
from joshua7.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Pre-publication AI content validation engine",
    )
    app.state.settings = settings
    app.include_router(router, prefix="/api/v1")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
