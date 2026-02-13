"""
Integration tests for Consent API endpoints.

Tests consent preferences and history endpoints with authentication.
"""
import pytest
import uuid

from app.database.models import User
from app.services.auth_service import AuthService
from tests.conftest import make_auth_user


@pytest.fixture
def consent_user(db_session):
    """Create a user with bcrypt hash for consent tests."""
    auth_service = AuthService(db_session)
    user = User(
        email=f"consent-{uuid.uuid4().hex[:8]}@example.com",
        name="Consent User",
        password_hash=auth_service.get_password_hash("testpass123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.mark.integration
def test_get_consent_requires_auth(client):
    """Test GET /consent returns 401 when unauthenticated."""
    response = client.get("/api/v1/consent/")
    assert response.status_code == 401


@pytest.mark.integration
def test_get_consent_success(client, consent_user, override_auth):
    """Test GET /consent returns consent preferences when authenticated."""
    override_auth(make_auth_user(consent_user))
    response = client.get("/api/v1/consent/")

    assert response.status_code == 200
    data = response.json()
    assert "consents" in data
    assert len(data["consents"]) == 3
    types = {c["consent_type"] for c in data["consents"]}
    assert types == {"essential", "analytics", "marketing"}


@pytest.mark.integration
def test_put_consent_success(client, consent_user, override_auth):
    """Test PUT /consent updates preferences when authenticated."""
    override_auth(make_auth_user(consent_user))
    response = client.put(
        "/api/v1/consent/",
        json={"consents": [{"consent_type": "marketing", "granted": True}]},
    )

    assert response.status_code == 200
    data = response.json()
    marketing = next(c for c in data["consents"] if c["consent_type"] == "marketing")
    assert marketing["granted"] is True


@pytest.mark.integration
def test_get_consent_history_success(client, consent_user, override_auth):
    """Test GET /consent/history returns history when authenticated."""
    override_auth(make_auth_user(consent_user))
    client.put(
        "/api/v1/consent/",
        json={"consents": [{"consent_type": "analytics", "granted": False}]},
    )
    response = client.get("/api/v1/consent/history")

    assert response.status_code == 200
    data = response.json()
    assert "history" in data
    assert len(data["history"]) >= 1
    assert data["history"][0]["consent_type"] == "analytics"
    assert data["history"][0]["action"] == "withdrawn"


@pytest.mark.integration
def test_put_consent_invalid_type_returns_422(client, consent_user, override_auth):
    """Test PUT /consent with invalid consent_type returns 422."""
    override_auth(make_auth_user(consent_user))
    response = client.put(
        "/api/v1/consent/",
        json={"consents": [{"consent_type": "invalid_type", "granted": True}]},
    )

    assert response.status_code == 422
