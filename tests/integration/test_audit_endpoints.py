"""
Integration tests for Admin Audit API endpoints (INT-32).

Tests audit log querying, compliance reports, GDPR/CCPA compliance checks,
and suspicious activity detection endpoints.
"""
import pytest
from fastapi.testclient import TestClient

from app.services.audit_service import log_data_access


class TestAuditEndpoints:
    """Test cases for Admin Audit API endpoints."""

    @pytest.mark.integration
    def test_audit_logs_requires_admin(self, client: TestClient):
        """Test audit logs endpoint returns 401 without admin auth."""
        response = client.get("/api/v1/admin/audit/logs")
        assert response.status_code == 401

    @pytest.mark.integration
    def test_audit_logs_success(self, client: TestClient, admin_user, override_admin_auth):
        """Test audit logs endpoint returns 200 with admin auth."""
        override_admin_auth({
            "id": str(admin_user.id),
            "email": admin_user.email,
            "is_admin": True,
            "role": "admin",
        })
        response = client.get("/api/v1/admin/audit/logs")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "limit" in data
        assert "offset" in data

    @pytest.mark.integration
    def test_audit_logs_with_filters(
        self, client: TestClient, admin_user, override_admin_auth, db_session, sample_user
    ):
        """Test audit logs with filters applied."""
        log_data_access(db_session, str(sample_user.id), "session", "read", resource_id="sess-1")
        db_session.commit()
        override_admin_auth({
            "id": str(admin_user.id),
            "email": admin_user.email,
            "is_admin": True,
            "role": "admin",
        })
        response = client.get(
            f"/api/v1/admin/audit/logs?user_id={sample_user.id}&resource_type=session&action=read"
        )
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert len(data["logs"]) >= 1
        assert data["logs"][0]["resource_type"] == "session"
        assert data["logs"][0]["action"] == "read"

    @pytest.mark.integration
    def test_audit_summary_requires_admin(self, client: TestClient):
        """Test audit summary endpoint returns 401 without admin auth."""
        response = client.get("/api/v1/admin/audit/summary")
        assert response.status_code == 401

    @pytest.mark.integration
    def test_audit_summary_success(self, client: TestClient, admin_user, override_admin_auth):
        """Test audit summary endpoint returns 200 with expected structure."""
        override_admin_auth({
            "id": str(admin_user.id),
            "email": admin_user.email,
            "is_admin": True,
            "role": "admin",
        })
        response = client.get("/api/v1/admin/audit/summary")
        assert response.status_code == 200
        data = response.json()
        assert "total_events" in data
        assert "by_resource_type" in data
        assert "by_action" in data
        assert "since" in data

    @pytest.mark.integration
    def test_consent_history_requires_admin(self, client: TestClient):
        """Test consent history endpoint returns 401 without admin auth."""
        response = client.get("/api/v1/admin/audit/consent-history")
        assert response.status_code == 401

    @pytest.mark.integration
    def test_consent_history_success(self, client: TestClient, admin_user, override_admin_auth):
        """Test consent history endpoint returns 200 with history."""
        override_admin_auth({
            "id": str(admin_user.id),
            "email": admin_user.email,
            "is_admin": True,
            "role": "admin",
        })
        response = client.get("/api/v1/admin/audit/consent-history")
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert "limit" in data
        assert "offset" in data

    @pytest.mark.integration
    def test_suspicious_requires_admin(self, client: TestClient):
        """Test suspicious activity endpoint returns 401 without admin auth."""
        response = client.get("/api/v1/admin/audit/suspicious")
        assert response.status_code == 401

    @pytest.mark.integration
    def test_suspicious_success(self, client: TestClient, admin_user, override_admin_auth):
        """Test suspicious activity endpoint returns 200 with findings structure."""
        override_admin_auth({
            "id": str(admin_user.id),
            "email": admin_user.email,
            "is_admin": True,
            "role": "admin",
        })
        response = client.get("/api/v1/admin/audit/suspicious")
        assert response.status_code == 200
        data = response.json()
        assert "findings" in data
        assert "since" in data

    @pytest.mark.integration
    def test_compliance_report_requires_admin(self, client: TestClient):
        """Test compliance report endpoint returns 401 without admin auth."""
        response = client.get("/api/v1/admin/audit/compliance-report")
        assert response.status_code == 401

    @pytest.mark.integration
    def test_compliance_report_success(self, client: TestClient, admin_user, override_admin_auth):
        """Test compliance report endpoint returns 200 with expected structure."""
        override_admin_auth({
            "id": str(admin_user.id),
            "email": admin_user.email,
            "is_admin": True,
            "role": "admin",
        })
        response = client.get("/api/v1/admin/audit/compliance-report")
        assert response.status_code == 200
        data = response.json()
        assert "period" in data
        assert "data_access" in data
        assert "consent" in data
        assert "suspicious_activity_count" in data

    @pytest.mark.integration
    def test_compliance_status_requires_admin(self, client: TestClient):
        """Test compliance status endpoint returns 401 without admin auth."""
        response = client.get("/api/v1/admin/audit/compliance-status")
        assert response.status_code == 401

    @pytest.mark.integration
    def test_compliance_status_success(self, client: TestClient, admin_user, override_admin_auth):
        """Test compliance status endpoint returns 200 with GDPR/CCPA checklist."""
        override_admin_auth({
            "id": str(admin_user.id),
            "email": admin_user.email,
            "is_admin": True,
            "role": "admin",
        })
        response = client.get("/api/v1/admin/audit/compliance-status")
        assert response.status_code == 200
        data = response.json()
        assert "gdpr_ccpa_compliance" in data
        assert "overall" in data
