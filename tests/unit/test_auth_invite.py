"""
Unit tests for AuthService invite flow (INT-38).
"""
import pytest
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException

from app.services.auth_service import AuthService
from app.database.models import User, UserInvite, Organization, Department


@pytest.mark.unit
def test_validate_invite_success(db_session, sample_organization, enterprise_user):
    """Test validate_invite returns invite details for valid token."""
    invite = UserInvite(
        organization_id=sample_organization.id,
        email="invited@example.com",
        role="user",
        invite_token="valid-token-123",
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        created_by=enterprise_user.id,
    )
    db_session.add(invite)
    db_session.commit()

    auth_service = AuthService(db_session)
    details = auth_service.validate_invite("valid-token-123")
    assert details["email"] == "invited@example.com"
    assert details["organization_name"] == "Acme Corp"
    assert details["role"] == "user"


@pytest.mark.unit
def test_validate_invite_invalid_token(db_session):
    """Test validate_invite raises 404 for invalid token."""
    auth_service = AuthService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        auth_service.validate_invite("invalid-token")
    assert exc_info.value.status_code == 404


@pytest.mark.unit
def test_accept_invite_success(db_session, sample_organization, enterprise_user, sample_department):
    """Test accept_invite creates user with org/department and marks invite accepted."""
    invite = UserInvite(
        organization_id=sample_organization.id,
        department_id=sample_department.id,
        email="newinvite@example.com",
        role="admin",
        invite_token="accept-token-456",
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        created_by=enterprise_user.id,
    )
    db_session.add(invite)
    db_session.commit()

    auth_service = AuthService(db_session)
    user = auth_service.accept_invite(
        token="accept-token-456",
        password="SecurePass123",
        name="New User",
    )
    assert user.email == "newinvite@example.com"
    assert user.organization_id == sample_organization.id
    assert user.department_id == sample_department.id
    assert user.role == "admin"
    assert user.name == "New User"

    db_session.refresh(invite)
    assert invite.status == "accepted"


@pytest.mark.unit
def test_accept_invite_email_already_registered(db_session, sample_organization, enterprise_user):
    """Test accept_invite raises 400 when email already has account."""
    invite = UserInvite(
        organization_id=sample_organization.id,
        email=enterprise_user.email,
        role="user",
        invite_token="dup-token",
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        created_by=enterprise_user.id,
    )
    db_session.add(invite)
    db_session.commit()

    auth_service = AuthService(db_session)
    with pytest.raises(HTTPException) as exc_info:
        auth_service.accept_invite(
            token="dup-token",
            password="SecurePass123",
            name="Test",
        )
    assert exc_info.value.status_code == 400
