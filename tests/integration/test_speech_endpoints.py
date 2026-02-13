import base64
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.dependencies import get_tts_service
from app.services.tts.base import TTSProviderRateLimitError


def test_synthesize_speech_success(client: TestClient, override_admin_auth, mock_admin_user):
    """Admins can synthesize speech and receive base64 audio payloads."""
    override_admin_auth(mock_admin_user)

    mock_audio_bytes = b"fake-audio"
    expected_base64 = base64.b64encode(mock_audio_bytes).decode("utf-8")

    mock_instance = MagicMock()
    mock_instance.settings.TTS_DEFAULT_VOICE_ID = "test-voice"
    mock_instance.settings.TTS_DEFAULT_FORMAT = "mp3"
    mock_instance.synthesize = AsyncMock(return_value=mock_audio_bytes)

    app.dependency_overrides[get_tts_service] = lambda: mock_instance

    try:
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
    finally:
        app.dependency_overrides.pop(get_tts_service, None)


def test_synthesize_speech_rate_limit_error(client: TestClient, override_admin_auth, mock_admin_user):
    """TTS provider rate limits are surfaced to admins as HTTP 429 errors."""
    override_admin_auth(mock_admin_user)

    mock_instance = MagicMock()
    mock_instance.synthesize = AsyncMock(
        side_effect=TTSProviderRateLimitError("Rate limit exceeded")
    )

    app.dependency_overrides[get_tts_service] = lambda: mock_instance

    try:
        response = client.post(
            "/api/v1/speech/synthesize",
            json={"text": "Hello world"},
        )

        assert response.status_code == 429
        assert "rate limit exceeded" in response.json()["detail"].lower()

        mock_instance.synthesize.assert_awaited_once()
    finally:
        app.dependency_overrides.pop(get_tts_service, None)


def test_synthesize_speech_requires_admin(client: TestClient):
    """Non-admin (or unauthenticated) callers are rejected."""
    # No authorization header / override -> should fail in get_current_admin
    response = client.post(
        "/api/v1/speech/synthesize",
        json={"text": "Unauthorized access"},
    )

    assert response.status_code == 401

