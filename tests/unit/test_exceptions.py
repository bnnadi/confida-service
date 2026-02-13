"""
Unit tests for custom exceptions.
"""
import pytest

from app.exceptions import (
    ConfidaException,
    AIServiceError,
    ServiceUnavailableError,
    InvalidResponseError,
    RateLimitExceededError,
    ConfigurationError,
    AdminError,
    ServiceNotInitializedError,
    ConfigurationRetrievalError,
    StatisticsRetrievalError,
)


class TestConfidaException:
    """Test cases for ConfidaException."""

    @pytest.mark.unit
    def test_confida_exception_with_context(self):
        """Test ConfidaException stores context when provided."""
        exc = ConfidaException("Error message", context={"key": "value"})
        assert str(exc) == "Error message"
        assert exc.context == {"key": "value"}

    @pytest.mark.unit
    def test_confida_exception_default_context(self):
        """Test ConfidaException has empty dict when context not provided."""
        exc = ConfidaException("Error")
        assert exc.context == {}


class TestExceptionHierarchy:
    """Test exception inheritance."""

    @pytest.mark.unit
    def test_ai_service_error_inherits_confida(self):
        """Test AIServiceError is a ConfidaException."""
        exc = AIServiceError("AI failed")
        assert isinstance(exc, ConfidaException)

    @pytest.mark.unit
    def test_service_unavailable_inherits_ai_service_error(self):
        """Test ServiceUnavailableError is an AIServiceError."""
        exc = ServiceUnavailableError("Service down")
        assert isinstance(exc, AIServiceError)

    @pytest.mark.unit
    def test_admin_error_inherits_confida(self):
        """Test AdminError is a ConfidaException."""
        exc = AdminError("Admin error")
        assert isinstance(exc, ConfidaException)

    @pytest.mark.unit
    def test_service_not_initialized_inherits_admin_error(self):
        """Test ServiceNotInitializedError is an AdminError."""
        exc = ServiceNotInitializedError("Not init")
        assert isinstance(exc, AdminError)
