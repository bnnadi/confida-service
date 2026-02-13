"""
Unit tests for HTTPPool.

Tests the HTTP connection pool utility.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.utils.http_pool import HTTPPool, http_pool


class TestHTTPPool:
    """Test cases for HTTPPool."""

    @pytest.mark.unit
    def test_init_creates_session(self):
        """Verify HTTPPool creates a requests Session."""
        with patch("app.utils.http_pool.requests.Session") as mock_session_class:
            pool = HTTPPool()
            mock_session_class.assert_called_once()
            assert pool.session is not None

    @pytest.mark.unit
    def test_get_session_returns_session(self):
        """Verify get_session returns the configured session."""
        with patch("app.utils.http_pool.requests.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session
            pool = HTTPPool()
            result = pool.get_session()
            assert result is mock_session

    @pytest.mark.unit
    def test_close_closes_session(self):
        """Verify close() calls session.close()."""
        with patch("app.utils.http_pool.requests.Session") as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session
            pool = HTTPPool()
            pool.close()
            mock_session.close.assert_called_once()

    @pytest.mark.unit
    def test_global_http_pool_instance(self):
        """Verify global http_pool is an HTTPPool instance."""
        assert isinstance(http_pool, HTTPPool)
