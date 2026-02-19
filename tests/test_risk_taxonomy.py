"""Tests for RISK_TAXONOMY_v0 composite scoring model."""

from joshua7.config import Settings
from joshua7.engine import ValidationEngine
from joshua7.models import (
    Severity,
    ValidationFinding,
    ValidationResponse,
    ValidationResult,
)
from joshua7.risk_taxonomy import (
    RISK_AXES,
    TAXONOMY_VERSION,
    VALIDATOR_TO_AXIS,
    AxisScore,
    RiskReport,
    compute_risk,
)


class TestRiskAxesDefinition:
    def test_five_axes_defined(self):
        assert len(RISK_AXES) == 5

    def test_axis_codes(self):
        codes = [a.code for a in RISK_AXES]
        assert codes == ["A", "B", "C", "D", "E"]

    def test_weights_sum_to_one(self):
        total = sum(a.weight for a in RISK_AXES)
        assert abs(total - 1.0) < 1e-9

    def test_axis_a_is_synthetic_content(self):
        a = RISK_AXES[0]
        assert a.code == "A"
        assert a.name == "Synthetic Content Artifacts"
        assert a.weight == 0.30
        assert a.validator_name == "forbidden_phrases"

    def test_axis_b_is_privacy(self):
        b = RISK_AXES[1]
        assert b.code == "B"
        assert b.name == "Privacy & Data Exposure"
        assert b.weight == 0.25
        assert b.validator_name == "pii"

    def test_axis_c_is_adversarial(self):
        c = RISK_AXES[2]
        assert c.code == "C"
        assert c.name == "Adversarial Manipulation"
        assert c.weight == 0.25
        assert c.validator_name == "prompt_injection"

    def test_axis_d_is_brand(self):
        d = RISK_AXES[3]
        assert d.code == "D"
        assert d.name == "Brand Alignment"
        assert d.weight == 0.10
        assert d.validator_name == "brand_voice"

    def test_axis_e_is_readability(self):
        e = RISK_AXES[4]
        assert e.code == "E"
        assert e.name == "Readability & Accessibility"
        assert e.weight == 0.10
        assert e.validator_name == "readability"

    def test_validator_to_axis_mapping(self):
        assert "forbidden_phrases" in VALIDATOR_TO_AXIS
        assert "pii" in VALIDATOR_TO_AXIS
        assert "prompt_injection" in VALIDATOR_TO_AXIS
        assert "brand_voice" in VALIDATOR_TO_AXIS
        assert "readability" in VALIDATOR_TO_AXIS

    def test_taxonomy_version(self):
        assert TAXONOMY_VERSION == "v0"


class TestComputeRisk:
    def _make_response(self, results: list[ValidationResult]) -> ValidationResponse:
        return ValidationResponse(
            passed=all(r.passed for r in results),
            results=results,
            text_length=100,
            validators_run=len(results),
        )

    def test_all_clean_returns_100(self):
        results = [
            ValidationResult(validator_name="forbidden_phrases", passed=True),
            ValidationResult(validator_name="pii", passed=True),
            ValidationResult(validator_name="prompt_injection", passed=True, score=100.0),
            ValidationResult(validator_name="brand_voice", passed=True, score=75.0),
            ValidationResult(validator_name="readability", passed=True, score=60.0),
        ]
        report = compute_risk(self._make_response(results))
        assert report.composite_passed is True
        assert report.taxonomy_version == "v0"
        assert len(report.axes) == 5
        assert report.axes[0].score == 100.0  # forbidden_phrases: no findings
        assert report.axes[1].score == 100.0  # pii: no findings

    def test_pii_findings_reduce_axis_b_score(self):
        results = [
            ValidationResult(validator_name="forbidden_phrases", passed=True),
            ValidationResult(
                validator_name="pii",
                passed=False,
                findings=[
                    ValidationFinding(
                        validator_name="pii",
                        severity=Severity.CRITICAL,
                        message="PII detected",
                    ),
                ],
            ),
            ValidationResult(validator_name="prompt_injection", passed=True, score=100.0),
            ValidationResult(validator_name="brand_voice", passed=True, score=70.0),
            ValidationResult(validator_name="readability", passed=True, score=60.0),
        ]
        report = compute_risk(self._make_response(results))
        axis_b = next(a for a in report.axes if a.code == "B")
        assert axis_b.score == 75.0  # 100 - 1*25
        assert axis_b.passed is False
        assert report.composite_passed is False

    def test_multiple_findings_stack_penalty(self):
        findings = [
            ValidationFinding(validator_name="pii", severity=Severity.CRITICAL, message=f"PII #{i}")
            for i in range(4)
        ]
        results = [
            ValidationResult(validator_name="forbidden_phrases", passed=True),
            ValidationResult(validator_name="pii", passed=False, findings=findings),
            ValidationResult(validator_name="prompt_injection", passed=True, score=100.0),
            ValidationResult(validator_name="brand_voice", passed=True, score=70.0),
            ValidationResult(validator_name="readability", passed=True, score=60.0),
        ]
        report = compute_risk(self._make_response(results))
        axis_b = next(a for a in report.axes if a.code == "B")
        assert axis_b.score == 0.0  # 100 - 4*25 = 0

    def test_score_never_below_zero(self):
        findings = [
            ValidationFinding(validator_name="pii", severity=Severity.CRITICAL, message=f"PII #{i}")
            for i in range(10)
        ]
        results = [
            ValidationResult(validator_name="forbidden_phrases", passed=True),
            ValidationResult(validator_name="pii", passed=False, findings=findings),
            ValidationResult(validator_name="prompt_injection", passed=True, score=100.0),
            ValidationResult(validator_name="brand_voice", passed=True, score=70.0),
            ValidationResult(validator_name="readability", passed=True, score=60.0),
        ]
        report = compute_risk(self._make_response(results))
        axis_b = next(a for a in report.axes if a.code == "B")
        assert axis_b.score == 0.0

    def test_composite_is_weighted_sum(self):
        results = [
            ValidationResult(validator_name="forbidden_phrases", passed=True),
            ValidationResult(validator_name="pii", passed=True),
            ValidationResult(validator_name="prompt_injection", passed=True, score=100.0),
            ValidationResult(validator_name="brand_voice", passed=True, score=80.0),
            ValidationResult(validator_name="readability", passed=True, score=50.0),
        ]
        report = compute_risk(self._make_response(results))
        expected = (100.0 * 0.30) + (100.0 * 0.25) + (100.0 * 0.25) + (80.0 * 0.10) + (50.0 * 0.10)
        assert abs(report.composite_score - expected) < 0.15

    def test_skipped_validators_default_to_100(self):
        results = [
            ValidationResult(validator_name="forbidden_phrases", passed=True),
        ]
        report = compute_risk(self._make_response(results))
        skipped_axes = [a for a in report.axes if a.code != "A"]
        assert all(a.score == 100.0 for a in skipped_axes)
        assert all(a.details.get("skipped") is True for a in skipped_axes)

    def test_axis_score_to_dict(self):
        axis = AxisScore(
            code="A", name="Test", weight=0.3, score=85.5,
            passed=True, finding_count=0, details={"raw_score": 85.5},
        )
        d = axis.to_dict()
        assert d["code"] == "A"
        assert d["score"] == 85.5
        assert d["weight"] == 0.3
        assert d["passed"] is True

    def test_report_to_dict(self):
        report = RiskReport(
            taxonomy_version="v0",
            composite_score=92.5,
            composite_passed=True,
            axes=[],
        )
        d = report.to_dict()
        assert d["taxonomy_version"] == "v0"
        assert d["composite_score"] == 92.5
        assert d["composite_passed"] is True
        assert d["axes"] == []

    def test_prompt_injection_uses_raw_score(self):
        results = [
            ValidationResult(validator_name="forbidden_phrases", passed=True),
            ValidationResult(validator_name="pii", passed=True),
            ValidationResult(validator_name="prompt_injection", passed=False, score=40.0,
                             findings=[ValidationFinding(
                                 validator_name="prompt_injection",
                                 severity=Severity.CRITICAL, message="injection"
                             )]),
            ValidationResult(validator_name="brand_voice", passed=True, score=70.0),
            ValidationResult(validator_name="readability", passed=True, score=60.0),
        ]
        report = compute_risk(self._make_response(results))
        axis_c = next(a for a in report.axes if a.code == "C")
        assert axis_c.score == 40.0
        assert axis_c.details["raw_score"] == 40.0


