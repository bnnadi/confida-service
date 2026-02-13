"""
Unit tests for Data Rights Service.

Tests user data export and account deletion for GDPR/CCPA compliance.
"""
import pytest
import uuid

from app.services.data_rights_service import DataRightsService
from app.services.auth_service import AuthService
from app.database.models import User, InterviewSession, UserConsent, ConsentHistory


@pytest.fixture
def sample_user_for_export(db_session):
    """Create a sample user with bcrypt hash for data rights tests."""
    auth_service = AuthService(db_session)
    user = User(
        email=f"export-{uuid.uuid4().hex[:8]}@example.com",
        name="Export Test User",
        password_hash=auth_service.get_password_hash("testpass123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.mark.unit
def test_export_user_data_includes_all_entities(db_session, sample_user_for_export):
    """Test export includes user, sessions, performance, analytics, goals, consents."""
    # Add some consent
    consent = UserConsent(
        user_id=sample_user_for_export.id,
        consent_type="analytics",
        granted=True,
    )
    db_session.add(consent)
    db_session.commit()

    service = DataRightsService(db_session)
    data = service.export_user_data(sample_user_for_export.id)

    assert "user" in data
    assert data["user"]["email"] == sample_user_for_export.email
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]
    assert "sessions" in data
    assert "answers" in data
    assert "performance" in data
    assert "analytics_events" in data
    assert "goals" in data
    assert "consents" in data
    assert len(data["consents"]) >= 1


@pytest.mark.unit
def test_export_excludes_password_hash(db_session, sample_user_for_export):
    """Test export does not include password_hash."""
    service = DataRightsService(db_session)
    data = service.export_user_data(sample_user_for_export.id)

    assert "password_hash" not in data["user"]
    assert "password" not in data["user"]


@pytest.mark.unit
def test_delete_user_account_cascades_all_data(db_session, sample_user_for_export):
    """Test delete removes user and related data."""
    # Add consent
    consent = UserConsent(
        user_id=sample_user_for_export.id,
        consent_type="essential",
        granted=True,
    )
    db_session.add(consent)
    db_session.commit()
    user_id = sample_user_for_export.id

    service = DataRightsService(db_session)
    success = service.delete_user_account(user_id)

    assert success is True
    user = db_session.query(User).filter(User.id == user_id).first()
    assert user is None
    remaining = db_session.query(UserConsent).filter(UserConsent.user_id == user_id).all()
    assert len(remaining) == 0


@pytest.mark.unit
def test_delete_user_account_removes_consents(db_session, sample_user_for_export):
    """Test delete removes consent history."""
    consent = UserConsent(
        user_id=sample_user_for_export.id,
        consent_type="marketing",
        granted=False,
    )
    db_session.add(consent)
    history = ConsentHistory(
        user_id=sample_user_for_export.id,
        consent_type="marketing",
        action="withdrawn",
    )
    db_session.add(history)
    db_session.commit()
    user_id = sample_user_for_export.id

    service = DataRightsService(db_session)
    service.delete_user_account(user_id)

    remaining_history = db_session.query(ConsentHistory).filter(ConsentHistory.user_id == user_id).all()
    assert len(remaining_history) == 0


@pytest.mark.unit
def test_export_user_data_not_found(db_session):
    """Test export returns error when user not found."""
    service = DataRightsService(db_session)
    data = service.export_user_data(uuid.uuid4())

    assert "error" in data
    assert data["error"] == "User not found"


@pytest.mark.unit
def test_delete_user_account_not_found(db_session):
    """Test delete returns False when user not found."""
    service = DataRightsService(db_session)
    success = service.delete_user_account(uuid.uuid4())

    assert success is False
