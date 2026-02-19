"""FastAPI application factory for Joshua 7."""

from __future__ import annotations

import logging
import re
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

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,128}$")

_MAX_BODY_BYTES = 4 * 1024 * 1024  # 4 MiB hard cap


def create_app() -> FastAPI:
    settings = get_settings()

    docs_url = "/docs" if settings.debug else None
    redoc_url = "/redoc" if settings.debug else None

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Pre-publication AI content validation engine",
        docs_url=docs_url,
        redoc_url=redoc_url,
    )

    allowed_origins = settings.cors_allowed_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["X-API-Key", "X-Request-ID", "Content-Type"],
    )

    app.state.settings = settings
    app.state.engine = ValidationEngine(settings=settings)

    app.include_router(router, prefix="/api/v1")

    @app.middleware("http")
    async def request_pipeline(request: Request, call_next) -> Response:  # noqa: ANN001
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _MAX_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large"},
            )

        raw_id = request.headers.get("X-Request-ID", "")
        if raw_id and _REQUEST_ID_RE.match(raw_id):
            request_id = raw_id
        else:
            request_id = uuid.uuid4().hex
        request.state.request_id = request_id

        start = time.monotonic()
        response: Response = await call_next(request)
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
