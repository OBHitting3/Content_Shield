"""Forbidden Phrase Detector — flags banned words and phrases in content."""

from __future__ import annotations

import re
from typing import Any

from joshua7.config import DEFAULT_FORBIDDEN_PHRASES
from joshua7.models import Severity, ValidationFinding, ValidationResult
from joshua7.validators.base import BaseValidator


class ForbiddenPhraseDetector(BaseValidator):
    """Scan content for configurable forbidden/banned phrases."""

    name = "forbidden_phrases"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        raw = self.config.get("forbidden_phrases", list(DEFAULT_FORBIDDEN_PHRASES))
        self._phrases: list[str] = [p.lower() for p in raw]
        self._patterns: list[tuple[str, re.Pattern[str]]] = [
            (phrase, re.compile(re.escape(phrase), re.IGNORECASE))
            for phrase in self._phrases
        ]

    def validate(self, text: str) -> ValidationResult:
        findings: list[ValidationFinding] = []
        for phrase, pattern in self._patterns:
            for match in pattern.finditer(text):
                findings.append(
                    ValidationFinding(
                        validator_name=self.name,
                        severity=Severity.ERROR,
                        message=f"Forbidden phrase detected: '{phrase}'",
                        span=(match.start(), match.end()),
                        metadata={"phrase": phrase},
                    )
                )
        return ValidationResult(
            validator_name=self.name,
            passed=len(findings) == 0,
            findings=findings,
        )
