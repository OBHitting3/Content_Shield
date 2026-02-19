"""RISK_TAXONOMY_v0 — Composite risk scoring model for content validation.

Five risk axes, each mapped to a validator, produce per-axis scores (0–100,
where 100 = safest).  The weighted composite score is returned alongside the
per-axis breakdown.

Axis definitions and weights
-----------------------------
A  Synthetic Content Artifacts   30 %  → forbidden_phrases
B  Privacy & Data Exposure       25 %  → pii
C  Adversarial Manipulation      25 %  → prompt_injection
D  Brand Alignment               10 %  → brand_voice
E  Readability & Accessibility   10 %  → readability
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from joshua7.models import ValidationResponse, ValidationResult

TAXONOMY_VERSION = "v0"


@dataclass(frozen=True)
class RiskAxis:
    """Definition of a single risk axis."""

    code: str
    name: str
    weight: float
    validator_name: str


RISK_AXES: tuple[RiskAxis, ...] = (
    RiskAxis(
        code="A", name="Synthetic Content Artifacts",
        weight=0.30, validator_name="forbidden_phrases",
    ),
    RiskAxis(
        code="B", name="Privacy & Data Exposure",
        weight=0.25, validator_name="pii",
    ),
    RiskAxis(
        code="C", name="Adversarial Manipulation",
        weight=0.25, validator_name="prompt_injection",
    ),
    RiskAxis(
        code="D", name="Brand Alignment",
        weight=0.10, validator_name="brand_voice",
    ),
    RiskAxis(
        code="E", name="Readability & Accessibility",
        weight=0.10, validator_name="readability",
    ),
)

AXIS_MAP: dict[str, RiskAxis] = {a.code: a for a in RISK_AXES}
VALIDATOR_TO_AXIS: dict[str, RiskAxis] = {a.validator_name: a for a in RISK_AXES}


@dataclass
class AxisScore:
    """Score for a single risk axis."""

    code: str
    name: str
    weight: float
    score: float
    passed: bool
    finding_count: int
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "weight": self.weight,
            "score": round(self.score, 1),
            "passed": self.passed,
            "finding_count": self.finding_count,
            "details": self.details,
        }


@dataclass
class RiskReport:
    """Full risk taxonomy report with composite and per-axis scores."""

    taxonomy_version: str
    composite_score: float
    composite_passed: bool
    axes: list[AxisScore]

    def to_dict(self) -> dict[str, Any]:
        return {
            "taxonomy_version": self.taxonomy_version,
            "composite_score": round(self.composite_score, 1),
            "composite_passed": self.composite_passed,
            "axes": [a.to_dict() for a in self.axes],
        }


def _score_from_result(axis: RiskAxis, result: ValidationResult) -> AxisScore:
    """Derive a 0–100 safety score from a validator result.

    Validators that already emit a numeric score (prompt_injection,
    brand_voice, readability) have that score carried forward.  For boolean
    validators (forbidden_phrases, pii), the score is derived from findings.
    """
    finding_count = len(result.findings)
    details: dict[str, Any] = {}

    if result.score is not None:
        score = float(result.score)
        details["raw_score"] = result.score
    elif finding_count == 0:
        score = 100.0
    else:
        penalty_per_finding = 25.0
        score = max(0.0, 100.0 - finding_count * penalty_per_finding)
        details["penalty_per_finding"] = penalty_per_finding

    score = max(0.0, min(100.0, score))
    details["finding_count"] = finding_count

    return AxisScore(
        code=axis.code,
        name=axis.name,
        weight=axis.weight,
        score=score,
        passed=result.passed,
        finding_count=finding_count,
        details=details,
    )


def _placeholder_axis(axis: RiskAxis) -> AxisScore:
    """Return a neutral axis score when the validator was not run."""
    return AxisScore(
        code=axis.code,
        name=axis.name,
        weight=axis.weight,
        score=100.0,
        passed=True,
        finding_count=0,
        details={"skipped": True},
    )


def compute_risk(response: ValidationResponse) -> RiskReport:
    """Compute the RISK_TAXONOMY_v0 composite score from a ValidationResponse."""
    result_map: dict[str, ValidationResult] = {
        r.validator_name: r for r in response.results
    }

    axes: list[AxisScore] = []
    for axis in RISK_AXES:
        result = result_map.get(axis.validator_name)
        if result is not None:
            axes.append(_score_from_result(axis, result))
        else:
            axes.append(_placeholder_axis(axis))

    composite = sum(a.score * a.weight for a in axes)
    composite = max(0.0, min(100.0, composite))
    composite_passed = all(a.passed for a in axes)

    return RiskReport(
        taxonomy_version=TAXONOMY_VERSION,
        composite_score=composite,
        composite_passed=composite_passed,
        axes=axes,
    )
