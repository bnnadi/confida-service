"""
Unit tests for Audit Service (INT-32).

Tests detect_suspicious_activity and related audit service functions.
"""
import pytest
import uuid
from datetime import datetime, timedelta

from app.services.audit_service import (
    detect_suspicious_activity,
    SUSPICIOUS_EXPORTS_PER_DAY,
    SUSPICIOUS_ACCESS_PER_HOUR,
    SUSPICIOUS_UNIQUE_IPS_PER_USER,
)
from app.database.models import User, DataAccessLog
from app.services.auth_service import AuthService


@pytest.fixture
def sample_user_for_audit(db_session):
    """Create a sample user for audit tests."""
    auth_service = AuthService(db_session)
    user = User(
        email=f"audit-{uuid.uuid4().hex[:8]}@example.com",
        name="Audit Test User",
        password_hash=auth_service.get_password_hash("testpass123"),
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.mark.unit
def test_detect_suspicious_returns_empty_when_no_data(db_session):
    """Test detect_suspicious_activity returns empty list when no data."""
    since = datetime.utcnow() - timedelta(hours=1)
    findings = detect_suspicious_activity(db_session, since=since)
    assert findings == []


@pytest.mark.unit
def test_detect_suspicious_high_export_volume(db_session, sample_user_for_audit):
    """Test high export volume triggers finding."""
    recent = datetime.utcnow()
    since = recent - timedelta(hours=1)
    for _ in range(SUSPICIOUS_EXPORTS_PER_DAY + 1):
        log = DataAccessLog(
            user_id=sample_user_for_audit.id,
            resource_type="export",
            action="export",
            ip_address="192.168.1.1",
            created_at=recent,
        )
        db_session.add(log)
    db_session.commit()
    findings = detect_suspicious_activity(db_session, since=since)
    export_findings = [f for f in findings if f["type"] == "high_export_volume"]
    assert len(export_findings) >= 1
    assert len(export_findings) == 1
    assert export_findings[0]["user_id"] == str(sample_user_for_audit.id)
    assert export_findings[0]["count"] >= SUSPICIOUS_EXPORTS_PER_DAY


@pytest.mark.unit
def test_detect_suspicious_below_export_threshold(db_session, sample_user_for_audit):
    """Test below export threshold returns no finding."""
    recent = datetime.utcnow()
    since = recent - timedelta(hours=1)
    for _ in range(SUSPICIOUS_EXPORTS_PER_DAY - 1):
        log = DataAccessLog(
            user_id=sample_user_for_audit.id,
            resource_type="export",
            action="export",
            created_at=recent,
        )
        db_session.add(log)
    db_session.commit()
    findings = detect_suspicious_activity(db_session, since=since)
    export_findings = [f for f in findings if f["type"] == "high_export_volume"]
    assert len(export_findings) == 0


@pytest.mark.unit
def test_detect_suspicious_high_access_volume(db_session, sample_user_for_audit):
    """Test high access volume triggers finding."""
    recent = datetime.utcnow()
    since = recent - timedelta(hours=1)
    for i in range(SUSPICIOUS_ACCESS_PER_HOUR + 5):
        log = DataAccessLog(
            user_id=sample_user_for_audit.id,
            resource_type="session",
            action="read",
            resource_id=f"sess-{i}",
            created_at=recent,
        )
        db_session.add(log)
    db_session.commit()
    findings = detect_suspicious_activity(db_session, since=since)
    access_findings = [f for f in findings if f["type"] == "high_access_volume"]
    assert len(access_findings) >= 1
    assert access_findings[0]["user_id"] == str(sample_user_for_audit.id)
    assert access_findings[0]["count"] >= SUSPICIOUS_ACCESS_PER_HOUR


@pytest.mark.unit
def test_detect_suspicious_multiple_ips(db_session, sample_user_for_audit):
    """Test multiple IPs per user triggers finding."""
    recent = datetime.utcnow()
    since = recent - timedelta(hours=1)
    for i in range(SUSPICIOUS_UNIQUE_IPS_PER_USER):
        log = DataAccessLog(
            user_id=sample_user_for_audit.id,
            resource_type="session",
            action="read",
            ip_address=f"192.168.1.{i}",
            created_at=recent,
        )
        db_session.add(log)
    db_session.commit()
    findings = detect_suspicious_activity(db_session, since=since)
    ip_findings = [f for f in findings if f["type"] == "multiple_ips"]
    assert len(ip_findings) >= 1
    assert ip_findings[0]["user_id"] == str(sample_user_for_audit.id)
    assert ip_findings[0]["unique_ips"] >= SUSPICIOUS_UNIQUE_IPS_PER_USER


@pytest.mark.unit
def test_detect_suspicious_respects_since_filter(db_session, sample_user_for_audit):
    """Test old logs outside since window are not included."""
    old_since = datetime.utcnow() - timedelta(days=7)
    for _ in range(SUSPICIOUS_EXPORTS_PER_DAY + 1):
        log = DataAccessLog(
            user_id=sample_user_for_audit.id,
            resource_type="export",
            action="export",
            created_at=datetime.utcnow() - timedelta(days=5),
        )
        db_session.add(log)
    db_session.commit()
    recent_since = datetime.utcnow() - timedelta(hours=1)
    findings = detect_suspicious_activity(db_session, since=recent_since)
    export_findings = [f for f in findings if f["type"] == "high_export_volume"]
    assert len(export_findings) == 0


@pytest.mark.unit
def test_detect_suspicious_combines_findings(db_session, sample_user_for_audit):
    """Test user triggering multiple rules produces multiple findings."""
    recent = datetime.utcnow()
    since = recent - timedelta(hours=1)
    for i in range(SUSPICIOUS_EXPORTS_PER_DAY + 1):
        log = DataAccessLog(
            user_id=sample_user_for_audit.id,
            resource_type="export",
            action="export",
            ip_address=f"10.0.0.{i}",
            created_at=recent,
        )
        db_session.add(log)
    for i in range(SUSPICIOUS_ACCESS_PER_HOUR - SUSPICIOUS_EXPORTS_PER_DAY - 1):
        log = DataAccessLog(
            user_id=sample_user_for_audit.id,
            resource_type="session",
            action="read",
            resource_id=f"sess-{i}",
            created_at=recent,
        )
        db_session.add(log)
    db_session.commit()
    findings = detect_suspicious_activity(db_session, since=since)
    assert len(findings) >= 2
    types = {f["type"] for f in findings}
    assert "high_export_volume" in types
    assert "high_access_volume" in types
