"""
Unit tests for AI Service Client.

Tests the HTTP client for AI service microservice communication.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.services.ai_client import AIServiceClient, AIServiceUnavailableError


@pytest.fixture
def mock_httpx_client():
    """Create a mock httpx AsyncClient for AI client tests."""
    with patch("app.services.ai_client.httpx.AsyncClient") as mock_class:
        mock_client = MagicMock()
        mock_client.get = AsyncMock()
        mock_client.post = AsyncMock()
        mock_client.aclose = AsyncMock()
        mock_class.return_value = mock_client
        yield mock_client


class TestAIServiceClient:
    """Test cases for AIServiceClient."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_httpx_client):
        """Mock client.get returns 200, assert True."""
        mock_httpx_client.get.return_value = MagicMock(status_code=200)

        client = AIServiceClient(base_url="http://test-ai:8000")
        result = await client.health_check()

        assert result is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_failure(self, mock_httpx_client):
        """Mock returns 500, assert False."""
        mock_httpx_client.get.return_value = MagicMock(status_code=500)

        client = AIServiceClient(base_url="http://test-ai:8000")
        result = await client.health_check()

        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_check_exception(self, mock_httpx_client):
        """Mock raises Exception, assert False."""
        mock_httpx_client.get.side_effect = Exception("Connection refused")

        client = AIServiceClient(base_url="http://test-ai:8000")
        result = await client.health_check()

        assert result is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_questions_success(self, mock_httpx_client):
        """Mock client.post returns 200 + JSON, assert result matches."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"questions": [{"text": "Q1"}]}
        mock_httpx_client.post.return_value = mock_response

        client = AIServiceClient(base_url="http://test-ai:8000")
        result = await client.generate_questions(
            role="Developer", job_description="Python dev", count=5
        )

        assert result["questions"] == [{"text": "Q1"}]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_questions_non_200(self, mock_httpx_client):
        """Mock returns 500, assert AIServiceUnavailableError."""
        mock_httpx_client.post.return_value = MagicMock(status_code=500)

        client = AIServiceClient(base_url="http://test-ai:8000")
        with pytest.raises(AIServiceUnavailableError, match="Question generation failed"):
            await client.generate_questions(
                role="Developer", job_description="Python dev"
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_questions_structured_success(self, mock_httpx_client):
        """Mock returns questions and identifiers, assert returned dict."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "questions": [{"text": "Q1"}],
            "identifiers": ["id1"],
            "embedding_vectors": {},
        }
        mock_httpx_client.post.return_value = mock_response

        client = AIServiceClient(base_url="http://test-ai:8000")
        result = await client.generate_questions_structured(
            role_name="Developer", job_description="Python dev"
        )

        assert "questions" in result
        assert "identifiers" in result
        assert result["questions"] == [{"text": "Q1"}]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_questions_structured_missing_questions(
        self, mock_httpx_client
    ):
        """Mock returns {}, assert ValueError."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_httpx_client.post.return_value = mock_response

        client = AIServiceClient(base_url="http://test-ai:8000")
        with pytest.raises(ValueError, match="questions"):
            await client.generate_questions_structured(
                role_name="Developer", job_description="Python dev"
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_questions_structured_request_error(self, mock_httpx_client):
        """Mock raises httpx.RequestError, assert AIServiceUnavailableError."""
        mock_httpx_client.post.side_effect = httpx.RequestError("Connection failed")

        client = AIServiceClient(base_url="http://test-ai:8000")
        with pytest.raises(AIServiceUnavailableError, match="AI service unavailable"):
            await client.generate_questions_structured(
                role_name="Developer", job_description="Python dev"
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_answer_success(self, mock_httpx_client):
        """Mock returns 200 + analysis JSON, assert result."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "score": {"overall": 8},
            "analysis": "Good answer",
        }
        mock_httpx_client.post.return_value = mock_response

        client = AIServiceClient(base_url="http://test-ai:8000")
        result = await client.analyze_answer(
            job_description="JD",
            question="Q?",
            answer="A",
        )

        assert result["score"]["overall"] == 8
        assert result["analysis"] == "Good answer"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_analyze_answer_failure(self, mock_httpx_client):
        """Mock returns 500, assert AIServiceUnavailableError."""
        mock_httpx_client.post.return_value = MagicMock(status_code=500)

        client = AIServiceClient(base_url="http://test-ai:8000")
        with pytest.raises(AIServiceUnavailableError, match="Answer analysis failed"):
            await client.analyze_answer(
                job_description="JD", question="Q?", answer="A"
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_transcribe_audio_success(self, mock_httpx_client, tmp_path):
        """Mock client.post with file upload, return 200."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake_audio_data")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "transcribed"}
        mock_httpx_client.post.return_value = mock_response

        client = AIServiceClient(base_url="http://test-ai:8000")
        result = await client.transcribe_audio(
            audio_file_path=str(audio_file),
            session_id="sess-1",
        )

        assert result["text"] == "transcribed"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_transcribe_audio_failure(self, mock_httpx_client, tmp_path):
        """Mock returns 500, assert AIServiceUnavailableError."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake_audio_data")

        mock_httpx_client.post.return_value = MagicMock(status_code=500)

        client = AIServiceClient(base_url="http://test-ai:8000")
        with pytest.raises(AIServiceUnavailableError, match="Transcription failed"):
            await client.transcribe_audio(
                audio_file_path=str(audio_file),
                session_id="sess-1",
            )
