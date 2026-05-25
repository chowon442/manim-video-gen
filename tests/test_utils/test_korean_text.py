"""Tests for korean_text utilities."""

from __future__ import annotations

import pytest

from manim_video_gen.utils.korean_text import (
    extract_content_tokens,
    payoff_references_application,
)


class TestExtractContentTokens:
    """Tests for extract_content_tokens()."""

    def test_empty_string(self):
        assert extract_content_tokens("") == set()

    def test_english_tokens(self):
        tokens = extract_content_tokens("p-value is significant")
        assert "p-value" in tokens
        assert "significant" in tokens

    def test_korean_particles_stripped(self):
        tokens = extract_content_tokens("기울기로 추세를 판단할 수 있어요")
        # "기울기로" → "기울기", "추세를" → "추세"
        assert "기울기" in tokens
        assert "추세" in tokens

    def test_mixed_korean_english(self):
        tokens = extract_content_tokens("p-value가 0.014로 유의미합니다")
        assert "p-value" in tokens
        assert "0.014" in tokens
        assert "유의미합니다" in tokens

    def test_number_with_parentheses_normalized(self):
        tokens = extract_content_tokens("0.014(1.4%)로 유의미합니다")
        # Should extract "0.014" from "0.014(1.4%)로"
        assert "0.014" in tokens

    def test_percentage_number_normalized(self):
        tokens = extract_content_tokens("50% 증가했습니다")
        assert "50" in tokens

    def test_short_tokens_filtered(self):
        tokens = extract_content_tokens("나는 학생입니다")
        # "나" and "는" are too short after particle strip
        assert "학생입니다" in tokens

    def test_complex_particles(self):
        tokens = extract_content_tokens("함수에서 기울기으로 변화율을")
        assert "함수" in tokens
        assert "기울기" in tokens
        assert "변화율" in tokens


class TestPayoffReferencesApplication:
    """Tests for payoff_references_application()."""

    def test_korean_number_variant_pass(self):
        """p-value가 0.014(1.4%)로 → p-value 0.014로 should pass."""
        app = "p-value가 0.014(1.4%)로 유의미합니다"
        payoff = "p-value 0.014로 유의미해요"
        assert payoff_references_application(app, payoff) is True

    def test_korean_semantic_connection_pass(self):
        """Same content words with different particles should pass."""
        app = "기울기로 추세를 판단할 수 있어요"
        payoff = "기울기로 추세를 읽는 거예요"
        assert payoff_references_application(app, payoff) is True

    def test_unrelated_korean_fail(self):
        """Completely unrelated topics should fail."""
        app = "기울기로 추세를 판단할 수 있어요"
        payoff = "오늘 날씨가 좋네요"
        assert payoff_references_application(app, payoff) is False

    def test_english_overlap_pass(self):
        """English with shared tokens should pass."""
        app = "The correlation coefficient is 0.95"
        payoff = "correlation coefficient of 0.95 shows strong relationship"
        assert payoff_references_application(app, payoff) is True

    def test_english_no_overlap_fail(self):
        """English with no shared tokens should fail."""
        app = "The correlation coefficient is 0.95"
        payoff = "Today is a beautiful day"
        assert payoff_references_application(app, payoff) is False

    def test_empty_app_result_fail(self):
        """Empty application_result should fail."""
        assert payoff_references_application("", "some payoff") is False

    def test_empty_payoff_fail(self):
        """Empty payoff_line should fail."""
        assert payoff_references_application("some result", "") is False

    def test_both_empty_fail(self):
        """Both empty should fail."""
        assert payoff_references_application("", "") is False

    def test_substring_fallback_pass(self):
        """Token appearing as substring in raw text should pass."""
        app = "통계적 유의성"
        payoff = "이 결과는 통계적으로 유의미합니다"
        assert payoff_references_application(app, payoff) is True

    def test_korean_with_english_concept_pass(self):
        """Korean text with English concept name should pass."""
        app = "p-value가 0.05보다 작으면 유의미합니다"
        payoff = "p-value 0.03으로 유의미한 결과예요"
        assert payoff_references_application(app, payoff) is True

    def test_single_shared_token_pass(self):
        """Even one shared meaningful token should pass."""
        app = "기울기를 계산합니다"
        payoff = "이 기울기는 의미가 있어요"
        assert payoff_references_application(app, payoff) is True
