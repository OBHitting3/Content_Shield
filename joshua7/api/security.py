"""Security middleware and utilities for Joshua 7 API."""

from __future__ import annotations

import hashlib
import hmac
import logging
import re
import time
from collections import defaultdict
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

_REQUEST_ID_RE = re.compile(r"^[\w\-]{1,128}$")
_MAX_REQUEST_BODY_BYTES = 4 * 1024 * 1024  # 4 MB hard cap


def timing_safe_compare(a: str, b: str) -> bool:
    """Compare two strings in constant time to prevent timing attacks."""
    a_bytes = hashlib.sha256(a.encode("utf-8")).digest()
    b_bytes = hashlib.sha256(b.encode("utf-8")).digest()
    return hmac.compare_digest(a_bytes, b_bytes)


def sanitize_request_id(raw: str) -> str:
    """Sanitize X-Request-ID to prevent log/header injection.

    Allows only alphanumeric, hyphen, and underscore; max 128 chars.
    Falls back to empty string if invalid (caller generates a new one).
    """
    if _REQUEST_ID_RE.match(raw):
        return raw
    cleaned = re.sub(r"[^\w\-]", "", raw)[:128]
    if cleaned:
        logger.warning("Sanitized X-Request-ID header (contained invalid characters)")
        return cleaned
    return ""


_ALLOWED_OVERRIDE_KEYS: frozenset[str] = frozenset({
    "forbidden_phrases",
    "pii_patterns_enabled",
    "brand_voice_target_score",
    "brand_voice_keywords",
    "brand_voice_tone",
    "readability_min_score",
    "readability_max_score",
})

_BLOCKED_OVERRIDE_KEYS: frozenset[str] = frozenset({
    "api_key",
    "debug",
    "host",
    "port",
    "log_level",
    "max_text_length",
    "app_name",
})


def sanitize_config_overrides(
    overrides: dict[str, Any],
) -> dict[str, Any]:
    """Strip dangerous keys from per-request config overrides.

    Only validator-specific tuning keys are allowed through.
    Infrastructure keys (api_key, debug, host, port, etc.) are silently dropped.
    """
    sanitized: dict[str, Any] = {}
    for validator_name, validator_config in overrides.items():
        if not isinstance(validator_config, dict):
            continue
        clean: dict[str, Any] = {}
        for k, v in validator_config.items():
            if k in _BLOCKED_OVERRIDE_KEYS:
                logger.warning(
                    "Blocked config override key '%s' in validator '%s'",
                    k, validator_name,
                )
                continue
            if k in _ALLOWED_OVERRIDE_KEYS:
                clean[k] = v
            else:
                logger.debug(
                    "Ignoring unknown config override key '%s' in validator '%s'",
                    k, validator_name,
                )
        if clean:
            sanitized[validator_name] = clean
    return sanitized


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject standard security headers into every response."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )
        csp = (
            "default-src 'none'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "frame-ancestors 'none'"
        )
        response.headers["Content-Security-Policy"] = csp
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )
        return response


class RequestBodyLimitMiddleware(BaseHTTPMiddleware):
    """Reject request bodies exceeding a hard byte limit before full read."""

    def __init__(self, app: Any, max_bytes: int = _MAX_REQUEST_BODY_BYTES) -> None:
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint,
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_bytes:
                    logger.warning(
                        "Rejected request: Content-Length %s exceeds limit %s",
                        content_length, self.max_bytes,
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"Request body too large. Maximum: {self.max_bytes} bytes."
                        },
                    )
            except ValueError:
                pass
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory sliding-window rate limiter per client IP.

    Not suitable for distributed deployments; use an external rate limiter
    (API Gateway, Redis-backed) in production multi-instance setups.
    """

    def __init__(
        self,
        app: Any,
        requests_per_minute: int = 60,
        burst: int = 10,
    ) -> None:
        super().__init__(app)
        self.rpm = requests_per_minute
        self.burst = burst
        self._window: dict[str, list[float]] = defaultdict(list)

    def _client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _cleanup(self, timestamps: list[float], now: float) -> list[float]:
        cutoff = now - 60.0
        return [t for t in timestamps if t > cutoff]

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint,
    ) -> Response:
        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        client = self._client_ip(request)
        now = time.monotonic()
        self._window[client] = self._cleanup(self._window[client], now)

        if len(self._window[client]) >= self.rpm:
            logger.warning("Rate limit exceeded for client %s", client)
            retry_after = 60 - (now - self._window[client][0]) if self._window[client] else 60
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": str(int(max(retry_after, 1)))},
            )

        self._window[client].append(now)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.rpm)
        response.headers["X-RateLimit-Remaining"] = str(
            max(self.rpm - len(self._window[client]), 0)
        )
        return response
