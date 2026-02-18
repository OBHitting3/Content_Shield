"""Brand Voice Scorer — scores content against a target brand-voice profile."""

from __future__ import annotations

import re
from typing import Any

from joshua7.models import Severity, ValidationFinding, ValidationResult
from joshua7.validators.base import BaseValidator

_TONE_PENALTY_WORDS: dict[str, list[str]] = {
    "professional": [
        "lol", "omg", "bruh", "gonna", "wanna", "kinda", "sorta",
        "tbh", "ngl", "fr fr", "yo ", "dude", "bro",
    ],
    "casual": [
        "hereby", "aforementioned", "pursuant", "notwithstanding",
        "heretofore", "therein", "whereas",
    ],
}

_POSITIVE_SIGNALS = [
    r"\b(we|our|us)\b",
    r"\b(you|your)\b",
]


class BrandVoiceScorer(BaseValidator):
    """Score content against a target tone and keyword list."""

    name = "brand_voice"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._target_score = self.config.get("brand_voice_target_score", 60.0)
        self._keywords = [k.lower() for k in self.config.get("brand_voice_keywords", [])]
        self._tone = self.config.get("brand_voice_tone", "professional")

    def validate(self, text: str) -> ValidationResult:
        findings: list[ValidationFinding] = []
        score = 70.0  # baseline

        lower = text.lower()
        words = lower.split()
        word_count = max(len(words), 1)

        penalty_words = _TONE_PENALTY_WORDS.get(self._tone, [])
        penalty_count = 0
        for pw in penalty_words:
            occurrences = lower.count(pw)
            if occurrences > 0:
                penalty_count += occurrences
                findings.append(
                    ValidationFinding(
                        validator_name=self.name,
                        severity=Severity.WARNING,
                        message=f"Off-tone word detected: '{pw}' ({occurrences}x)",
                        metadata={"word": pw, "count": occurrences},
                    )
                )

        score -= min(penalty_count * 5.0, 40.0)

        if self._keywords:
            keyword_hits = sum(1 for kw in self._keywords if kw in lower)
            keyword_ratio = keyword_hits / len(self._keywords)
            score += keyword_ratio * 15.0

        signal_hits = 0
        for pattern in _POSITIVE_SIGNALS:
            signal_hits += len(re.findall(pattern, lower))
        engagement_ratio = min(signal_hits / word_count, 0.15)
        score += engagement_ratio * 100.0

        score = max(0.0, min(100.0, score))
        passed = score >= self._target_score

        if not passed:
            findings.append(
                ValidationFinding(
                    validator_name=self.name,
                    severity=Severity.ERROR,
                    message=f"Brand voice score {score:.1f} below target {self._target_score}",
                    metadata={"score": score, "target": self._target_score},
                )
            )

        return ValidationResult(
            validator_name=self.name,
            passed=passed,
            score=round(score, 1),
            findings=findings,
        )
