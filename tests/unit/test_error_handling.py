"""
Unit tests for Error Handling Service.

Tests the unified error handling functionality including decorators,
error classification, and circuit breaker pattern.
"""
import pytest
from unittest.mock import patch
from fastapi import HTTPException

from app.utils.error_handling import ErrorHandlingService
from app.exceptions import ConfidaException, ServiceUnavailableError


class TestErrorHandlingService:
    """Test cases for ErrorHandlingService."""

    @pytest.mark.unit
    def test_with_fallback_success(self):
        """Decorated function returns value, assert no fallback."""
        service = ErrorHandlingService()

        @service.with_fallback(fallback_value="fallback")
        def succeed():
            return "success"

        assert succeed() == "success"

    @pytest.mark.unit
    def test_with_fallback_on_exception(self):
        """Decorated function raises, assert returns fallback_value."""
        service = ErrorHandlingService()

        @service.with_fallback(fallback_value="fallback")
        def fail():
            raise ValueError("error")

        assert fail() == "fallback"

    @pytest.mark.unit
    @patch("time.sleep")
    def test_with_retry_success_first_attempt(self, mock_sleep):
        """Function succeeds, assert called once."""
        service = ErrorHandlingService()
        call_count = 0

        @service.with_retry(max_retries=2, delay=0.1, backoff_factor=2.0)
        def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        assert succeed() == "ok"
        assert call_count == 1

    @pytest.mark.unit
    @patch("time.sleep")
    def test_with_retry_eventually_succeeds(self, mock_sleep):
        """Fails twice then succeeds, assert retries and final success."""
        service = ErrorHandlingService()
        call_count = 0

        @service.with_retry(max_retries=3, delay=0.01, backoff_factor=2.0)
        def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("temporary")
            return "ok"

        assert fail_then_succeed() == "ok"
        assert call_count == 3

    @pytest.mark.unit
    @patch("time.sleep")
    def test_with_retry_all_fail(self, mock_sleep):
        """Always raises, assert last_exception re-raised."""
        service = ErrorHandlingService()

        @service.with_retry(max_retries=2, delay=0.01, backoff_factor=2.0)
        def always_fail():
            raise RuntimeError("persistent")

        with pytest.raises(RuntimeError, match="persistent"):
            always_fail()

    @pytest.mark.unit
    def test_with_logging_success(self):
        """Decorated function succeeds, assert no exception."""
        service = ErrorHandlingService()

        @service.with_logging()
        def succeed():
            return 42

        assert succeed() == 42

    @pytest.mark.unit
    def test_with_validation_valid(self):
        """validator_func returns True, assert function called."""
        service = ErrorHandlingService()

        @service.with_validation(validator_func=lambda x: x > 0, error_message="Must be positive")
        def process(n):
            return n * 2

        assert process(5) == 10

    @pytest.mark.unit
    def test_with_validation_invalid(self):
        """Validator returns False, assert ValueError with error_message."""
        service = ErrorHandlingService()

        @service.with_validation(validator_func=lambda x: x > 0, error_message="Must be positive")
        def process(n):
            return n * 2

        with pytest.raises(ValueError, match="Must be positive"):
            process(-1)

    @pytest.mark.unit
    def test_classify_error_transient(self):
        """Error message contains 'timeout', assert returns 'transient'."""
        service = ErrorHandlingService()
        assert service.classify_error(Exception("Connection timeout")) == "transient"
        assert service.classify_error(Exception("network error")) == "transient"

    @pytest.mark.unit
    def test_classify_error_quota_exceeded(self):
        """Message contains '429', assert returns 'quota_exceeded'."""
        service = ErrorHandlingService()
        assert service.classify_error(Exception("429 Too Many Requests")) == "quota_exceeded"

    @pytest.mark.unit
    def test_classify_error_service_unavailable(self):
        """Message contains '503', assert returns 'service_unavailable'."""
        service = ErrorHandlingService()
        assert service.classify_error(Exception("503 Service Unavailable")) == "service_unavailable"

    @pytest.mark.unit
    def test_classify_error_permanent(self):
        """Message contains '401', assert returns 'permanent'."""
        service = ErrorHandlingService()
        assert service.classify_error(Exception("401 Unauthorized")) == "permanent"

    @pytest.mark.unit
    def test_get_fallback_response_question_generation(self):
        """Assert structure has questions, metadata."""
        service = ErrorHandlingService()
        result = service.get_fallback_response(
            "question_generation", Exception("service down")
        )
        assert "questions" in result
        assert "metadata" in result
        assert len(result["questions"]) > 0

    @pytest.mark.unit
    def test_get_fallback_response_answer_analysis(self):
        """Assert structure has analysis, score, suggestions."""
        service = ErrorHandlingService()
        result = service.get_fallback_response(
            "answer_analysis", Exception("service down")
        )
        assert "analysis" in result
        assert "score" in result
        assert "suggestions" in result

    @pytest.mark.unit
    def test_create_circuit_breaker_can_execute_closed(self):
        """New breaker, assert can_execute() is True."""
        service = ErrorHandlingService()
        breaker = service.create_circuit_breaker(failure_threshold=5)
        assert breaker.can_execute() is True

    @pytest.mark.unit
    def test_circuit_breaker_opens_after_threshold(self):
        """record_failure() N times, assert can_execute() becomes False."""
        service = ErrorHandlingService()
        breaker = service.create_circuit_breaker(
            failure_threshold=3, recovery_timeout=60.0
        )
        for _ in range(3):
            breaker.record_failure()
        assert breaker.can_execute() is False

    @pytest.mark.unit
    def test_create_service_error(self):
        """Assert ServiceUnavailableError with context."""
        service = ErrorHandlingService()
        orig = Exception("connection refused")
        error = service.create_service_error("ai", "generate", orig)
        assert isinstance(error, ServiceUnavailableError)
        assert "ai" in str(error)
        assert error.context["service"] == "ai"
        assert error.context["operation"] == "generate"

    @pytest.mark.unit
    def test_create_validation_error(self):
        """Assert ConfidaException with context."""
        service = ErrorHandlingService()
        error = service.create_validation_error("email", "bad", "invalid format")
        assert isinstance(error, ConfidaException)
        assert error.context["field"] == "email"
        assert error.context["value"] == "bad"
        assert error.context["reason"] == "invalid format"

    @pytest.mark.unit
    async def test_with_service_errors_success(self):
        """Async decorated function succeeds, assert no exception."""
        service = ErrorHandlingService()

        @service.with_service_errors(operation_name="test_op")
        async def succeed():
            return "ok"

        assert await succeed() == "ok"

    @pytest.mark.unit
    async def test_with_service_errors_raises_http_exception(self):
        """Async decorated function raises, assert HTTPException 500."""
        service = ErrorHandlingService()

        @service.with_service_errors(operation_name="test_op")
        async def fail():
            raise ValueError("internal")

        with pytest.raises(HTTPException) as exc_info:
            await fail()
        assert exc_info.value.status_code == 500
        assert "test_op" in exc_info.value.detail

    @pytest.mark.unit
    def test_circuit_breaker_record_success_resets(self):
        """After record_failure, record_success resets state."""
        service = ErrorHandlingService()
        breaker = service.create_circuit_breaker(failure_threshold=2)
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.can_execute() is False
        breaker.record_success()
        assert breaker.can_execute() is True
