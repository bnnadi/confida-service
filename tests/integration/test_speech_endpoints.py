import base64
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.middleware.auth_middleware import get_current_admin
from app.services.tts.base import TTSProviderRateLimitError


@pytest.fixture
def admin_override():
    """Provide a reusable admin dependency override."""
    def _override():
        return {
            "id": "admin-user",
            "email": "admin@example.com",
            "role": "admin",
        }

    return _override


def test_synthesize_speech_success(client: TestClient, admin_override):
    """Admins can synthesize speech and receive base64 audio payloads."""
    client.app.dependency_overrides[get_current_admin] = admin_override

    mock_audio_bytes = b"fake-audio"
    expected_base64 = base64.b64encode(mock_audio_bytes).decode("utf-8")

    with patch("app.routers.speech.TTSService") as mock_tts_service:
        mock_instance = mock_tts_service.return_value
        mock_instance.synthesize = AsyncMock(return_value=mock_audio_bytes)

        payload = {
            "text": "Hello world",
            "voice_id": "test-voice",
            "audio_format": "mp3",
            "use_cache": True,
        }
        response = client.post("/api/v1/speech/synthesize", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["audio_data"] == expected_base64
        assert data["voice_id"] == "test-voice"
        assert data["audio_format"] == "mp3"
        assert data["text_length"] == len(payload["text"])
        assert data["cached"] is False
        assert data["metadata"]["audio_size_bytes"] == len(mock_audio_bytes)

        mock_instance.synthesize.assert_awaited_once_with(
            text="Hello world",
            voice_id="test-voice",
            audio_format="mp3",
            use_cache=True,
        )

    client.app.dependency_overrides.clear()


def test_synthesize_speech_rate_limit_error(client: TestClient, admin_override):
    """TTS provider rate limits are surfaced to admins as HTTP 429 errors."""
    client.app.dependency_overrides[get_current_admin] = admin_override

    with patch("app.routers.speech.TTSService") as mock_tts_service:
        mock_instance = mock_tts_service.return_value
        mock_instance.synthesize = AsyncMock(
            side_effect=TTSProviderRateLimitError("Rate limit exceeded")
        )

        response = client.post(
            "/api/v1/speech/synthesize",
            json={"text": "Hello world"},
        )

        assert response.status_code == 429
        assert "rate limit exceeded" in response.json()["detail"].lower()

        mock_instance.synthesize.assert_awaited_once()

    client.app.dependency_overrides.clear()


def test_synthesize_speech_requires_admin(client: TestClient):
    """Non-admin (or unauthenticated) callers are rejected."""
    # No authorization header / override -> should fail in get_current_admin
    response = client.post(
        "/api/v1/speech/synthesize",
        json={"text": "Unauthorized access"},
    )

    assert response.status_code == 401

