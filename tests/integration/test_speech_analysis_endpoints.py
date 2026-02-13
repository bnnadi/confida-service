"""
Integration tests for Speech Analysis API endpoints (INT-48).

Tests /api/v1/speech/analyze and /api/v1/speech/analyze/batch with authentication.
"""
import pytest
import uuid

from app.database.models import User
from app.services.auth_service import AuthService
from tests.conftest import make_auth_user


@pytest.fixture
def speech_user(db_session):
    """Create a user for speech analysis tests."""
    auth_service = AuthService(db_session)
    user = User(
        email=f"speech-{uuid.uuid4().hex[:8]}@example.com",
        name="Speech User",
        password_hash=auth_service.get_password_hash("testpass123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.mark.integration
def test_analyze_requires_auth(client):
    """Test POST /speech/analyze returns 401 when unauthenticated."""
    response = client.post(
        "/api/v1/speech/analyze",
        json={"transcript": "This is a test transcript."},
    )
    assert response.status_code == 401


@pytest.mark.integration
def test_analyze_success(client, speech_user, override_auth):
    """Test POST /speech/analyze returns analysis when authenticated."""
    override_auth(make_auth_user(speech_user))
    response = client.post(
        "/api/v1/speech/analyze",
        json={"transcript": "This is a clear test transcript without fillers."},
    )

    assert response.status_code == 200
    data = response.json()
    assert "filler_words" in data
    assert "pace" in data
    assert "clarity" in data
    assert "confidence" in data
    assert "suggestions" in data
    assert data["filler_words"] >= 0
    assert data["pace"] >= 0
    assert 0.0 <= data["clarity"] <= 1.0
    assert 0.0 <= data["confidence"] <= 1.0
    assert isinstance(data["suggestions"], list)


@pytest.mark.integration
def test_analyze_with_duration(client, speech_user, override_auth):
    """Test POST /speech/analyze with duration_seconds for accurate WPM."""
    override_auth(make_auth_user(speech_user))
    transcript = "One two three four five six seven eight nine ten."
    response = client.post(
        "/api/v1/speech/analyze",
        json={
            "transcript": transcript,
            "duration_seconds": 5.0,
        },
    )

    assert response.status_code == 200
    data = response.json()
    # 10 words in 5 seconds = 120 WPM
    assert data["pace"] == 120.0


@pytest.mark.integration
def test_analyze_with_filler_words(client, speech_user, override_auth):
    """Test POST /speech/analyze detects filler words."""
    override_auth(make_auth_user(speech_user))
    response = client.post(
        "/api/v1/speech/analyze",
        json={
            "transcript": "Um, so I think that, you know, the main point is, like, really important.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["filler_words"] > 0
    assert data["clarity"] < 1.0
    assert any("filler" in s.lower() for s in data["suggestions"]) or data["filler_words"] <= 5


@pytest.mark.integration
def test_analyze_batch_requires_auth(client):
    """Test POST /speech/analyze/batch returns 401 when unauthenticated."""
    response = client.post(
        "/api/v1/speech/analyze/batch",
        json={
            "transcripts": [
                {"text": "First transcript."},
                {"text": "Second transcript."},
            ],
        },
    )
    assert response.status_code == 401


@pytest.mark.integration
def test_analyze_batch_success(client, speech_user, override_auth):
    """Test POST /speech/analyze/batch returns results for each transcript."""
    override_auth(make_auth_user(speech_user))
    response = client.post(
        "/api/v1/speech/analyze/batch",
        json={
            "transcripts": [
                {"text": "First clear transcript."},
                {"text": "Second transcript with um filler.", "duration_seconds": 3.0},
            ],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 2
    for result in data["results"]:
        assert "filler_words" in result
        assert "pace" in result
        assert "clarity" in result
        assert "confidence" in result
        assert "suggestions" in result
    # Second has "um" and duration - check pace is calculated (5 words in 3 sec = 100 WPM)
    assert data["results"][1]["pace"] == 100.0


@pytest.mark.integration
def test_analyze_empty_transcript_returns_422(client, speech_user, override_auth):
    """Test POST /speech/analyze with empty transcript returns 422."""
    override_auth(make_auth_user(speech_user))
    response = client.post(
        "/api/v1/speech/analyze",
        json={"transcript": ""},
    )
    assert response.status_code == 422


@pytest.mark.integration
def test_analyze_batch_empty_list_returns_422(client, speech_user, override_auth):
    """Test POST /speech/analyze/batch with empty transcripts returns 422."""
    override_auth(make_auth_user(speech_user))
    response = client.post(
        "/api/v1/speech/analyze/batch",
        json={"transcripts": []},
    )
    assert response.status_code == 422
