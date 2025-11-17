from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.middleware.auth_middleware import get_current_admin
from app.services.tts.base import TTSProviderRateLimitError
from app.routers.speech import get_file_service
from app.exceptions import RateLimitExceededError
from app.models.schemas import FileType


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
        mime_type = "audio/mpeg" if filename.endswith(".mp3") else "audio/wav"
        file_info = {
            "file_id": file_id,
            "mime_type": mime_type,
            "file_size": len(content),
            "metadata": metadata or {},
        }
        self.saved_files[file_id] = file_info
        return file_info

    def get_file_info(self, file_id: str):
        info = self.saved_files.get(file_id)
        if not info:
            return None
        return {
            "file_id": file_id,
            "filename": f"{file_id}.mp3",
            "file_type": FileType.AUDIO,
            "file_size": info["file_size"],
            "mime_type": info["mime_type"],
            "file_path": f"/tmp/{file_id}.mp3",
            "created_at": None,
            "status": None,
        }


@pytest.fixture
def dummy_file_service():
    return DummyFileService()


def test_synthesize_speech_success(client: TestClient, admin_override, dummy_file_service):
    """Admins can synthesize speech and receive stored audio metadata."""
    client.app.dependency_overrides[get_current_admin] = admin_override
    client.app.dependency_overrides[get_file_service] = lambda: dummy_file_service

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
        response = client.post("/api/v1/speech/synthesize", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["voice_id"] == "test-voice"
        assert data["audio_format"] == "mp3"
        assert data["file_id"] == "file-123"
        assert data["download_url"] == "/api/v1/files/file-123/download"
        assert data["mime_type"] == "audio/mpeg"
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
    """Admin endpoint enforces stricter rate limiting."""
    client.app.dependency_overrides[get_current_admin] = admin_override

    limiter_mock = MagicMock()
    limiter_mock.check_rate_limit.side_effect = RateLimitExceededError("limit")

    with patch("app.routers.speech.admin_tts_rate_limiter", limiter_mock):
        response = client.post("/api/v1/speech/synthesize", json={"text": "Hello world"})

        assert response.status_code == 429
        assert "limited to 10 requests per hour" in response.json()["detail"]

    client.app.dependency_overrides.clear()


def test_synthesize_speech_provider_rate_limit(client: TestClient, admin_override, dummy_file_service):
    """TTS provider rate limits are surfaced to admins as HTTP 429 errors."""
    client.app.dependency_overrides[get_current_admin] = admin_override
    client.app.dependency_overrides[get_file_service] = lambda: dummy_file_service

    with patch("app.routers.speech.TTSService") as mock_tts_service, \
        patch("app.routers.speech.VoiceCacheService") as mock_voice_cache:

        mock_voice_cache.return_value.generate_settings_hash.return_value = "hash"
        mock_voice_cache.return_value.get_cached_voice = AsyncMock(return_value=None)

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

