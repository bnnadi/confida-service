"""
Integration tests for Data Rights API endpoints.

Tests data export and account deletion for GDPR/CCPA compliance.
"""
import pytest
import uuid

from app.database.models import User
from app.services.auth_service import AuthService
from tests.conftest import make_auth_user


@pytest.fixture
def data_rights_user(db_session):
    """Create a user with bcrypt hash for data rights tests."""
    auth_service = AuthService(db_session)
    user = User(
        email=f"datarights-{uuid.uuid4().hex[:8]}@example.com",
        name="Data Rights User",
        password_hash=auth_service.get_password_hash("testpass123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.mark.integration
def test_export_requires_auth(client):
    """Test GET /data-rights/export returns 401 when unauthenticated."""
    response = client.get("/api/v1/data-rights/export")
    assert response.status_code == 401


@pytest.mark.integration
def test_export_returns_user_data(client, data_rights_user, override_auth):
    """Test GET /data-rights/export returns user data when authenticated."""
    override_auth(make_auth_user(data_rights_user))
    response = client.get("/api/v1/data-rights/export")

    assert response.status_code == 200
    data = response.json()
    assert "exported_at" in data
    assert "user" in data
    assert data["user"]["email"] == data_rights_user.email
    assert "password_hash" not in data["user"]
    assert "sessions" in data
    assert "answers" in data
    assert "consents" in data


@pytest.mark.integration
def test_delete_account_requires_confirmation(client, data_rights_user, override_auth):
    """Test POST /delete-account with confirm=false returns 422."""
    override_auth(make_auth_user(data_rights_user))
    response = client.post(
        "/api/v1/data-rights/delete-account",
        json={"confirm": False, "password": "testpass123"},
    )

    assert response.status_code == 422


@pytest.mark.integration
def test_delete_account_requires_auth(client, data_rights_user):
    """Test POST /delete-account returns 401 when unauthenticated."""
    response = client.post(
        "/api/v1/data-rights/delete-account",
        json={"confirm": True, "password": "testpass123"},
    )
    assert response.status_code == 401


@pytest.mark.integration
def test_delete_account_wrong_password(client, data_rights_user, override_auth):
    """Test POST /delete-account with wrong password returns 401."""
    override_auth(make_auth_user(data_rights_user))
    response = client.post(
        "/api/v1/data-rights/delete-account",
        json={"confirm": True, "password": "wrongpassword"},
    )

    assert response.status_code == 401


@pytest.mark.integration
def test_delete_account_removes_user_and_data(client, data_rights_user, override_auth, db_session):
    """Test POST /delete-account successfully removes user."""
    override_auth(make_auth_user(data_rights_user))
    user_id = data_rights_user.id

    response = client.post(
        "/api/v1/data-rights/delete-account",
        json={"confirm": True, "password": "testpass123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Account deleted successfully"

    user = db_session.query(User).filter(User.id == user_id).first()
    assert user is None
