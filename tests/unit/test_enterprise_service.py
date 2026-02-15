"""
Unit tests for EnterpriseService (INT-49).
"""
import pytest
from datetime import datetime, timedelta, timezone

from app.services.enterprise_service import EnterpriseService
from app.database.models import (
    User,
    UserInvite,
    InterviewSession,
    Organization,
    OrganizationSettings,
    Department,
)
from app.services.auth_service import AuthService


@pytest.mark.unit
def test_get_stats_empty_org(db_session, sample_organization):
    """Test stats with no users or sessions."""
    service = EnterpriseService(db_session)
    stats = service.get_stats(str(sample_organization.id))
    assert stats.totalUsers == 0
    assert stats.activeSessions == 0
    assert stats.totalSessions == 0
    assert stats.averageScore == 0.0
    assert stats.improvementRate == 0.0
    assert stats.organization == "Acme Corp"


@pytest.mark.unit
def test_get_stats_with_data(db_session, sample_organization, enterprise_user):
    """Test stats with users and sessions."""
    session = InterviewSession(
        user_id=enterprise_user.id,
        role="Software Engineer",
        organization_id=sample_organization.id,
        status="completed",
        total_questions=5,
        completed_questions=5,
        overall_score={"overall": 8.5},
    )
    db_session.add(session)
    db_session.commit()

    service = EnterpriseService(db_session)
    stats = service.get_stats(str(sample_organization.id))
    assert stats.totalUsers == 1
    assert stats.totalSessions == 1
    assert stats.averageScore == 8.5
    assert stats.organization == "Acme Corp"


