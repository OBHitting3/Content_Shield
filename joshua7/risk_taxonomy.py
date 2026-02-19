"""RISK_TAXONOMY_v0 — Composite scoring model for content risk assessment.

Defines 5 weighted risk axes that map validator results into a unified risk score.
Each axis normalises its constituent validator outputs to a 0–100 scale, where
100 = no risk detected and 0 = maximum risk.  The composite score is the
weighted average across all axes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from joshua7.models import Severity, ValidationResult

logger = logging.getLogger(__name__)

TAXONOMY_VERSION = "v0"

_SEVERITY_PENALTY: dict[str, float] = {
    Severity.INFO: 0.0,
    Severity.WARNING: 5.0,
    Severity.ERROR: 15.0,
    Severity.CRITICAL: 30.0,
}


@dataclass(frozen=True)
class RiskAxisDefinition:
    """Static definition of one risk axis."""

    axis_id: str
    name: str
    weight: float
    validator_names: tuple[str, ...]
    description: str = ""


RISK_AXES: tuple[RiskAxisDefinition, ...] = (
    RiskAxisDefinition(
        axis_id="A",
        name="Synthetic Content Artifacts",
        weight=0.30,
        validator_names=("forbidden_phrases", "brand_voice"),
        description="Detects AI-generated phrasing, forbidden clichés, and off-brand tone.",
    ),
    RiskAxisDefinition(
        axis_id="B",
        name="PII Exposure",
        weight=0.25,
        validator_names=("pii",),
        description="Flags personally identifiable information leakage.",
    ),
    RiskAxisDefinition(
        axis_id="C",
        name="Prompt Injection / Adversarial",
        weight=0.25,
        validator_names=("prompt_injection",),
        description="Catches hidden prompt-injection and jailbreak attempts.",
    ),
    RiskAxisDefinition(
        axis_id="D",
        name="Readability & Audience Fit",
        weight=0.10,
        validator_names=("readability",),
        description="Ensures content readability falls within target range.",
    ),
    RiskAxisDefinition(
        axis_id="E",
        name="Overall Coherence & Policy Compliance",
        weight=0.10,
        validator_names=(),
        description="Aggregate policy compliance derived from all validator signals.",
    ),
)


@dataclass
class AxisScore:
    """Computed score for a single risk axis."""

    axis_id: str
    name: str
    weight: float
    score: float
    weighted_score: float
    contributing_validators: list[str] = field(default_factory=list)


@dataclass
class CompositeRiskScore:
    """Full risk assessment output."""

    taxonomy_version: str
    composite_score: float
    risk_level: str
    axes: list[AxisScore]
    passed: bool


def _score_from_result(result: ValidationResult) -> float:
    """Derive a 0–100 safety score from a single validator result.

    Validators that already emit a numeric score use it directly.
    For binary pass/fail validators the score is derived from findings.
    """
    if result.score is not None:
        return max(0.0, min(100.0, result.score))

    if result.passed and not result.findings:
        return 100.0

    penalty = sum(
        _SEVERITY_PENALTY.get(f.severity, 10.0) for f in result.findings
    )
    return max(0.0, 100.0 - penalty)


def _classify_risk(score: float) -> str:
    """Map composite score to a human-readable risk level."""
    if score >= 90.0:
        return "low"
    if score >= 70.0:
        return "moderate"
    if score >= 50.0:
        return "elevated"
    if score >= 30.0:
        return "high"
    return "critical"


def compute_composite_score(
    results: list[ValidationResult],
    axes: tuple[RiskAxisDefinition, ...] | None = None,
) -> CompositeRiskScore:
    """Compute the RISK_TAXONOMY_v0 composite risk score.

    Parameters
    ----------
    results:
        Validation results keyed or listed by validator name.
    axes:
        Override axis definitions (defaults to ``RISK_AXES``).
    """
    axis_defs = axes or RISK_AXES
    results_by_name: dict[str, ValidationResult] = {r.validator_name: r for r in results}

    all_scores: list[float] = []
    for r in results:
        all_scores.append(_score_from_result(r))
    global_avg = sum(all_scores) / max(len(all_scores), 1) if all_scores else 100.0

    axis_scores: list[AxisScore] = []
    total_weight = 0.0
    weighted_sum = 0.0

    for ax in axis_defs:
        if ax.axis_id == "E" and not ax.validator_names:
            axis_raw = global_avg
            contributors: list[str] = list(results_by_name.keys())
        else:
            matched = [
                _score_from_result(results_by_name[vn])
                for vn in ax.validator_names
                if vn in results_by_name
            ]
            contributors = [vn for vn in ax.validator_names if vn in results_by_name]
            axis_raw = sum(matched) / max(len(matched), 1) if matched else 100.0

        axis_raw = round(max(0.0, min(100.0, axis_raw)), 1)
        ws = round(axis_raw * ax.weight, 2)

        axis_scores.append(
            AxisScore(
                axis_id=ax.axis_id,
                name=ax.name,
                weight=ax.weight,
                score=axis_raw,
                weighted_score=ws,
                contributing_validators=contributors,
            )
        )
        total_weight += ax.weight
        weighted_sum += ws

    composite = round(weighted_sum / max(total_weight, 1e-9), 1) if total_weight else 100.0
    composite = max(0.0, min(100.0, composite))

    return CompositeRiskScore(
        taxonomy_version=TAXONOMY_VERSION,
        composite_score=composite,
        risk_level=_classify_risk(composite),
        axes=axis_scores,
        passed=composite >= 70.0,
    )


def composite_score_to_dict(score: CompositeRiskScore) -> dict[str, Any]:
    """Serialise a CompositeRiskScore to a plain dict for JSON responses."""
    return {
        "taxonomy_version": score.taxonomy_version,
        "composite_score": score.composite_score,
        "risk_level": score.risk_level,
        "passed": score.passed,
        "axes": [
            {
                "axis_id": a.axis_id,
                "name": a.name,
                "weight": a.weight,
                "score": a.score,
                "weighted_score": a.weighted_score,
                "contributing_validators": a.contributing_validators,
            }
            for a in score.axes
        ],
    }
