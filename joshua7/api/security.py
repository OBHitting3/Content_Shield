"""Security middleware and utilities for Joshua 7 API."""

from __future__ import annotations

import logging
import re
import time
from collections import defaultdict
from threading import Lock

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("joshua7.audit")

_REQUEST_ID_RE = re.compile(r"^[a-zA-Z0-9\-_.:]{1,128}$")

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "0",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
}


def sanitize_request_id(raw: str) -> str | None:
    """Return the request ID if it matches the safe pattern, else ``None``."""
    if _REQUEST_ID_RE.match(raw):
        return raw
    return None


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject hardened security headers into every response."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        for header, value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header, value)
        return response


class RequestBodyLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests whose Content-Length exceeds the configured limit."""

    def __init__(self, app, max_bytes: int = 2_097_152) -> None:  # noqa: ANN001
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_bytes:
                    audit_logger.warning(
                        "BODY_TOO_LARGE ip=%s content_length=%s limit=%s",
                        request.client.host if request.client else "unknown",
                        content_length,
                        self.max_bytes,
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"Request body too large (limit {self.max_bytes:,} bytes)"
                        },
                    )
            except ValueError:
                pass
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple sliding-window rate limiter keyed by client IP.

    Uses an in-memory store — suitable for single-process deployments.
    For multi-process/multi-node setups, swap in Redis.
    """

    def __init__(
        self,
        app,  # noqa: ANN001
        max_requests: int = 60,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)
        self._lock = Lock()

    def _prune_and_count(self, key: str, now: float) -> int:
        cutoff = now - self.window_seconds
        timestamps = self._hits[key]
        pruned = [t for t in timestamps if t > cutoff]
        self._hits[key] = pruned
        return len(pruned)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if self.max_requests <= 0:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()

        with self._lock:
            count = self._prune_and_count(client_ip, now)
            if count >= self.max_requests:
                audit_logger.warning(
                    "RATE_LIMITED ip=%s count=%d window=%ds",
                    client_ip,
                    count,
                    self.window_seconds,
                )
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Try again later."},
                    headers={"Retry-After": str(self.window_seconds)},
                )
            self._hits[client_ip].append(now)

        response = await call_next(request)
        remaining = max(0, self.max_requests - count - 1)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
