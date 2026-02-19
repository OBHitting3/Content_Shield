"""FastAPI application factory for Joshua 7."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from joshua7 import __version__
from joshua7.api.routes import router
from joshua7.config import get_settings
from joshua7.engine import ValidationEngine

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Pre-publication AI content validation engine"
            " — Content Shield by Iron Forge Studios"
        ),
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    app.state.settings = settings
    app.state.engine = ValidationEngine(settings=settings)

    app.include_router(router, prefix="/api/v1")

    @app.middleware("http")
    async def add_request_context(request: Request, call_next) -> Response:  # noqa: ANN001
        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
        request.state.request_id = request_id
        start = time.monotonic()
        response: Response = await call_next(request)
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
        return response

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    return app


app = create_app()
