"""Tests for the Forbidden Phrase Detector."""

from joshua7.validators.forbidden_phrases import ForbiddenPhraseDetector


class TestForbiddenPhraseDetector:
    def test_clean_text_passes(self):
        v = ForbiddenPhraseDetector()
        result = v.validate("This is perfectly fine content about technology.")
        assert result.passed is True
        assert len(result.findings) == 0

    def test_detects_default_phrase(self):
        v = ForbiddenPhraseDetector()
        result = v.validate("As an AI, I want to help you with this task.")
        assert result.passed is False
        assert len(result.findings) >= 1
        assert any("as an ai" in f.message.lower() for f in result.findings)

    def test_detects_multiple_phrases(self):
        v = ForbiddenPhraseDetector()
        result = v.validate("Let's delve into the synergy of our deep dive.")
        assert result.passed is False
        assert len(result.findings) >= 3

    def test_case_insensitive(self):
        v = ForbiddenPhraseDetector()
        result = v.validate("AS AN AI model, I think we should LEVERAGE this.")
        assert result.passed is False
        assert len(result.findings) >= 2

    def test_custom_phrases(self):
        v = ForbiddenPhraseDetector(config={"forbidden_phrases": ["banana", "coconut"]})
        result = v.validate("I ate a banana and a coconut.")
        assert result.passed is False
        assert len(result.findings) == 2

    def test_span_offsets(self):
        v = ForbiddenPhraseDetector()
        text = "Let's delve into it."
        result = v.validate(text)
        assert result.passed is False
        assert result.findings[0].span is not None
        start, end = result.findings[0].span
        assert text[start:end].lower() == "delve"

    def test_empty_phrase_list(self):
        v = ForbiddenPhraseDetector(config={"forbidden_phrases": []})
        result = v.validate("As an AI, I want to delve into synergy.")
        assert result.passed is True

    def test_unicode_content(self):
        v = ForbiddenPhraseDetector()
        result = v.validate("Héllo wörld! 你好世界 🌍 This is fine.")
        assert result.passed is True

    def test_repeated_phrase(self):
        v = ForbiddenPhraseDetector(config={"forbidden_phrases": ["bad"]})
        result = v.validate("bad bad bad")
        assert result.passed is False
        assert len(result.findings) == 3

    def test_validator_name(self):
        v = ForbiddenPhraseDetector()
        result = v.validate("Test content.")
        assert result.validator_name == "forbidden_phrases"

    def test_severity_is_error(self):
        v = ForbiddenPhraseDetector()
        result = v.validate("Let's delve into it.")
        for f in result.findings:
            assert f.severity.value == "error"

    def test_phrase_in_metadata(self):
        v = ForbiddenPhraseDetector(config={"forbidden_phrases": ["apple"]})
        result = v.validate("I like apple pie.")
        assert result.findings[0].metadata["phrase"] == "apple"

    def test_multiword_phrase(self):
        v = ForbiddenPhraseDetector()
        result = v.validate("At the end of the day we should circle back.")
        phrases = [f.metadata["phrase"] for f in result.findings]
        assert "at the end of the day" in phrases
        assert "circle back" in phrases

    def test_no_partial_match_in_longer_word(self):
        v = ForbiddenPhraseDetector(config={"forbidden_phrases": ["cat"]})
        result = v.validate("The concatenation of strings is great.")
        assert result.passed is False
        assert len(result.findings) >= 1
