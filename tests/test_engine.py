"""Tests for the validation engine."""

from unittest.mock import patch

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
        assert response.passed is False

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

    def test_response_model_fields(self):
        engine = self._engine()
        response = engine.validate_text("Short text.")
        assert hasattr(response, "passed")
        assert hasattr(response, "results")
        assert hasattr(response, "text_length")
        assert hasattr(response, "validators_run")

    def test_response_has_request_id(self):
        engine = self._engine()
        response = engine.validate_text("Content here.")
        assert response.request_id is not None
        assert len(response.request_id) > 0

    def test_response_has_version(self):
        engine = self._engine()
        response = engine.validate_text("Content here.")
        assert response.version != ""

    def test_response_has_timestamp(self):
        engine = self._engine()
        response = engine.validate_text("Content here.")
        assert response.timestamp is not None
        assert "T" in response.timestamp

    def test_custom_request_id_propagated(self):
        engine = self._engine()
        response = engine.validate_text("Content.", request_id="test-123")
        assert response.request_id == "test-123"

    def test_validator_exception_does_not_crash(self):
        """If a validator throws, the engine should catch it and report failure."""
        engine = self._engine()
        with patch.object(
            engine._validators["readability"],
            "validate",
            side_effect=RuntimeError("boom"),
        ):
            response = engine.validate_text("Normal content for testing.")
        assert response.validators_run == 5
        readability = next(r for r in response.results if r.validator_name == "readability")
        assert readability.passed is False

    def test_unicode_content(self):
        engine = self._engine()
        response = engine.validate_text("Héllo wörld! 你好世界 🌍")
        assert response.text_length > 0
        assert response.validators_run == 5

    def test_max_text_length_enforced(self):
        settings = Settings(max_text_length=50)
        engine = ValidationEngine(settings=settings)
        response = engine.validate_text("A" * 100)
        assert response.passed is False
        assert response.validators_run == 0
        assert any("exceeds" in f.message for r in response.results for f in r.findings)

    def test_max_text_length_allows_under_limit(self):
        settings = Settings(max_text_length=500)
        engine = ValidationEngine(settings=settings)
        response = engine.validate_text("Short text.")
        assert response.validators_run == 5

    def test_exception_emits_error_finding(self):
        """When a validator raises, the engine should emit an error finding."""
        engine = self._engine()
        with patch.object(
            engine._validators["readability"],
            "validate",
            side_effect=RuntimeError("test error"),
        ):
            response = engine.validate_text("Normal content for testing.")
        readability = next(r for r in response.results if r.validator_name == "readability")
        assert readability.passed is False
        assert len(readability.findings) == 1
        assert "internal error" in readability.findings[0].message.lower()

    def test_findings_capped(self):
        """Findings count per validator must not exceed max_findings_per_validator."""
        settings = Settings(max_findings_per_validator=2)
        engine = ValidationEngine(settings=settings)
        request = ValidationRequest(
            text="bad bad bad bad bad",
            validators=["forbidden_phrases"],
            config_overrides={
                "forbidden_phrases": {"forbidden_phrases": ["bad"]},
            },
        )
        response = engine.run(request)
        fp = next(r for r in response.results if r.validator_name == "forbidden_phrases")
        assert len(fp.findings) <= 2

    def test_unsafe_config_override_blocked(self):
        """Security-sensitive config keys like pii_patterns_enabled must be ignored."""
        engine = self._engine()
        request = ValidationRequest(
            text="Contact me at user@example.com",
            validators=["pii"],
            config_overrides={
                "pii": {"pii_patterns_enabled": []},
            },
        )
        response = engine.run(request)
        pii = next(r for r in response.results if r.validator_name == "pii")
        assert pii.passed is False

    def test_api_key_not_in_validator_config(self):
        """The API key must never be passed to validators."""
        settings = Settings(api_key="supersecret")
        engine = ValidationEngine(settings=settings)
        config = engine._settings_to_config()
        assert "api_key" not in config
