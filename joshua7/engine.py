"""Validation engine — orchestrates all validators against incoming content."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from joshua7 import __version__
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

    def run(
        self,
        request: ValidationRequest,
        request_id: str | None = None,
    ) -> ValidationResponse:
        """Execute requested validators and return aggregated response."""
        rid = request_id or uuid.uuid4().hex
        max_len = self._settings.max_text_length
        if len(request.text) > max_len:
            return ValidationResponse(
                request_id=rid,
                version=__version__,
                passed=False,
                results=[
                    ValidationResult(
                        validator_name="_engine",
                        passed=False,
                        findings=[
                            ValidationFinding(
                                validator_name="_engine",
                                severity=Severity.ERROR,
                                message=(
                                    f"Text length {len(request.text):,} exceeds "
                                    f"configured maximum of {max_len:,} characters."
                                ),
                            ),
                        ],
                    ),
                ],
                text_length=len(request.text),
                validators_run=0,
            )

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

        all_passed = bool(results) and all(r.passed for r in results)
        return ValidationResponse(
            request_id=rid,
            version=__version__,
            passed=all_passed,
            results=results,
            text_length=len(request.text),
            validators_run=len(results),
        )

    def validate_text(
        self,
        text: str,
        validators: list[str] | None = None,
        request_id: str | None = None,
    ) -> ValidationResponse:
        """Convenience wrapper that builds a request from plain text."""
        request = ValidationRequest(
            text=text,
            validators=validators or ["all"],
        )
        return self.run(request, request_id=request_id)

    def _resolve_validators(self, names: list[str]) -> list[str]:
        if "all" in names:
            return list(self._validators.keys())
        resolved = []
        for n in names:
            if n in self._validators:
                resolved.append(n)
            else:
                logger.warning("Unknown validator requested: '%s' — skipping", n)
        return resolved
