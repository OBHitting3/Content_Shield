"""FastAPI application factory for Joshua 7."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse

from joshua7 import __version__
from joshua7.api.routes import router
from joshua7.api.security import (
    RateLimitMiddleware,
    RequestBodyLimitMiddleware,
    SecurityHeadersMiddleware,
    sanitize_request_id,
)
from joshua7.config import get_settings
from joshua7.engine import ValidationEngine

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Pre-publication AI content validation engine",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
    )

    if settings.trusted_hosts != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
        expose_headers=[
            "X-Request-ID",
            "X-Response-Time-Ms",
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
        ],
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        RequestBodyLimitMiddleware,
        max_bytes=settings.max_request_body_bytes,
    )

    if settings.rate_limit_rpm > 0:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=settings.rate_limit_rpm,
            burst=settings.rate_limit_burst,
        )

    app.state.settings = settings
    app.state.engine = ValidationEngine(settings=settings)

    app.include_router(router, prefix="/api/v1")

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError,
    ) -> JSONResponse:
        safe_errors = []
        for err in exc.errors():
            safe_errors.append({
                "loc": err.get("loc", []),
                "msg": err.get("msg", "Validation error"),
                "type": err.get("type", "value_error"),
            })
        return JSONResponse(
            status_code=422,
            content={"detail": safe_errors},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    @app.middleware("http")
    async def add_request_context(request: Request, call_next) -> Response:  # noqa: ANN001
        raw_id = request.headers.get("X-Request-ID", "")
        if raw_id:
            request_id = sanitize_request_id(raw_id) or uuid.uuid4().hex
        else:
            request_id = uuid.uuid4().hex
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

    return app


app = create_app()
