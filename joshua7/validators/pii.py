"""PII Validator — detects emails, phone numbers, and SSNs.

SECURITY: Raw PII values are NEVER returned in findings. All matches are
replaced with fixed redaction placeholders before being surfaced.
"""

from __future__ import annotations

import re
from typing import Any

from joshua7.models import Severity, ValidationFinding, ValidationResult
from joshua7.validators.base import BaseValidator

_PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": re.compile(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    ),
    "phone": re.compile(
        r"(?<!\d)"
        r"(?:\+?1[\s\-.]?)?"
        r"\(?\d{3}\)?[\s\-.]?"
        r"\d{3}[\s\-.]?\d{4}"
        r"(?!\d)",
    ),
    "ssn": re.compile(
        r"(?<!\d)\d{3}[\s\-]\d{2}[\s\-]\d{4}(?!\d)",
    ),
}

_REDACT_PLACEHOLDERS: dict[str, str] = {
    "email": "***@***.***",
    "phone": "***-***-****",
    "ssn": "***-**-****",
}


def _redacted(pii_type: str) -> str:
    """Return a fixed placeholder — never echo real PII values."""
    return _REDACT_PLACEHOLDERS.get(pii_type, "***REDACTED***")


class PIIValidator(BaseValidator):
    """Detect personally identifiable information in content."""

    name = "pii"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        enabled = self.config.get("pii_patterns_enabled", list(_PII_PATTERNS.keys()))
        self._active: dict[str, re.Pattern[str]] = {
            k: v for k, v in _PII_PATTERNS.items() if k in enabled
        }

    def validate(self, text: str) -> ValidationResult:
        findings: list[ValidationFinding] = []
        for pii_type, pattern in self._active.items():
            for match in pattern.finditer(text):
                placeholder = _redacted(pii_type)
                findings.append(
                    ValidationFinding(
                        validator_name=self.name,
                        severity=Severity.CRITICAL,
                        message=f"Potential {pii_type.upper()} detected (redacted: {placeholder})",
                        span=(match.start(), match.end()),
                        metadata={"pii_type": pii_type, "redacted": placeholder},
                    )
                )
        return ValidationResult(
            validator_name=self.name,
            passed=len(findings) == 0,
            findings=findings,
        )
