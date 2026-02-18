"""Prompt Injection Detector — catches hidden prompt-injection attempts."""

from __future__ import annotations

import re
from typing import Any

from joshua7.models import Severity, ValidationFinding, ValidationResult
from joshua7.validators.base import BaseValidator

_INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("ignore_instructions", re.compile(
        r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)",
        re.IGNORECASE,
    )),
    ("system_prompt_leak", re.compile(
        r"(show|reveal|print|output|repeat)\s+(your\s+)?(system\s+prompt|instructions|rules)",
        re.IGNORECASE,
    )),
    ("role_override", re.compile(
        r"you\s+are\s+now\s+(?:a\s+)?(?:DAN|unrestricted|jailbroken|evil)",
        re.IGNORECASE,
    )),
    ("delimiter_injection", re.compile(
        r"```\s*(system|assistant|user)\s*\n",
        re.IGNORECASE,
    )),
    ("encoded_injection", re.compile(
        r"(?:base64|rot13|hex)\s*(?:decode|encode)\s*[:=]",
        re.IGNORECASE,
    )),
    ("do_anything_now", re.compile(
        r"(?:DAN|do\s+anything\s+now)\s+mode",
        re.IGNORECASE,
    )),
    ("instruction_override", re.compile(
        r"(?:new|updated?|override)\s+(?:system\s+)?(?:instructions?|prompt|rules?)\s*[:=]",
        re.IGNORECASE,
    )),
    ("hidden_text", re.compile(
        r"<\s*(?:hidden|invisible|secret)\s*>",
        re.IGNORECASE,
    )),
]


class PromptInjectionDetector(BaseValidator):
    """Detect prompt-injection attacks embedded in content."""

    name = "prompt_injection"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._threshold = self.config.get("prompt_injection_threshold", 0.6)

    def validate(self, text: str) -> ValidationResult:
        findings: list[ValidationFinding] = []
        triggered = 0

        for pattern_name, pattern in _INJECTION_PATTERNS:
            for match in pattern.finditer(text):
                triggered += 1
                findings.append(
                    ValidationFinding(
                        validator_name=self.name,
                        severity=Severity.CRITICAL,
                        message=f"Prompt injection pattern: {pattern_name}",
                        span=(match.start(), match.end()),
                        metadata={"pattern": pattern_name, "matched": match.group()},
                    )
                )

        risk_score = min(triggered / max(len(_INJECTION_PATTERNS), 1), 1.0)
        passed = triggered == 0

        return ValidationResult(
            validator_name=self.name,
            passed=passed,
            score=round((1.0 - risk_score) * 100, 1),
            findings=findings,
        )
