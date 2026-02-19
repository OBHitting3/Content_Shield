"""API route definitions for Joshua 7."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from joshua7.api.security import sanitize_config_overrides, timing_safe_compare
from joshua7.config import Settings, get_settings
from joshua7.engine import ValidationEngine
from joshua7.models import ValidationRequest, ValidationResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["validation"])


def verify_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> None:
    """API key auth for /api/v1 endpoints.

    If ``J7_API_KEY`` is set, requests must include a matching ``X-API-Key``
    header.  Comparison uses constant-time HMAC to prevent timing attacks.
    """
    if not settings.api_key:
        return
    if x_api_key is None or not timing_safe_compare(x_api_key, settings.api_key):
        logger.warning("Authentication failure: invalid or missing API key")
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def _get_engine(request: Request) -> ValidationEngine:
    return request.app.state.engine


@router.post("/validate", response_model=ValidationResponse, dependencies=[Depends(verify_api_key)])
async def validate_content(
    body: ValidationRequest,
    request: Request,
) -> ValidationResponse:
    if body.config_overrides:
        body.config_overrides = sanitize_config_overrides(body.config_overrides)

    engine = _get_engine(request)
    request_id = getattr(request.state, "request_id", None)
    return engine.run(body, request_id=request_id)


@router.get("/validators", dependencies=[Depends(verify_api_key)])
async def list_validators(request: Request) -> dict[str, list[str]]:
    engine = _get_engine(request)
    return {"validators": engine.available_validators}
