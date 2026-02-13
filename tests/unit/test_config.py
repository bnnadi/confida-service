"""
Unit tests for application configuration.

Tests config loading and rate limit configuration.
"""
import pytest
from unittest.mock import patch

from app.config import get_settings


class TestConfig:
    """Test cases for application config."""

    @pytest.mark.unit
    def test_get_settings_returns_settings(self):
        """Test get_settings returns Settings instance."""
        settings = get_settings()
        assert settings is not None
        assert hasattr(settings, "DATABASE_URL")
        assert hasattr(settings, "CACHE_ENABLED")

    @pytest.mark.unit
    def test_rate_limit_per_endpoint(self):
        """Test rate_limit_per_endpoint property returns dict."""
        settings = get_settings()
        limits = settings.rate_limit_per_endpoint
        assert isinstance(limits, dict)
        assert "/api/v1/parse-jd" in limits
        assert "requests" in limits["/api/v1/parse-jd"]
        assert "window" in limits["/api/v1/parse-jd"]

    @pytest.mark.unit
    def test_get_rate_limit_for_endpoint(self):
        """Test get_rate_limit_for_endpoint returns config for known endpoint."""
        settings = get_settings()
        limit = settings.get_rate_limit_for_endpoint("/api/v1/parse-jd")
        assert "requests" in limit
        assert "window" in limit

    @pytest.mark.unit
    def test_get_rate_limit_for_unknown_endpoint_uses_default(self):
        """Test get_rate_limit_for_endpoint returns default for unknown endpoint."""
        settings = get_settings()
        limit = settings.get_rate_limit_for_endpoint("/unknown/endpoint")
        assert limit["requests"] == settings.RATE_LIMIT_DEFAULT_REQUESTS
        assert limit["window"] == settings.RATE_LIMIT_DEFAULT_WINDOW

    @pytest.mark.unit
    def test_rate_limit_per_user_type(self):
        """Test rate_limit_per_user_type property returns dict."""
        settings = get_settings()
        limits = settings.rate_limit_per_user_type
        assert "free" in limits
        assert "premium" in limits
        assert "enterprise" in limits

    @pytest.mark.unit
    def test_get_rate_limit_for_user_type(self):
        """Test get_rate_limit_for_user_type returns config for known type."""
        settings = get_settings()
        limit = settings.get_rate_limit_for_user_type("free")
        assert "requests" in limit
        assert "window" in limit

    @pytest.mark.unit
    def test_get_rate_limit_for_unknown_user_type_uses_default(self):
        """Test get_rate_limit_for_user_type returns default for unknown type."""
        settings = get_settings()
        limit = settings.get_rate_limit_for_user_type("unknown_type")
        assert limit["requests"] == settings.RATE_LIMIT_DEFAULT_REQUESTS
        assert limit["window"] == settings.RATE_LIMIT_DEFAULT_WINDOW

    @pytest.mark.unit
    def test_configured_services(self):
        """Test configured_services property."""
        settings = get_settings()
        services = settings.configured_services
        assert isinstance(services, dict)
        assert "ai_service_microservice" in services

    @pytest.mark.unit
    def test_is_service_configured(self):
        """Test is_service_configured returns bool."""
        settings = get_settings()
        result = settings.is_service_configured("ai_service_microservice")
        assert isinstance(result, bool)

    @pytest.mark.unit
    def test_rate_limit_all_endpoints(self):
        """Test all rate limit endpoints return valid config."""
        settings = get_settings()
        limits = settings.rate_limit_per_endpoint
        for endpoint, config in limits.items():
            assert "requests" in config
            assert "window" in config
            assert config["requests"] > 0
            assert config["window"] > 0

    @pytest.mark.unit
    def test_rate_limit_all_user_types(self):
        """Test all user type rate limits return valid config."""
        settings = get_settings()
        limits = settings.rate_limit_per_user_type
        for user_type, config in limits.items():
            assert "requests" in config
            assert "window" in config
