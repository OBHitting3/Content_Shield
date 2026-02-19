"""Toxicity Detector — flags threatening, harassing, or harmful content."""

from __future__ import annotations

import logging
import re
from typing import Any

from joshua7.models import Severity, ValidationFinding, ValidationResult
from joshua7.validators.base import BaseValidator

logger = logging.getLogger(__name__)

_TOXICITY_CATEGORIES: dict[str, list[tuple[str, re.Pattern[str], Severity]]] = {
    "threat": [
        ("death_threat", re.compile(
            r"\b(?:i(?:'ll| will| am going to))\s+"
            r"(?:kill|murder|destroy|eliminate|end)\s+(?:you|them|him|her)",
            re.IGNORECASE,
        ), Severity.CRITICAL),
        ("violence_intent", re.compile(
            r"\b(?:gonna|going to|will)\s+(?:hurt|harm|attack|beat|shoot|stab)\b",
            re.IGNORECASE,
        ), Severity.CRITICAL),
        ("bomb_threat", re.compile(
            r"\b(?:bomb|explode|blow\s+up|detonate)\s+(?:the|this|that|your)\b",
            re.IGNORECASE,
        ), Severity.CRITICAL),
    ],
    "harassment": [
        ("targeted_insult", re.compile(
            r"\byou(?:'re| are)\s+(?:stupid|worthless|pathetic|disgusting|ugly|trash|garbage)\b",
            re.IGNORECASE,
        ), Severity.ERROR),
        ("harassment_directive", re.compile(
            r"\b(?:nobody|no one)\s+(?:likes|loves|cares about|wants)\s+you\b",
            re.IGNORECASE,
        ), Severity.ERROR),
        ("stalking_language", re.compile(
            r"\bi\s+(?:know|found)\s+where\s+you\s+(?:live|work|go)\b",
            re.IGNORECASE,
        ), Severity.CRITICAL),
    ],
    "profanity": [
        ("strong_profanity", re.compile(
            r"\b(?:fuck|shit|bitch|asshole|bastard|cunt|dick|piss)\b",
            re.IGNORECASE,
        ), Severity.WARNING),
        ("slur_adjacent", re.compile(
            r"\b(?:retard(?:ed)?|spaz|cripple)\b",
            re.IGNORECASE,
        ), Severity.ERROR),
    ],
    "discrimination": [
        ("hate_group_reference", re.compile(
            r"\b(?:white\s+(?:power|supremac\w*)|master\s+race|ethnic\s+cleansing"
            r"|racial\s+purity|heil\s+hitler)\b",
            re.IGNORECASE,
        ), Severity.CRITICAL),
        ("dehumanizing_language", re.compile(
            r"\b(?:subhuman|vermin|cockroach(?:es)?|parasite(?:s)?)\b"
            r"(?:\s+(?:people|race|group|community|immigrants?))?",
            re.IGNORECASE,
        ), Severity.CRITICAL),
    ],
    "self_harm": [
        ("self_harm_encouragement", re.compile(
            r"\b(?:kill\s+yourself|end\s+(?:it|your\s+life)|you\s+should\s+die)\b",
            re.IGNORECASE,
        ), Severity.CRITICAL),
        ("self_harm_instruction", re.compile(
            r"\bhow\s+to\s+(?:commit\s+suicide|cut\s+yourself|overdose)\b",
            re.IGNORECASE,
        ), Severity.CRITICAL),
    ],
}

_SEVERITY_WEIGHTS = {
    Severity.INFO: 0.0,
    Severity.WARNING: 0.15,
    Severity.ERROR: 0.30,
    Severity.CRITICAL: 0.60,
}


class ToxicityDetector(BaseValidator):
    """Detect toxic, threatening, or harmful content."""

    name = "toxicity"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._threshold = self.config.get("toxicity_threshold", 0.5)
        enabled = self.config.get(
            "toxicity_categories_enabled",
            list(_TOXICITY_CATEGORIES.keys()),
        )
        self._active_categories = {
            k: v for k, v in _TOXICITY_CATEGORIES.items() if k in enabled
        }

    def validate(self, text: str) -> ValidationResult:
        findings: list[ValidationFinding] = []
        weighted_hits = 0.0

        for category, patterns in self._active_categories.items():
            for pattern_name, pattern, severity in patterns:
                for match in pattern.finditer(text):
                    findings.append(
                        ValidationFinding(
                            validator_name=self.name,
                            severity=severity,
                            message=f"Toxicity [{category}]: {pattern_name}",
                            span=(match.start(), match.end()),
                            metadata={
                                "category": category,
                                "pattern": pattern_name,
                                "matched": match.group(),
                            },
                        )
                    )
                    weighted_hits += _SEVERITY_WEIGHTS.get(severity, 0.0)

        toxicity_score = min(weighted_hits, 1.0)
        passed = len(findings) == 0

        display_score = round((1.0 - toxicity_score) * 100, 1)

        return ValidationResult(
            validator_name=self.name,
            passed=passed,
            score=display_score,
            findings=findings,
        )
