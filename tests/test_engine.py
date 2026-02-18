"""Tests for the validation engine."""

from joshua7.config import Settings
from joshua7.engine import ValidationEngine
from joshua7.models import ValidationRequest


class TestValidationEngine:
    def _engine(self) -> ValidationEngine:
        return ValidationEngine(settings=Settings())

    def test_available_validators(self):
        engine = self._engine()
        names = engine.available_validators
        assert "forbidden_phrases" in names
        assert "pii" in names
        assert "brand_voice" in names
        assert "prompt_injection" in names
        assert "readability" in names

    def test_validate_clean_text(self):
        engine = self._engine()
        response = engine.validate_text(
            "We deliver professional solutions for our customers every day."
        )
        assert response.validators_run == 5
        assert response.text_length > 0

    def test_validate_with_pii(self):
        engine = self._engine()
        response = engine.validate_text("Contact john@example.com for info.")
        assert response.passed is False
        pii_result = next(r for r in response.results if r.validator_name == "pii")
        assert pii_result.passed is False

    def test_validate_subset(self):
        engine = self._engine()
        response = engine.validate_text(
            "Just a test.",
            validators=["forbidden_phrases", "pii"],
        )
        assert response.validators_run == 2
        names = {r.validator_name for r in response.results}
        assert names == {"forbidden_phrases", "pii"}

    def test_validate_all_keyword(self):
        engine = self._engine()
        request = ValidationRequest(text="Hello world.", validators=["all"])
        response = engine.run(request)
        assert response.validators_run == 5

    def test_unknown_validator_ignored(self):
        engine = self._engine()
        response = engine.validate_text("Hello.", validators=["nonexistent"])
        assert response.validators_run == 0

    def test_config_overrides(self):
        engine = self._engine()
        request = ValidationRequest(
            text="This has a banana in it.",
            validators=["forbidden_phrases"],
            config_overrides={
                "forbidden_phrases": {"forbidden_phrases": ["banana"]},
            },
        )
        response = engine.run(request)
        fp_result = next(r for r in response.results if r.validator_name == "forbidden_phrases")
        assert fp_result.passed is False

    def test_response_model(self):
        engine = self._engine()
        response = engine.validate_text("Short text.")
        assert hasattr(response, "passed")
        assert hasattr(response, "results")
        assert hasattr(response, "text_length")
        assert hasattr(response, "validators_run")
