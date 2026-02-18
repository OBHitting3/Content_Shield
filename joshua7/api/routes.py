"""API route definitions for Joshua 7."""

from __future__ import annotations

from fastapi import APIRouter, Request

from joshua7.engine import ValidationEngine
from joshua7.models import ValidationRequest, ValidationResponse

router = APIRouter(tags=["validation"])


def _get_engine(request: Request) -> ValidationEngine:
    return request.app.state.engine


@router.post("/validate", response_model=ValidationResponse)
async def validate_content(
    body: ValidationRequest,
    request: Request,
) -> ValidationResponse:
    engine = _get_engine(request)
    request_id = getattr(request.state, "request_id", None)
    return engine.run(body, request_id=request_id)


@router.get("/validators")
async def list_validators(request: Request) -> dict[str, list[str]]:
    engine = _get_engine(request)
    return {"validators": engine.available_validators}
