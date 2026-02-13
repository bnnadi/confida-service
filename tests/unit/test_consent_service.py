"""
Unit tests for Consent Service.

Tests consent CRUD operations and history tracking.
"""
import pytest
import uuid

from app.services.consent_service import ConsentService
from app.database.models import User, UserConsent, ConsentHistory


@pytest.fixture
def sample_user_for_consent(db_session):
    """Create a sample user for consent tests."""
    from werkzeug.security import generate_password_hash
    user = User(
        email=f"consent-{uuid.uuid4().hex[:8]}@example.com",
        name="Consent Test User",
        password_hash=generate_password_hash("testpass123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.mark.unit
def test_get_consents_returns_defaults_for_new_user(db_session, sample_user_for_consent):
    """Test getting consents for user with no stored preferences returns defaults."""
    service = ConsentService(db_session)
    consents = service.get_consents(sample_user_for_consent.id)

    assert len(consents) == 3
    types = {c["consent_type"] for c in consents}
    assert types == {"essential", "analytics", "marketing"}
    essential = next(c for c in consents if c["consent_type"] == "essential")
    analytics = next(c for c in consents if c["consent_type"] == "analytics")
    marketing = next(c for c in consents if c["consent_type"] == "marketing")
    assert essential["granted"] is True
    assert analytics["granted"] is True
    assert marketing["granted"] is False


@pytest.mark.unit
def test_update_consent_single(db_session, sample_user_for_consent):
    """Test updating a single consent preference."""
    service = ConsentService(db_session)
    service.update_consent(sample_user_for_consent.id, "marketing", True)

    consents = service.get_consents(sample_user_for_consent.id)
    marketing = next(c for c in consents if c["consent_type"] == "marketing")
    assert marketing["granted"] is True
    assert marketing["updated_at"] is not None


@pytest.mark.unit
def test_update_consents_bulk(db_session, sample_user_for_consent):
    """Test bulk updating consent preferences."""
    service = ConsentService(db_session)
    preferences = {"analytics": False, "marketing": True}
    service.update_consents(sample_user_for_consent.id, preferences)

    consents = service.get_consents(sample_user_for_consent.id)
    analytics = next(c for c in consents if c["consent_type"] == "analytics")
    marketing = next(c for c in consents if c["consent_type"] == "marketing")
    assert analytics["granted"] is False
    assert marketing["granted"] is True


@pytest.mark.unit
def test_consent_history_appended_on_update(db_session, sample_user_for_consent):
    """Test that consent history is appended when consent is updated."""
    service = ConsentService(db_session)
    service.update_consent(sample_user_for_consent.id, "analytics", False)
    service.update_consent(sample_user_for_consent.id, "analytics", True)

    history = service.get_consent_history(sample_user_for_consent.id)
    assert len(history) >= 2
    actions = [h["action"] for h in history if h["consent_type"] == "analytics"]
    assert "granted" in actions
    assert "withdrawn" in actions


@pytest.mark.unit
def test_get_consent_history_paginated(db_session, sample_user_for_consent):
    """Test consent history respects limit parameter."""
    service = ConsentService(db_session)
    for _ in range(5):
        service.update_consent(sample_user_for_consent.id, "marketing", True)
        service.update_consent(sample_user_for_consent.id, "marketing", False)

    history = service.get_consent_history(sample_user_for_consent.id, limit=3)
    assert len(history) == 3


@pytest.mark.unit
def test_update_consent_invalid_type_raises(db_session, sample_user_for_consent):
    """Test that invalid consent type raises ValueError."""
    service = ConsentService(db_session)
    with pytest.raises(ValueError, match="Invalid consent_type"):
        service.update_consent(sample_user_for_consent.id, "invalid_type", True)
