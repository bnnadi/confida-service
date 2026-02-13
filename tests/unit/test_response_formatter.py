"""
Unit tests for ResponseFormatter.

Tests the unified response formatting logic.
"""
import pytest

from app.utils.response_formatter import ResponseFormatter


class TestResponseFormatter:
    """Test cases for ResponseFormatter."""

    @pytest.fixture
    def formatter(self):
        return ResponseFormatter()

    @pytest.mark.unit
    def test_format_success_response_basic(self, formatter):
        """Verify basic success response structure."""
        result = formatter.format_success_response()

        assert result["success"] is True
        assert result["message"] == "Success"
        assert "timestamp" in result
        assert result["status_code"] == 200

    @pytest.mark.unit
    def test_format_success_response_with_data(self, formatter):
        """Verify success response includes data when provided."""
        result = formatter.format_success_response(data={"id": "123", "name": "test"})

        assert result["data"] == {"id": "123", "name": "test"}

    @pytest.mark.unit
    def test_format_success_response_with_metadata(self, formatter):
        """Verify success response includes metadata when provided."""
        result = formatter.format_success_response(
            data=[], metadata={"count": 5, "filter": "active"}
        )

        assert result["metadata"] == {"count": 5, "filter": "active"}

    @pytest.mark.unit
    def test_format_error_response_string(self, formatter):
        """Verify error response with string error."""
        result = formatter.format_error_response("Something went wrong")

        assert result["success"] is False
        assert result["error"] == "Something went wrong"
        assert result["status_code"] == 400

    @pytest.mark.unit
    def test_format_error_response_exception(self, formatter):
        """Verify error response with Exception."""
        result = formatter.format_error_response(ValueError("Invalid input"))

        assert result["success"] is False
        assert "Invalid input" in result["error"]

    @pytest.mark.unit
    def test_format_error_response_with_details(self, formatter):
        """Verify error response includes details when provided."""
        result = formatter.format_error_response(
            "Validation failed", details={"field": "email", "reason": "invalid"}
        )

        assert result["details"] == {"field": "email", "reason": "invalid"}

    @pytest.mark.unit
    def test_format_pagination_response(self, formatter):
        """Verify pagination response structure."""
        result = formatter.format_pagination_response(
            data=[{"id": 1}, {"id": 2}],
            page=1,
            page_size=10,
            total=25,
        )

        assert result["success"] is True
        assert result["data"] == [{"id": 1}, {"id": 2}]
        assert result["pagination"]["page"] == 1
        assert result["pagination"]["page_size"] == 10
        assert result["pagination"]["total"] == 25
        assert result["pagination"]["total_pages"] == 3
        assert result["pagination"]["has_next"] is True
        assert result["pagination"]["has_prev"] is False

    @pytest.mark.unit
    def test_format_analysis_response(self, formatter):
        """Verify analysis response structure."""
        result = formatter.format_analysis_response(
            analysis="Good answer with clear examples",
            score={"clarity": 8, "confidence": 7},
            suggestions=["Add more metrics"],
        )

        assert result["success"] is True
        assert "analysis" in result
        assert result.get("score") == {"clarity": 8, "confidence": 7}
        assert "suggestions" in result
