"""Validation engine — orchestrates all validators against incoming content."""

from __future__ import annotations

import logging
import re
import unicodedata
import uuid
from typing import Any

from joshua7 import __version__
from joshua7.config import Settings, get_settings
from joshua7.models import (
    RiskAxis,
    RiskTaxonomy,
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

_LOCKED_OVERRIDE_KEYS: set[str] = {
    "pii_patterns_enabled",
    "forbidden_phrases",
    "max_text_length",
}

# ---------------------------------------------------------------------------
# Input normalisation — defeat zero-width char and homoglyph evasion
# ---------------------------------------------------------------------------
_ZERO_WIDTH_RE = re.compile(
    "[\u200b\u200c\u200d\u200e\u200f\u2060\u2061\u2062\u2063\u2064\ufeff]"
)

_HOMOGLYPH_MAP: dict[str, str] = {
    "\u0410": "A", "\u0412": "B", "\u0421": "C", "\u0415": "E",
    "\u041d": "H", "\u041a": "K", "\u041c": "M", "\u041e": "O",
    "\u0420": "P", "\u0422": "T", "\u0425": "X",
    "\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0440": "p",
    "\u0441": "c", "\u0443": "y", "\u0445": "x",
    "\uff21": "A", "\uff22": "B", "\uff23": "C", "\uff24": "D",
    "\uff25": "E", "\uff26": "F", "\uff27": "G", "\uff28": "H",
    "\uff29": "I", "\uff2a": "J", "\uff2b": "K", "\uff2c": "L",
    "\uff2d": "M", "\uff2e": "N", "\uff2f": "O", "\uff30": "P",
    "\uff31": "Q", "\uff32": "R", "\uff33": "S", "\uff34": "T",
    "\uff35": "U", "\uff36": "V", "\uff37": "W", "\uff38": "X",
    "\uff39": "Y", "\uff3a": "Z",
    "\uff41": "a", "\uff42": "b", "\uff43": "c", "\uff44": "d",
    "\uff45": "e", "\uff46": "f", "\uff47": "g", "\uff48": "h",
    "\uff49": "i", "\uff4a": "j", "\uff4b": "k", "\uff4c": "l",
    "\uff4d": "m", "\uff4e": "n", "\uff4f": "o", "\uff50": "p",
    "\uff51": "q", "\uff52": "r", "\uff53": "s", "\uff54": "t",
    "\uff55": "u", "\uff56": "v", "\uff57": "w", "\uff58": "x",
    "\uff59": "y", "\uff5a": "z",
}


def normalize_text(text: str) -> str:
    """Apply Unicode NFKC normalisation, strip zero-width characters, and
    replace common Cyrillic / fullwidth homoglyphs with their ASCII equivalents.

    The original text is preserved for span-offset reporting; this normalized
    copy is used only for pattern matching inside validators.
    """
    text = unicodedata.normalize("NFKC", text)
    text = _ZERO_WIDTH_RE.sub("", text)
    for glyph, replacement in _HOMOGLYPH_MAP.items():
        if glyph in text:
            text = text.replace(glyph, replacement)
    return text


# ---------------------------------------------------------------------------
# RISK_TAXONOMY_v0 — weighted composite scoring
# ---------------------------------------------------------------------------
_SEVERITY_POINTS = {
    Severity.INFO: 0,
    Severity.WARNING: 15,
    Severity.ERROR: 40,
    Severity.CRITICAL: 80,
}

_RISK_AXES: list[dict[str, Any]] = [
    {"axis": "A", "label": "Synthetic Artifacts", "weight": 0.30,
     "validators": ["forbidden_phrases", "readability"]},
    {"axis": "B", "label": "Hallucination / Factual Integrity", "weight": 0.25,
     "validators": ["readability"]},
    {"axis": "C", "label": "Brand Safety / GARM", "weight": 0.20,
     "validators": ["brand_voice"]},
    {"axis": "D", "label": "Regulatory Compliance / PII+Disclosure", "weight": 0.15,
     "validators": ["pii"]},
    {"axis": "E", "label": "Adversarial Robustness / Injection", "weight": 0.10,
     "validators": ["prompt_injection"]},
]


def _risk_level(score: float) -> str:
    if score < 20:
        return "GREEN"
    if score < 50:
        return "YELLOW"
    if score < 80:
        return "ORANGE"
    return "RED"


def _axis_score_from_results(
    validator_names: list[str],
    results_map: dict[str, ValidationResult],
) -> float:
    """Derive a 0-100 raw axis score from the mapped validators' findings."""
    total_points = 0.0
    contributor_count = 0

    for vname in validator_names:
        result = results_map.get(vname)
        if result is None:
            continue
        contributor_count += 1

        if result.passed and not result.findings:
            continue

        if not result.passed and result.score is not None:
            inverted = max(0.0, 100.0 - result.score)
            total_points += inverted
            continue

        finding_points = sum(
            _SEVERITY_POINTS.get(f.severity, 0) for f in result.findings
        )
        total_points += min(finding_points, 100.0)

    if contributor_count == 0:
        return 0.0
    return min(total_points / contributor_count, 100.0)


def _critical_escalation(results: list[ValidationResult]) -> float:
    """Return an escalation bonus based on CRITICAL-severity findings.

    CRITICAL findings represent hard failures (PII leaks, active injection
    attacks) that must dominate the composite regardless of axis weight.

    Escalation schedule:
        1 CRITICAL axis  → +40  (guarantees YELLOW, likely ORANGE with base)
        2 CRITICAL axes  → +80  (guarantees RED with any non-zero base)
        3+ CRITICAL axes → +100 (hard RED)
    """
    axes_with_criticals: set[str] = set()
    results_map = {r.validator_name: r for r in results}

    for axis_def in _RISK_AXES:
        for vname in axis_def["validators"]:
            result = results_map.get(vname)
            if result is None:
                continue
            if any(f.severity == Severity.CRITICAL for f in result.findings):
                axes_with_criticals.add(axis_def["axis"])
                break

    n = len(axes_with_criticals)
    if n == 0:
        return 0.0
    if n == 1:
        return 40.0
    if n == 2:
        return 80.0
    return 100.0


def compute_risk_taxonomy(results: list[ValidationResult]) -> RiskTaxonomy:
    """Build a RISK_TAXONOMY_v0 from a list of validator results."""
    results_map = {r.validator_name: r for r in results}
    axes: list[RiskAxis] = []
    weighted_sum = 0.0

    for axis_def in _RISK_AXES:
        raw = _axis_score_from_results(axis_def["validators"], results_map)
        weighted = raw * axis_def["weight"]
        weighted_sum += weighted
        axes.append(RiskAxis(
            axis=axis_def["axis"],
            label=axis_def["label"],
            weight=axis_def["weight"],
            raw_score=round(raw, 1),
            weighted_score=round(weighted, 2),
        ))

    escalation = _critical_escalation(results)
    composite = round(min(weighted_sum + escalation, 100.0), 1)

    return RiskTaxonomy(
        composite_risk_score=composite,
        risk_level=_risk_level(composite),
        axes=axes,
    )


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
                risk=RiskTaxonomy(
                    composite_risk_score=100.0,
                    risk_level="RED",
                    axes=[],
                ),
                text_length=len(request.text),
                validators_run=0,
            )

        normalized = normalize_text(request.text)
        overrides = self._sanitize_overrides(request.config_overrides)
        selected = self._resolve_validators(request.validators)
        results: list[ValidationResult] = []

        for name in selected:
            validator = self._validators[name]
            if name in overrides:
                merged = {**self._settings_to_config(), **overrides[name]}
                validator = _REGISTRY[name](config=merged)
            try:
                result = validator.validate(normalized)
            except Exception:
                logger.exception("Validator '%s' raised an exception", name)
                result = ValidationResult(
                    validator_name=name,
                    passed=False,
                    findings=[],
                )
            results.append(result)

        all_passed = bool(results) and all(r.passed for r in results)
        risk = compute_risk_taxonomy(results)

        return ValidationResponse(
            request_id=rid,
            version=__version__,
            passed=all_passed,
            results=results,
            risk=risk,
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

    @staticmethod
    def _sanitize_overrides(
        raw: dict[str, Any],
    ) -> dict[str, Any]:
        """Strip security-critical keys from per-request config overrides.

        Prevents callers from disabling PII detection, clearing the
        forbidden-phrases list, or raising the max text length at runtime.
        """
        max_override_size = 16_384

        serialized_len = sum(
            len(str(k)) + len(str(v)) for k, v in raw.items()
        )
        if serialized_len > max_override_size:
            logger.warning(
                "config_overrides payload too large (%d chars) — ignoring",
                serialized_len,
            )
            return {}

        cleaned: dict[str, Any] = {}
        for validator_name, overrides in raw.items():
            if not isinstance(overrides, dict):
                logger.warning(
                    "config_overrides[%s] is not a dict — ignoring",
                    validator_name,
                )
                continue
            filtered = {
                k: v for k, v in overrides.items()
                if k not in _LOCKED_OVERRIDE_KEYS
            }
            stripped = set(overrides.keys()) - set(filtered.keys())
            if stripped:
                logger.warning(
                    "Blocked security-locked override keys for '%s': %s",
                    validator_name,
                    stripped,
                )
            if filtered:
                cleaned[validator_name] = filtered
        return cleaned

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
