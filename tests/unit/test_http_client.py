"""
Unit tests for HTTPClient.

Tests the async HTTP client utility.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.utils.http_client import HTTPClient


class TestHTTPClient:
    """Test cases for HTTPClient."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_makes_request(self):
        """Verify get() makes async GET request."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("app.utils.http_client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            client = HTTPClient()
            result = await client.get("https://example.com")

            assert result.status_code == 200
            mock_client.get.assert_called_once_with("https://example.com")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_post_makes_request(self):
        """Verify post() makes async POST request."""
        mock_response = MagicMock()
        mock_response.status_code = 201

        with patch("app.utils.http_client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            client = HTTPClient()
            result = await client.post("https://example.com", json={"key": "value"})

            assert result.status_code == 201
            mock_client.post.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_returns_true_on_200(self):
        """Verify health_check returns True when status is 200."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("app.utils.http_client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            client = HTTPClient()
            result = await client.health_check("https://example.com/health")

            assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_non_200(self):
        """Verify health_check returns False when status is not 200."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch("app.utils.http_client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            client = HTTPClient()
            result = await client.health_check("https://example.com/health")

            assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_returns_false_on_exception(self):
        """Verify health_check returns False when request raises."""
        with patch("app.utils.http_client.httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.aclose = AsyncMock()
            mock_client_class.return_value = mock_client

            client = HTTPClient()
            result = await client.health_check("https://example.com/health")

            assert result is False
