"""
Unit tests for FallbackResponses.

Tests the centralized fallback responses used when AI services fail.
"""
import pytest

from app.utils.fallback_responses import FallbackResponses


class TestFallbackResponses:
    """Test cases for FallbackResponses."""

    @pytest.mark.unit
    def test_get_fallback_questions_returns_parse_jd_response(self):
        """Verify get_fallback_questions returns ParseJDResponse with questions."""
        result = FallbackResponses.get_fallback_questions(role="Software Engineer")

        assert result.questions is not None
        assert len(result.questions) == 10

    @pytest.mark.unit
    def test_get_fallback_questions_includes_role_in_first_question(self):
        """Verify first question includes the role."""
        result = FallbackResponses.get_fallback_questions(role="Backend Developer")

        assert "Backend Developer" in result.questions[0]
        assert "Tell me about your experience with Backend Developer" == result.questions[0]

    @pytest.mark.unit
    def test_get_fallback_questions_contains_expected_questions(self):
        """Verify fallback questions contain expected content."""
        result = FallbackResponses.get_fallback_questions(role="DevOps")

        assert any("challenging project" in q.lower() for q in result.questions)
        assert any("problem-solving" in q.lower() for q in result.questions)
        assert any("code review" in q.lower() for q in result.questions)
