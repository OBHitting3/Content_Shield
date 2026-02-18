"""Validation engine — orchestrates all validators against incoming content."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError

from joshua7.config import Settings, get_settings
from joshua7.models import (
    Severity,
    ValidationFinding,
    ValidationRequest,
    ValidationResponse,
    ValidationResult,
)
from joshua7.validators.base import BaseValidator
from joshua7.validators.brand_voice import BrandVoiceScorer
from joshua7.validators.forbidden_phrases import ForbiddenPhraseDetector
from joshua7.validators.pii import PIIValidator
from joshua7.validators.prompt_injection import PromptInjectionDetector
from joshua7.validators.readability import ReadabilityScorer

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, type[BaseValidator]] = {
    "forbidden_phrases": ForbiddenPhraseDetector,
    "pii": PIIValidator,
    "brand_voice": BrandVoiceScorer,
    "prompt_injection": PromptInjectionDetector,
    "readability": ReadabilityScorer,
}


class ValidationEngine:
    """Runs a configurable set of validators against content."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._validators: dict[str, BaseValidator] = {}
        self._build_validators()

    def _build_validators(self) -> None:
        config = self._settings_to_config()
        for name, cls in _REGISTRY.items():
            self._validators[name] = cls(config=config)

    def _settings_to_config(self) -> dict[str, Any]:
        return self._settings.model_dump()

    @property
    def available_validators(self) -> list[str]:
        return list(self._validators.keys())

    def run(self, request: ValidationRequest) -> ValidationResponse:
        """Execute requested validators and return aggregated response."""
        selected = self._resolve_validators(request.validators)
        results: list[ValidationResult] = []

        for name in selected:
            validator = self._validators[name]
            if name in request.config_overrides:
                merged = {**self._settings_to_config(), **request.config_overrides[name]}
                validator = _REGISTRY[name](config=merged)
            try:
                result = validator.validate(request.text)
                results.append(result)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Validator '%s' crashed during validation", name, exc_info=exc)
                results.append(
                    ValidationResult(
                        validator_name=name,
                        passed=False,
                        findings=[
                            ValidationFinding(
                                validator_name=name,
                                severity=Severity.ERROR,
                                message=(
                                    f"Validator '{name}' encountered an internal error — "
                                    "content blocked as a precaution"
                                ),
                                metadata={"error_type": type(exc).__name__},
                            )
                        ],
                    )
                )

        all_passed = all(r.passed for r in results)
        return ValidationResponse(
            passed=all_passed,
            results=results,
            text_length=len(request.text),
            validators_run=len(results),
        )

    def validate_text(self, text: str, validators: list[str] | None = None) -> ValidationResponse:
        """Convenience wrapper that builds a request from plain text."""
        try:
            request = ValidationRequest(
                text=text,
                validators=validators or ["all"],
            )
        except ValidationError as exc:
            logger.info("Invalid validate_text input rejected", exc_info=exc)
            raise HTTPException(
                status_code=422,
                detail="Invalid request: text must be a non-empty string.",
            ) from None
        return self.run(request)

    def _resolve_validators(self, names: list[str]) -> list[str]:
        if "all" in names:
            return list(self._validators.keys())
        resolved = []
        for n in names:
            if n in self._validators:
                resolved.append(n)
        return resolved
