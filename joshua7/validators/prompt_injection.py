"""Prompt Injection Detector — catches hidden prompt-injection attempts (15 pattern families)."""

from __future__ import annotations

import logging
import re

from joshua7.models import Severity, ValidationFinding, ValidationResult
from joshua7.validators.base import BaseValidator

logger = logging.getLogger(__name__)

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
    ("forget_everything", re.compile(
        r"forget\s+(everything|all|what)\s+(you|I)\s+(know|said|told)",
        re.IGNORECASE,
    )),
    ("act_as", re.compile(
        r"(?:act|behave|respond)\s+as\s+(?:if\s+)?(?:you\s+(?:are|were)\s+)?(?:a\s+)?(?:different|new|another)",
        re.IGNORECASE,
    )),
    ("token_manipulation", re.compile(
        r"(?:set|change|modify)\s+(?:your\s+)?(?:max_tokens|temperature|top_p|system)\s*(?:to|=)",
        re.IGNORECASE,
    )),
    ("context_boundary", re.compile(
        r"(?:</s>|\[/?INST\]|\[/?SYS\]|<\|(?:im_(?:start|end)|system|endoftext)\|>)",
        re.IGNORECASE,
    )),
    ("markdown_exfil", re.compile(
        r"!\[[^\]]*\]\(https?://[^\s)]+\?[^\s)]*(?:text|data|q|input)=",
        re.IGNORECASE,
    )),
    ("developer_mode", re.compile(
        r"(?:enable|activate|enter)\s+(?:developer|dev|debug|god)\s+mode",
        re.IGNORECASE,
    )),
    ("privilege_escalation", re.compile(
        r"(?:grant|give)\s+(?:me\s+)?(?:admin|root|sudo|superuser)\s+(?:access|privileges?|rights?|mode)",
        re.IGNORECASE,
    )),
]


class PromptInjectionDetector(BaseValidator):
    """Detect prompt-injection attacks embedded in content."""

    name = "prompt_injection"

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
