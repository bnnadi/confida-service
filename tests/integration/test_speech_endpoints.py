from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from app.middleware.auth_middleware import get_current_admin
from app.services.tts.base import TTSProviderRateLimitError
from app.routers.speech import get_file_service
from app.exceptions import RateLimitExceededError


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


class DummyFileService:
    """Simple in-memory file service replacement for tests."""

    def __init__(self):
        self.saved_files = {}

    def save_file_from_bytes(self, content, file_type, file_id, filename, metadata=None):
        file_info = {
            "file_id": file_id,
            "mime_type": "audio/mpeg" if filename.endswith(".mp3") else "audio/wav",
            "file_size": len(content),
            "metadata": metadata or {},
        }
        self.saved_files[file_id] = file_info
        return file_info


@pytest.fixture
def dummy_file_service():
    return DummyFileService()


@pytest.fixture
def admin_client(client: TestClient, admin_override):
    """Client fixture with admin override applied."""
    overrides = client.app.dependency_overrides
    previous = dict(overrides)
    overrides[get_current_admin] = admin_override
    try:
        yield client
    finally:
        overrides.clear()
        overrides.update(previous)


@pytest.fixture
def speech_admin_client(admin_client: TestClient, dummy_file_service):
    """Admin client fixture that also swaps in the dummy file service."""
    overrides = admin_client.app.dependency_overrides
    overrides[get_file_service] = lambda: dummy_file_service
    try:
        yield admin_client
    finally:
        overrides.pop(get_file_service, None)


def test_synthesize_speech_success(speech_admin_client: TestClient):
    """Admins can synthesize speech and receive stored audio metadata."""
    mock_audio_bytes = b"fake-audio"

    with patch("app.routers.speech.TTSService") as mock_tts_service, \
        patch("app.routers.speech.VoiceCacheService") as mock_voice_cache, \
        patch("app.routers.speech.FileService.generate_file_id", return_value="file-123"), \
        patch("app.routers.speech.cache_voice_result", new_callable=AsyncMock):

        mock_instance = mock_tts_service.return_value
        mock_instance.synthesize = AsyncMock(return_value=mock_audio_bytes)

        mock_voice_cache_instance = mock_voice_cache.return_value
        mock_voice_cache_instance.generate_settings_hash.return_value = "hash"
        mock_voice_cache_instance.get_cached_voice = AsyncMock(return_value=None)

        payload = {
            "text": "Hello world",
            "voice_id": "test-voice",
            "audio_format": "mp3",
            "use_cache": True,
        }
        response = speech_admin_client.post("/api/v1/speech/synthesize", json=payload)

        assert response.status_code == 200
        data = response.json()

        expected_fields = {
            "voice_id": payload["voice_id"],
            "audio_format": payload["audio_format"],
            "file_id": "file-123",
            "download_url": "/api/v1/files/file-123/download",
            "mime_type": "audio/mpeg",
            "text_length": len(payload["text"]),
            "cached": False,
        }
        for key, expected in expected_fields.items():
            assert data[key] == expected

        metadata = data["metadata"]
        assert metadata["audio_size_bytes"] == len(mock_audio_bytes)

        mock_instance.synthesize.assert_awaited_once_with(
            text="Hello world",
            voice_id="test-voice",
            audio_format="mp3",
            use_cache=True,
        )


def test_synthesize_speech_rate_limit_error(admin_client: TestClient):
    """Admin endpoint enforces stricter rate limiting."""
    limiter_mock = MagicMock()
    limiter_mock.check_rate_limit.side_effect = RateLimitExceededError("limit")

    with patch("app.routers.speech.admin_tts_rate_limiter", limiter_mock):
        response = admin_client.post("/api/v1/speech/synthesize", json={"text": "Hello world"})

        assert response.status_code == 429
        assert "limited to 10 requests per hour" in response.json()["detail"]


def test_synthesize_speech_provider_rate_limit(speech_admin_client: TestClient):
    """TTS provider rate limits are surfaced to admins as HTTP 429 errors."""
    with patch("app.routers.speech.TTSService") as mock_tts_service, \
        patch("app.routers.speech.VoiceCacheService") as mock_voice_cache:

        mock_voice_cache.return_value.generate_settings_hash.return_value = "hash"
        mock_voice_cache.return_value.get_cached_voice = AsyncMock(return_value=None)

        mock_instance = mock_tts_service.return_value
        mock_instance.synthesize = AsyncMock(
            side_effect=TTSProviderRateLimitError("Rate limit exceeded")
        )

        response = speech_admin_client.post(
            "/api/v1/speech/synthesize",
            json={"text": "Hello world"},
        )

        assert response.status_code == 429
        assert "rate limit exceeded" in response.json()["detail"].lower()

        mock_instance.synthesize.assert_awaited_once()

def test_synthesize_speech_requires_admin(client: TestClient):
    """Non-admin (or unauthenticated) callers are rejected."""
    # No authorization header / override -> should fail in get_current_admin
    response = client.post(
        "/api/v1/speech/synthesize",
        json={"text": "Unauthorized access"},
    )

    assert response.status_code == 401

