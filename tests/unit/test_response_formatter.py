"""
Unit tests for ResponseFormatter.

Tests the unified response formatting logic.
"""
import pytest

from app.utils.response_formatter import (
    ResponseFormatter,
    format_success,
    format_error,
    format_pagination,
    format_analysis,
    format_questions,
    format_file,
    format_health,
    format_validation,
    format_service,
    format_fallback,
)


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

    @pytest.mark.unit
    def test_format_analysis_response_with_metadata(self, formatter):
        """Verify analysis response includes metadata when provided."""
        result = formatter.format_analysis_response(
            analysis="Analysis text",
            metadata={"source": "ai", "confidence": 0.9},
        )
        assert result["metadata"] == {"source": "ai", "confidence": 0.9}

    @pytest.mark.unit
    def test_format_question_response(self, formatter):
        """Verify question generation response structure."""
        result = formatter.format_question_response(
            questions=["Q1", "Q2", "Q3"],
            role="Developer",
            job_description="Python dev",
            service_used="database",
            question_bank_count=2,
            ai_generated_count=1,
        )

        assert result["success"] is True
        assert result["questions"] == ["Q1", "Q2", "Q3"]
        assert result["role"] == "Developer"
        assert result["job_description"] == "Python dev"
        assert result["service_used"] == "database"
        assert result["question_counts"]["total"] == 3
        assert result["question_counts"]["from_database"] == 2
        assert result["question_counts"]["ai_generated"] == 1

    @pytest.mark.unit
    def test_format_question_response_with_metadata(self, formatter):
        """Verify question response includes metadata when provided."""
        result = formatter.format_question_response(
            questions=["Q1"],
            role="Dev",
            job_description="JD",
            service_used="ai",
            metadata={"source": "test"},
        )
        assert result["metadata"] == {"source": "test"}

    @pytest.mark.unit
    def test_format_file_response(self, formatter):
        """Verify file operation response structure."""
        result = formatter.format_file_response(
            file_info={"id": "f1", "filename": "doc.pdf", "size": 1024}
        )

        assert result["success"] is True
        assert result["file"] == {"id": "f1", "filename": "doc.pdf", "size": 1024}
        assert "timestamp" in result
        assert result["status_code"] == 200

    @pytest.mark.unit
    def test_format_file_response_custom_message(self, formatter):
        """Verify file response with custom message."""
        result = formatter.format_file_response(
            file_info={"id": "f1"}, message="File uploaded"
        )
        assert result["message"] == "File uploaded"

    @pytest.mark.unit
    def test_format_health_response(self, formatter):
        """Verify health check response structure."""
        result = formatter.format_health_response(
            health_data={"database": "ok", "redis": "ok"}
        )

        assert result["success"] is True
        assert result["health"] == {"database": "ok", "redis": "ok"}
        assert "timestamp" in result

    @pytest.mark.unit
    def test_format_validation_response_valid(self, formatter):
        """Verify validation response when valid."""
        result = formatter.format_validation_response(is_valid=True)

        assert result["success"] is True
        assert result["is_valid"] is True
        assert result["status_code"] == 200

    @pytest.mark.unit
    def test_format_validation_response_invalid_with_errors(self, formatter):
        """Verify validation response with errors."""
        result = formatter.format_validation_response(
            is_valid=False,
            errors=["Field X is required"],
            warnings=["Consider adding Y"],
            data={"partial": "data"},
        )

        assert result["success"] is False
        assert result["is_valid"] is False
        assert result["status_code"] == 400
        assert result["errors"] == ["Field X is required"]
        assert result["warnings"] == ["Consider adding Y"]
        assert result["data"] == {"partial": "data"}

    @pytest.mark.unit
    def test_format_service_response(self, formatter):
        """Verify service operation response structure."""
        result = formatter.format_service_response(
            service_name="TTS",
            operation="synthesize",
            result={"file_id": "abc"},
            execution_time=1.5,
            metadata={"provider": "elevenlabs"},
        )

        assert result["success"] is True
        assert result["service"] == "TTS"
        assert result["operation"] == "synthesize"
        assert result["result"] == {"file_id": "abc"}
        assert result["execution_time"] == 1.5
        assert result["metadata"] == {"provider": "elevenlabs"}

    @pytest.mark.unit
    def test_format_fallback_response(self, formatter):
        """Verify fallback response structure."""
        result = formatter.format_fallback_response(
            operation="synthesize",
            fallback_data={"cached": True},
            reason="Provider timeout",
        )

        assert result["success"] is True
        assert result["fallback"] is True
        assert result["reason"] == "Provider timeout"
        assert result["data"] == {"cached": True}
        assert "Fallback response for synthesize" in result["message"]


class TestResponseFormatterConvenienceFunctions:
    """Test convenience functions that delegate to ResponseFormatter."""

    @pytest.mark.unit
    def test_format_success(self):
        """Verify format_success convenience function."""
        result = format_success(data={"id": 1})
        assert result["success"] is True
        assert result["data"] == {"id": 1}

    @pytest.mark.unit
    def test_format_error(self):
        """Verify format_error convenience function."""
        result = format_error("Error message")
        assert result["success"] is False
        assert result["error"] == "Error message"

    @pytest.mark.unit
    def test_format_pagination(self):
        """Verify format_pagination convenience function."""
        result = format_pagination([1, 2], page=1, page_size=10, total=25)
        assert result["success"] is True
        assert result["pagination"]["page"] == 1
        assert result["pagination"]["total"] == 25

    @pytest.mark.unit
    def test_format_analysis(self):
        """Verify format_analysis convenience function."""
        result = format_analysis("Analysis text", score={"x": 8})
        assert result["success"] is True
        assert result["analysis"] == "Analysis text"
        assert result["score"] == {"x": 8}

    @pytest.mark.unit
    def test_format_questions(self):
        """Verify format_questions convenience function."""
        result = format_questions(
            ["Q1", "Q2"], "Dev", "JD", "database",
            question_bank_count=1, ai_generated_count=1
        )
        assert result["success"] is True
        assert result["questions"] == ["Q1", "Q2"]
        assert result["question_counts"]["from_database"] == 1
        assert result["question_counts"]["ai_generated"] == 1

    @pytest.mark.unit
    def test_format_file(self):
        """Verify format_file convenience function."""
        result = format_file({"id": "f1", "name": "test.pdf"})
        assert result["success"] is True
        assert result["file"] == {"id": "f1", "name": "test.pdf"}

    @pytest.mark.unit
    def test_format_health(self):
        """Verify format_health convenience function."""
        result = format_health({"db": "ok"})
        assert result["success"] is True
        assert result["health"] == {"db": "ok"}

    @pytest.mark.unit
    def test_format_validation(self):
        """Verify format_validation convenience function."""
        result = format_validation(True, errors=[], warnings=[])
        assert result["success"] is True
        assert result["is_valid"] is True

    @pytest.mark.unit
    def test_format_service(self):
        """Verify format_service convenience function."""
        result = format_service("Cache", "clear", {"cleared": True})
        assert result["success"] is True
        assert result["service"] == "Cache"
        assert result["operation"] == "clear"

    @pytest.mark.unit
    def test_format_fallback(self):
        """Verify format_fallback convenience function."""
        result = format_fallback("synthesize", {"fallback": "data"})
        assert result["success"] is True
        assert result["fallback"] is True
        assert result["data"] == {"fallback": "data"}