@pytest.mark.unit
def test_get_activity(db_session, sample_organization, enterprise_user):
    """Test activity list with pagination."""
    session = InterviewSession(
        user_id=enterprise_user.id,
        role="Engineer",
        organization_id=sample_organization.id,
        status="completed",
        overall_score={"overall": 7.0},
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(session)
    db_session.commit()

    service = EnterpriseService(db_session)
    resp = service.get_activity(str(sample_organization.id), limit=10, offset=0)
    assert resp.total >= 1
    assert len(resp.items) >= 1
    assert resp.items[0].user == "Enterprise User"
    assert resp.items[0].score == 7.0
    assert resp.items[0].status == "completed"


@pytest.mark.unit
def test_get_performers(db_session, sample_organization, enterprise_user):
    """Test top performers."""
    for i in range(3):
        s = InterviewSession(
            user_id=enterprise_user.id,
            role="Engineer",
            organization_id=sample_organization.id,
            status="completed",
            overall_score={"overall": 7.0 + i},
            created_at=datetime.now(timezone.utc) - timedelta(days=i),
        )
        db_session.add(s)
    db_session.commit()

    service = EnterpriseService(db_session)
    resp = service.get_performers(str(sample_organization.id), limit=5)
    assert len(resp.items) >= 1
    assert resp.items[0].name == "Enterprise User"
    assert resp.items[0].sessions >= 3


@pytest.mark.unit
def test_get_sessions(db_session, sample_organization, enterprise_user, sample_department):
    """Test sessions list with filters."""
    session = InterviewSession(
        user_id=enterprise_user.id,
        role="Engineer",
        organization_id=sample_organization.id,
        department_id=sample_department.id,
        status="completed",
        total_questions=5,
        overall_score={"overall": 8.0},
        feedback="Good session",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(session)
    db_session.commit()

    service = EnterpriseService(db_session)
    resp = service.get_sessions(str(sample_organization.id), limit=50, offset=0)
    assert resp.total >= 1
    assert resp.items[0].department == "Engineering"
    assert resp.items[0].score == 8.0
    assert resp.items[0].feedback == "Good session"


@pytest.mark.unit
def test_get_session_detail(db_session, sample_organization, enterprise_user):
    """Test session detail retrieval."""
    session = InterviewSession(
        user_id=enterprise_user.id,
        role="Engineer",
        organization_id=sample_organization.id,
        status="completed",
        total_questions=5,
        overall_score={"overall": 8.5},
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(session)
    db_session.commit()

    service = EnterpriseService(db_session)
    detail = service.get_session_detail(str(sample_organization.id), str(session.id))
    assert detail is not None
    assert detail.id == str(session.id)
    assert detail.score == 8.5


@pytest.mark.unit
def test_get_session_detail_wrong_org(db_session, sample_organization, sample_user):
    """Test session detail returns None for session in different org."""
    session = InterviewSession(
        user_id=sample_user.id,
        role="Engineer",
        organization_id=None,
        status="completed",
        total_questions=5,
        overall_score={"overall": 8.0},
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(session)
    db_session.commit()

    service = EnterpriseService(db_session)
    detail = service.get_session_detail(str(sample_organization.id), str(session.id))
    assert detail is None


@pytest.mark.unit
def test_get_analytics(db_session, sample_organization, enterprise_user):
    """Test analytics for time range."""
    session = InterviewSession(
        user_id=enterprise_user.id,
        role="Engineer",
        organization_id=sample_organization.id,
        status="completed",
        overall_score={"overall": 7.5},
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(session)
    db_session.commit()

    service = EnterpriseService(db_session)
    resp = service.get_analytics(str(sample_organization.id), "30d")
    assert resp.totalSessions >= 1
    assert resp.averageScore >= 0
    assert isinstance(resp.topSkills, list)
    assert isinstance(resp.departmentStats, list)
    assert isinstance(resp.monthlyTrend, list)


@pytest.mark.unit
def test_get_settings_default(db_session, sample_organization):
    """Test settings returns defaults when none stored."""
    service = EnterpriseService(db_session)
    settings = service.get_settings(str(sample_organization.id))
    assert settings.organization.name == "Acme Corp"
    assert settings.organization.domain == "acme.com"
    assert settings.features.analytics is True
    assert settings.security.sessionTimeout == 30


@pytest.mark.unit
def test_update_settings(db_session, sample_organization):
    """Test partial PATCH of settings."""
    service = EnterpriseService(db_session)
    updated = service.update_settings(
        str(sample_organization.id),
        {"organization": {"timezone": "PST"}, "features": {"sso": True}},
    )
    assert updated.organization.timezone == "PST"
    assert updated.features.sso is True


@pytest.mark.unit
def test_get_departments(db_session, sample_organization, sample_department):
    """Test departments list."""
    service = EnterpriseService(db_session)
    resp = service.get_departments(str(sample_organization.id))
    assert len(resp.items) >= 1
    assert resp.items[0].name == "Engineering"
    assert resp.items[0].id == str(sample_department.id)


@pytest.mark.unit
def test_get_users(db_session, sample_organization, enterprise_user):
    """Test users list in organization."""
    service = EnterpriseService(db_session)
    resp = service.get_users(str(sample_organization.id), limit=50, offset=0)
    assert resp.total >= 1
    assert len(resp.items) >= 1
    assert resp.items[0].email == enterprise_user.email
    assert resp.items[0].role == (enterprise_user.role or "user")


@pytest.mark.unit
def test_get_users_filter_by_role(db_session, sample_organization, enterprise_user):
    """Test users list filtered by role."""
    enterprise_user.role = "admin"
    db_session.commit()
    service = EnterpriseService(db_session)
    resp = service.get_users(str(sample_organization.id), role="admin")
    assert resp.total >= 1
    assert all(item.role == "admin" for item in resp.items)


@pytest.mark.unit
def test_create_invite(db_session, sample_organization, enterprise_user):
    """Test create invite returns invite link."""
    service = EnterpriseService(db_session)
    resp = service.create_invite(
        org_id=str(sample_organization.id),
        inviter_id=str(enterprise_user.id),
        email="newuser@example.com",
        role="user",
    )
    assert resp.invite_id
    assert "invite" in resp.invite_link.lower() or "token=" in resp.invite_link
    assert resp.expires_at
    invite = db_session.query(UserInvite).filter(UserInvite.email == "newuser@example.com").first()
    assert invite is not None
    assert invite.status == "pending"


@pytest.mark.unit
def test_create_invite_email_already_in_org(db_session, sample_organization, enterprise_user):
    """Test create invite fails when email already in org."""
    service = EnterpriseService(db_session)
    with pytest.raises(ValueError, match="already in organization"):
        service.create_invite(
            org_id=str(sample_organization.id),
            inviter_id=str(enterprise_user.id),
            email=enterprise_user.email,
            role="user",
        )


@pytest.mark.unit
def test_create_invite_pending_exists(db_session, sample_organization, enterprise_user):
    """Test create invite fails when pending invite exists for email."""
    from datetime import datetime, timedelta, timezone
    existing = UserInvite(
        organization_id=sample_organization.id,
        email="pending@example.com",
        role="user",
        invite_token="abc123",
        status="pending",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        created_by=enterprise_user.id,
    )
    db_session.add(existing)
    db_session.commit()
    service = EnterpriseService(db_session)
    with pytest.raises(ValueError, match="already exists"):
        service.create_invite(
            org_id=str(sample_organization.id),
            inviter_id=str(enterprise_user.id),
            email="pending@example.com",
            role="user",
        )
