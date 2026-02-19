"""FastAPI application factory for Joshua 7."""

from __future__ import annotations

import logging
import re
import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from joshua7 import __version__
from joshua7.api.routes import router
from joshua7.config import get_settings
from joshua7.engine import ValidationEngine

logger = logging.getLogger(__name__)

_REQUEST_ID_RE = re.compile(r"^[\w\-]{1,128}$")

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Cache-Control": "no-store",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
}


def _sanitize_request_id(raw: str | None) -> str:
    """Validate and sanitize the incoming X-Request-ID header.

    Rejects values containing newlines, non-printable characters, or
    exceeding 128 chars to prevent header injection and log forging.
    """
    if raw and _REQUEST_ID_RE.match(raw):
        return raw
    return uuid.uuid4().hex


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
        request_id = _sanitize_request_id(
            request.headers.get("X-Request-ID"),
        )
        request.state.request_id = request_id
        start = time.monotonic()
        response: Response = await call_next(request)
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
        for header, value in _SECURITY_HEADERS.items():
            response.headers[header] = value
        return response

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": __version__}

    return app


app = create_app()
