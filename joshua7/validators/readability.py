"""Readability Scorer — Flesch-Kincaid readability gate with grade-level reporting."""

from __future__ import annotations

from typing import Any

import textstat

from joshua7.models import Severity, ValidationFinding, ValidationResult
from joshua7.validators.base import BaseValidator


class ReadabilityScorer(BaseValidator):
    """Ensure content falls within an acceptable Flesch readability range."""

    name = "readability"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        super().__init__(config)
        self._min_score = float(self.config.get("readability_min_score", 30.0))
        self._max_score = float(self.config.get("readability_max_score", 80.0))

    def validate(self, text: str) -> ValidationResult:
        findings: list[ValidationFinding] = []

        fk_score = textstat.flesch_reading_ease(text)
        grade_level = textstat.flesch_kincaid_grade(text)

        passed = self._min_score <= fk_score <= self._max_score

        if fk_score < self._min_score:
            findings.append(
                ValidationFinding(
                    validator_name=self.name,
                    severity=Severity.WARNING,
                    message=(
                        f"Content too complex: Flesch score {fk_score:.1f} "
                        f"below minimum {self._min_score}"
                    ),
                    metadata={
                        "flesch_score": fk_score,
                        "grade_level": grade_level,
                        "threshold": "min",
                    },
                )
            )
        elif fk_score > self._max_score:
            findings.append(
                ValidationFinding(
                    validator_name=self.name,
                    severity=Severity.WARNING,
                    message=(
                        f"Content too simple: Flesch score {fk_score:.1f} "
                        f"above maximum {self._max_score}"
                    ),
                    metadata={
                        "flesch_score": fk_score,
                        "grade_level": grade_level,
                        "threshold": "max",
                    },
                )
            )
        else:
            findings.append(
                ValidationFinding(
                    validator_name=self.name,
                    severity=Severity.INFO,
                    message=f"Flesch score {fk_score:.1f}, grade level {grade_level:.1f}",
                    metadata={
                        "flesch_score": fk_score,
                        "grade_level": grade_level,
                    },
                )
            )

        clamped = max(0.0, min(100.0, fk_score))

        return ValidationResult(
            validator_name=self.name,
            passed=passed,
            score=round(clamped, 1),
            findings=findings,
        )
