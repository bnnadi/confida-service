"""
Unit tests for ResponseParser and QualityValidator.

Tests the consolidated response parsing functionality.
"""
import pytest

from app.utils.response_parser import ResponseParser, QualityValidator


class TestQualityValidator:
    """Test cases for QualityValidator."""

    @pytest.mark.unit
    def test_validate_question_quality_valid_question(self):
        """Verify valid question passes validation."""
        validator = QualityValidator()
        is_valid, issues = validator.validate_question_quality(
            "What is your experience with Python and FastAPI in production systems?"
        )
        assert is_valid is True
        assert len(issues) == 0

    @pytest.mark.unit
    def test_validate_question_quality_too_short(self):
        """Verify short question fails validation."""
        validator = QualityValidator()
        is_valid, issues = validator.validate_question_quality("Hi")
        assert is_valid is False
        assert len(issues) > 0

    @pytest.mark.unit
    def test_validate_question_quality_ai_failure_pattern(self):
        """Verify AI failure pattern is detected."""
        validator = QualityValidator()
        is_valid, issues = validator.validate_question_quality(
            "I cannot answer that question. I apologize for the inconvenience."
        )
        assert is_valid is False
        assert any("AI failure" in i for i in issues)

    @pytest.mark.unit
    def test_contains_inappropriate_content(self):
        """Verify inappropriate content is detected."""
        assert QualityValidator._contains_inappropriate_content("normal text") is False
        assert QualityValidator._contains_inappropriate_content("violence in content") is True

    @pytest.mark.unit
    def test_detects_ai_failure(self):
        """Verify AI failure patterns are detected."""
        assert QualityValidator._detects_ai_failure("Tell me about Python") is False
        assert QualityValidator._detects_ai_failure("I'm sorry I cannot help") is True


class TestResponseParser:
    """Test cases for ResponseParser."""

    @pytest.fixture
    def parser(self):
        return ResponseParser()

    @pytest.mark.unit
    def test_parse_questions_from_json(self, parser):
        """Verify questions are parsed from JSON response."""
        response = '{"questions": ["Q1?", "Q2?", "Q3?"]}'
        result = parser.parse_questions(response)
        assert result == ["Q1?", "Q2?", "Q3?"]

    @pytest.mark.unit
    def test_parse_questions_from_numbered_list(self, parser):
        """Verify questions are parsed from numbered list."""
        response = "1. First question here?\n2. Second question here?\n3. Third question here?"
        result = parser.parse_questions(response)
        assert len(result) >= 1
        assert "First question here?" in result[0] or "First question here" in result[0]

    @pytest.mark.unit
    def test_parse_questions_fallback_on_invalid_json(self, parser):
        """Verify fallback when JSON is invalid."""
        response = "not valid json at all"
        result = parser.parse_questions(response)
        assert len(result) >= 1
        assert "Tell me about yourself" in result or "challenging project" in str(result).lower()

    @pytest.mark.unit
    def test_parse_analysis_from_json_block(self, parser):
        """Verify analysis is parsed from JSON code block."""
        response = """```json
        {"analysis": "Good answer", "score": {"overall": 8}, "suggestions": ["Add examples"]}
        ```"""
        result = parser.parse_analysis(response)
        assert "analysis" in result or "score" in result
        assert result.get("analysis") == "Good answer" or "Good answer" in str(result)

    @pytest.mark.unit
    def test_parse_analysis_fallback_on_error(self, parser):
        """Verify fallback when parsing fails."""
        response = ""
        result = parser.parse_analysis(response)
        assert "analysis" in result or "score" in result
        assert "Unable to parse" in result.get("analysis", "") or "suggestions" in result
