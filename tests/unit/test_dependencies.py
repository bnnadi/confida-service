"""
Unit tests for dependency injection utilities.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.dependencies import (
    get_validation_service,
    get_database_dependency,
    get_file_service,
    get_dashboard_service,
    get_analytics_service,
    get_ai_client_dependency,
)


class TestDependencies:
    """Test cases for dependency injection."""

    @pytest.mark.unit
    def test_get_validation_service_returns_validation_service(self):
        """Test get_validation_service returns ValidationService instance."""
        from app.utils.validation import ValidationService

        result = get_validation_service()
        assert isinstance(result, ValidationService)

    @pytest.mark.unit
    def test_get_database_dependency_sync_when_async_disabled(self):
        """Test get_database_dependency returns sync when ASYNC_DATABASE_ENABLED is False."""
        with patch("app.dependencies.settings") as mock_settings:
            mock_settings.ASYNC_DATABASE_ENABLED = False
            from app.dependencies import get_database_session, get_database_dependency

            result = get_database_dependency()
            assert result == get_database_session

    @pytest.mark.unit
    def test_get_database_dependency_async_when_enabled(self):
        """Test get_database_dependency returns async when ASYNC_DATABASE_ENABLED is True."""
        with patch("app.dependencies.settings") as mock_settings:
            mock_settings.ASYNC_DATABASE_ENABLED = True
            from app.dependencies import get_async_database_session, get_database_dependency

            result = get_database_dependency()
            assert result == get_async_database_session

    @pytest.mark.unit
    def test_get_file_service_returns_file_service(self, db_session):
        """Test get_file_service returns FileService instance."""
        from app.services.file_service import FileService

        result = get_file_service(db_session)
        assert isinstance(result, FileService)

    @pytest.mark.unit
    def test_get_dashboard_service_returns_dashboard_service(self, db_session):
        """Test get_dashboard_service returns DashboardService instance."""
        from app.services.dashboard_service import DashboardService

        result = get_dashboard_service(db_session)
        assert isinstance(result, DashboardService)

    @pytest.mark.unit
    def test_get_analytics_service_returns_analytics_service(self, db_session):
        """Test get_analytics_service returns AnalyticsService instance."""
        from app.services.analytics_service import AnalyticsService

        result = get_analytics_service(db_session)
        assert isinstance(result, AnalyticsService)

    @pytest.mark.unit
    def test_get_ai_client_dependency_returns_none_on_error(self):
        """Test get_ai_client_dependency returns None when get_ai_client raises."""
        with patch("app.dependencies.get_ai_client", side_effect=Exception("Init failed")):
            result = get_ai_client_dependency()
            assert result is None

    @pytest.mark.unit
    def test_get_ai_client_dependency_returns_client_on_success(self):
        """Test get_ai_client_dependency returns client when get_ai_client succeeds."""
        mock_client = MagicMock()
        with patch("app.dependencies.get_ai_client", return_value=mock_client):
            result = get_ai_client_dependency()
            assert result is mock_client

    @pytest.mark.unit
    def test_get_database_session_returns_depends(self):
        """Test get_database_session returns Depends object."""
        from app.dependencies import get_database_session

        result = get_database_session()
        assert result is not None
        assert hasattr(result, "dependency")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_async_database_session_yields_session(self):
        """Test get_async_database_session is an async generator that yields sessions."""
        from app.dependencies import get_async_database_session

        session_count = 0
        async for session in get_async_database_session():
            session_count += 1
            assert session is not None
            break  # Only need one to verify it works
        assert session_count >= 1
