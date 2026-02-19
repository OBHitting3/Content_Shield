"""Tests for the Toxicity Detector."""

from joshua7.validators.toxicity import ToxicityDetector


class TestToxicityDetector:
    def test_clean_text_passes(self):
        v = ToxicityDetector()
        result = v.validate("This is a wonderful day for everyone involved.")
        assert result.passed is True
        assert len(result.findings) == 0

    def test_detects_death_threat(self):
        v = ToxicityDetector()
        result = v.validate("I will kill you if you don't stop.")
        assert result.passed is False
        assert any(f.metadata.get("category") == "threat" for f in result.findings)

    def test_detects_violence_intent(self):
        v = ToxicityDetector()
        result = v.validate("I am going to hurt someone tonight.")
        assert result.passed is False
        assert any("threat" in f.metadata.get("category", "") for f in result.findings)

    def test_detects_harassment(self):
        v = ToxicityDetector()
        result = v.validate("You're worthless and nobody cares about you.")
        assert result.passed is False
        assert any(f.metadata.get("category") == "harassment" for f in result.findings)

    def test_detects_profanity(self):
        v = ToxicityDetector()
        result = v.validate("This is absolute shit and I hate it.")
        assert result.passed is False
        assert any(f.metadata.get("category") == "profanity" for f in result.findings)

    def test_detects_self_harm_encouragement(self):
        v = ToxicityDetector()
        result = v.validate("You should just kill yourself already.")
        assert result.passed is False
        assert any(f.metadata.get("category") == "self_harm" for f in result.findings)

    def test_detects_discrimination(self):
        v = ToxicityDetector()
        result = v.validate("White supremacy is the only answer for our nation.")
        assert result.passed is False
        assert any(f.metadata.get("category") == "discrimination" for f in result.findings)

    def test_severity_critical_for_threats(self):
        v = ToxicityDetector()
        result = v.validate("I will murder you in your sleep.")
        assert any(f.severity.value == "critical" for f in result.findings)

    def test_severity_warning_for_profanity(self):
        v = ToxicityDetector()
        result = v.validate("What the fuck is going on here.")
        profanity_findings = [
            f for f in result.findings if f.metadata.get("category") == "profanity"
        ]
        assert len(profanity_findings) > 0
        assert profanity_findings[0].severity.value == "warning"

    def test_critical_findings_always_fail(self):
        v = ToxicityDetector(config={"toxicity_threshold": 1.0})
        result = v.validate("I will kill you tomorrow.")
        assert result.passed is False

    def test_disabled_categories(self):
        v = ToxicityDetector(config={"toxicity_categories_enabled": ["profanity"]})
        result = v.validate("I will kill you if you don't stop.")
        assert result.passed is True

    def test_multiple_categories(self):
        v = ToxicityDetector()
        result = v.validate(
            "You're stupid and I will kill you. What the fuck."
        )
        categories = {f.metadata.get("category") for f in result.findings}
        assert len(categories) >= 2

    def test_score_reflects_toxicity(self):
        v = ToxicityDetector()
        clean = v.validate("A lovely day with friends and family.")
        toxic = v.validate("I will kill you and destroy everything you love.")
        assert clean.score is not None and toxic.score is not None
        assert clean.score > toxic.score

    def test_score_bounded(self):
        v = ToxicityDetector()
        result = v.validate("Test content for score bounds.")
        assert result.score is not None
        assert 0.0 <= result.score <= 100.0

    def test_validator_name(self):
        v = ToxicityDetector()
        result = v.validate("Test.")
        assert result.validator_name == "toxicity"

    def test_span_offsets(self):
        v = ToxicityDetector()
        text = "This is absolute shit here."
        result = v.validate(text)
        if result.findings:
            assert result.findings[0].span is not None
            start, end = result.findings[0].span
            assert start >= 0
            assert end <= len(text)

    def test_stalking_language(self):
        v = ToxicityDetector()
        result = v.validate("I know where you live and I am coming for you.")
        assert result.passed is False
        assert any(
            "stalking_language" in f.metadata.get("pattern", "")
            for f in result.findings
        )

    def test_bomb_threat(self):
        v = ToxicityDetector()
        result = v.validate("I am going to blow up the building tonight.")
        assert result.passed is False
        assert any(
            "bomb_threat" in f.metadata.get("pattern", "")
            for f in result.findings
        )

    def test_clean_text_score_100(self):
        v = ToxicityDetector()
        result = v.validate("Our team is dedicated to excellence and quality.")
        assert result.score == 100.0

    def test_custom_threshold(self):
        v = ToxicityDetector(config={"toxicity_threshold": 0.01})
        result = v.validate("This is some shit.")
        assert result.passed is False
