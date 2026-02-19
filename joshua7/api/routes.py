"""API route definitions for Joshua 7."""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from joshua7.engine import ValidationEngine
from joshua7.models import ValidationRequest, ValidationResponse

router = APIRouter(tags=["validation"])


def _get_engine(request: Request) -> ValidationEngine:
    return request.app.state.engine


def verify_api_key(
    request: Request,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """Optional API key auth for /api/v1 endpoints.

    Uses the Settings stored on app.state (same instance the engine uses)
    and timing-safe comparison to prevent side-channel leaks.
    """
    expected = request.app.state.settings.api_key
    if not expected:
        return
    if x_api_key is None or not secrets.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@router.post("/validate", response_model=ValidationResponse, dependencies=[Depends(verify_api_key)])
async def validate_content(
    body: ValidationRequest,
    request: Request,
) -> ValidationResponse:
    engine = _get_engine(request)
    request_id = getattr(request.state, "request_id", None)
    return engine.run(body, request_id=request_id)


@router.get("/validators", dependencies=[Depends(verify_api_key)])
async def list_validators(request: Request) -> dict[str, list[str]]:
    engine = _get_engine(request)
    return {"validators": engine.available_validators}
