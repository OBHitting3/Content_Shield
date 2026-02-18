"""Tests for the PII Validator."""

from joshua7.validators.pii import PIIValidator


class TestPIIValidator:
    def test_clean_text_passes(self):
        v = PIIValidator()
        result = v.validate("No personal information here.")
        assert result.passed is True
        assert len(result.findings) == 0

    def test_detects_email(self):
        v = PIIValidator()
        result = v.validate("Contact us at john.doe@example.com for info.")
        assert result.passed is False
        assert any(f.metadata.get("pii_type") == "email" for f in result.findings)

    def test_detects_phone(self):
        v = PIIValidator()
        result = v.validate("Call me at (555) 123-4567 anytime.")
        assert result.passed is False
        assert any(f.metadata.get("pii_type") == "phone" for f in result.findings)

    def test_detects_ssn(self):
        v = PIIValidator()
        result = v.validate("My SSN is 123-45-6789.")
        assert result.passed is False
        assert any(f.metadata.get("pii_type") == "ssn" for f in result.findings)

    def test_detects_multiple_pii(self):
        v = PIIValidator()
        result = v.validate(
            "Email me at alice@example.com or call 555-123-4567. SSN: 123-45-6789"
        )
        assert result.passed is False
        pii_types = {f.metadata.get("pii_type") for f in result.findings}
        assert "email" in pii_types
        assert "ssn" in pii_types

    def test_disabled_patterns(self):
        v = PIIValidator(config={"pii_patterns_enabled": ["email"]})
        result = v.validate("SSN is 123-45-6789 and phone is 555-123-4567.")
        assert result.passed is True

    def test_severity_is_critical(self):
        v = PIIValidator()
        result = v.validate("My email: test@test.com")
        assert result.findings[0].severity.value == "critical"