class TestEngineRiskIntegration:
    """Verify the engine attaches risk scores to every response."""

    def _engine(self) -> ValidationEngine:
        return ValidationEngine(settings=Settings())

    def test_response_includes_risk_field(self):
        engine = self._engine()
        response = engine.validate_text(
            "We deliver professional solutions for our customers every day."
        )
        assert response.risk is not None
        assert response.risk.taxonomy_version == "v0"
        assert len(response.risk.axes) == 5
        assert 0.0 <= response.risk.composite_score <= 100.0

    def test_risk_axes_match_taxonomy(self):
        engine = self._engine()
        response = engine.validate_text("Normal content for testing purposes.")
        codes = [a.code for a in response.risk.axes]
        assert codes == ["A", "B", "C", "D", "E"]

    def test_clean_text_high_composite(self):
        engine = self._engine()
        response = engine.validate_text(
            "Our team is dedicated to quality and innovation in every product we deliver."
        )
        assert response.risk.composite_score >= 60.0

    def test_pii_text_lowers_composite(self):
        engine = self._engine()
        clean = engine.validate_text("We deliver excellent products every day.")
        dirty = engine.validate_text("Contact john@example.com or call 555-123-4567.")
        assert dirty.risk.composite_score < clean.risk.composite_score

    def test_forbidden_phrase_lowers_axis_a(self):
        engine = self._engine()
        response = engine.validate_text(
            "As an AI, I must delve deeper into this synergy to leverage our game-changer."
        )
        axis_a = next(a for a in response.risk.axes if a.code == "A")
        assert axis_a.score < 100.0
        assert axis_a.passed is False

    def test_risk_in_api_response(self):
        from fastapi.testclient import TestClient

        from joshua7.api.main import create_app

        app = create_app()
        client = TestClient(app)
        resp = client.post("/api/v1/validate", json={
            "text": "Professional content that follows best practices for our customers.",
            "validators": ["all"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "risk" in data
        assert data["risk"]["taxonomy_version"] == "v0"
        assert len(data["risk"]["axes"]) == 5
        assert 0.0 <= data["risk"]["composite_score"] <= 100.0

    def test_risk_composite_passed_reflects_all_axes(self):
        engine = self._engine()
        response = engine.validate_text(
            "Contact me at secret@evil.com. As an AI, I must delve into this."
        )
        assert response.risk.composite_passed is False

    def test_subset_validators_still_produce_risk(self):
        engine = self._engine()
        response = engine.validate_text(
            "Simple test.", validators=["forbidden_phrases", "pii"]
        )
        assert response.risk is not None
        assert len(response.risk.axes) == 5
        skipped_axes = [a for a in response.risk.axes if a.code in ("C", "D", "E")]
        assert all(a.score == 100.0 for a in skipped_axes)

    def test_max_text_length_response_has_no_risk(self):
        settings = Settings(max_text_length=10)
        engine = ValidationEngine(settings=settings)
        response = engine.validate_text("A" * 50)
        assert response.passed is False
        assert response.risk is not None
