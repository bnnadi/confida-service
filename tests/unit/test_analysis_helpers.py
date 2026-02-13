"""
Unit tests for analysis_helpers.

Tests the shared utilities for analyzing interview answers.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.routers.analysis_helpers import (
    perform_analysis_with_fallback,
    extract_enhanced_score,
)


class TestExtractEnhancedScore:
    """Test cases for extract_enhanced_score."""

    @pytest.mark.unit
    def test_extract_enhanced_score_direct_key(self):
        """Verify extraction when enhanced_rubric is at top level."""
        response = {"enhanced_rubric": {"total": 85, "verbal": 30}}
        result = extract_enhanced_score(response)
        assert result == {"total": 85, "verbal": 30}

    @pytest.mark.unit
    def test_extract_enhanced_score_nested_in_multi_agent(self):
        """Verify extraction when enhanced_rubric is nested in multi_agent_analysis."""
        response = {
            "multi_agent_analysis": {"enhanced_rubric": {"total": 90, "verbal": 35}}
        }
        result = extract_enhanced_score(response)
        assert result == {"total": 90, "verbal": 35}

    @pytest.mark.unit
    def test_extract_enhanced_score_returns_none_when_missing(self):
        """Verify returns None when enhanced_rubric not present."""
        response = {"score": 7, "analysis": "Good"}
        result = extract_enhanced_score(response)
        assert result is None

    @pytest.mark.unit
    def test_extract_enhanced_score_empty_multi_agent(self):
        """Verify returns None when multi_agent_analysis is empty."""
        response = {"multi_agent_analysis": {}}
        result = extract_enhanced_score(response)
        assert result is None


class TestPerformAnalysisWithFallback:
    """Test cases for perform_analysis_with_fallback."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_perform_analysis_success(self):
        """Verify returns AI response when service succeeds."""
        mock_ai = AsyncMock()
        mock_ai.analyze_answer.return_value = {
            "analysis": "Good answer",
            "score": {"clarity": 8, "confidence": 7},
            "suggestions": [],
        }

        request = MagicMock()
        request.jobDescription = "JD"
        request.answer = "My answer"

        result = await perform_analysis_with_fallback(
            mock_ai, request, "What is Python?", "Developer"
        )

        assert result["analysis"] == "Good answer"
        assert result["score"]["clarity"] == 8
        mock_ai.analyze_answer.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_perform_analysis_fallback_when_service_none(self):
        """Verify returns fallback when ai_service is None."""
        request = MagicMock()

        result = await perform_analysis_with_fallback(
            None, request, "Question", "Role"
        )

        assert "Analysis temporarily unavailable" in result["analysis"]
        assert result["score"] == {"clarity": 5, "confidence": 5}
        assert result["suggestions"] == []

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_perform_analysis_fallback_on_exception(self):
        """Verify returns fallback when service raises."""
        mock_ai = AsyncMock()
        mock_ai.analyze_answer.side_effect = Exception("Service error")

        request = MagicMock()
        request.jobDescription = "JD"
        request.answer = "Answer"

        result = await perform_analysis_with_fallback(
            mock_ai, request, "Question", "Role"
        )

        assert "Analysis temporarily unavailable" in result["analysis"]
        assert result["score"] == {"clarity": 5, "confidence": 5}
