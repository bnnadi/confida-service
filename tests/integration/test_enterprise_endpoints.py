"""
Integration tests for Enterprise API endpoints (INT-49).
"""
import pytest


@pytest.mark.integration
def test_enterprise_stats_unauthorized(client):
    """Test stats returns 401 without token."""
    response = client.get("/api/v1/enterprise/stats")
    assert response.status_code == 401


@pytest.mark.integration
def test_enterprise_stats_forbidden_non_enterprise_user(
    client, db_session, sample_user
):
    """Test stats returns 403 when user has no organization.
    
    Use real auth: login as user without organization_id, then call enterprise endpoint.
    """
    from app.services.auth_service import AuthService
    auth_service = AuthService(db_session)
    token = auth_service.create_access_token(
        user_id=str(sample_user.id),
        email=sample_user.email,
        role="user",
    )
    response = client.get(
        "/api/v1/enterprise/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


@pytest.mark.integration
def test_enterprise_stats_success(
    client, override_enterprise_auth, mock_enterprise_user
):
    """Test stats returns 200 with correct schema."""
    override_enterprise_auth(mock_enterprise_user)
    response = client.get("/api/v1/enterprise/stats")
    assert response.status_code == 200
    data = response.json()
    assert "totalUsers" in data
    assert "activeSessions" in data
    assert "totalSessions" in data
    assert "averageScore" in data
    assert "improvementRate" in data
    assert "organization" in data


@pytest.mark.integration
def test_enterprise_activity_success(
    client, override_enterprise_auth, mock_enterprise_user
):
    """Test activity returns 200."""
    override_enterprise_auth(mock_enterprise_user)
    response = client.get("/api/v1/enterprise/activity", params={"limit": 10, "offset": 0})
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.integration
def test_enterprise_performers_success(
    client, override_enterprise_auth, mock_enterprise_user
):
    """Test performers returns 200."""
    override_enterprise_auth(mock_enterprise_user)
    response = client.get("/api/v1/enterprise/performers", params={"limit": 10})
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.integration
def test_enterprise_sessions_success(
    client, override_enterprise_auth, mock_enterprise_user
):
    """Test sessions list returns 200."""
    override_enterprise_auth(mock_enterprise_user)
    response = client.get(
        "/api/v1/enterprise/sessions",
        params={"status": "all", "limit": 50, "offset": 0},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.integration
def test_enterprise_session_detail_not_found(
    client, override_enterprise_auth, mock_enterprise_user
):
    """Test session detail returns 404 for non-existent session."""
    override_enterprise_auth(mock_enterprise_user)
    response = client.get(
        "/api/v1/enterprise/sessions/00000000-0000-0000-0000-000000000001"
    )
    assert response.status_code == 404


@pytest.mark.integration
def test_enterprise_analytics_success(
    client, override_enterprise_auth, mock_enterprise_user
):
    """Test analytics returns 200 with valid timeRange."""
    override_enterprise_auth(mock_enterprise_user)
    response = client.get("/api/v1/enterprise/analytics", params={"timeRange": "30d"})
    assert response.status_code == 200
    data = response.json()
    assert "totalSessions" in data
    assert "averageScore" in data
    assert "topSkills" in data
    assert "departmentStats" in data
    assert "monthlyTrend" in data


@pytest.mark.integration
def test_enterprise_analytics_invalid_time_range(
    client, override_enterprise_auth, mock_enterprise_user
):
    """Test analytics returns 422 for invalid timeRange."""
    override_enterprise_auth(mock_enterprise_user)
    response = client.get("/api/v1/enterprise/analytics", params={"timeRange": "invalid"})
    assert response.status_code == 422


@pytest.mark.integration
def test_enterprise_settings_get_success(
    client, override_enterprise_auth, mock_enterprise_user
):
    """Test settings GET returns 200."""
    override_enterprise_auth(mock_enterprise_user)
    response = client.get("/api/v1/enterprise/settings")
    assert response.status_code == 200
    data = response.json()
    assert "organization" in data
    assert "features" in data
    assert "notifications" in data
    assert "security" in data


@pytest.mark.integration
def test_enterprise_settings_patch_success(
    client, override_enterprise_auth, mock_enterprise_user
):
    """Test settings PATCH returns 200 with updated values."""
    override_enterprise_auth(mock_enterprise_user)
    response = client.patch(
        "/api/v1/enterprise/settings",
        json={"organization": {"timezone": "EST"}},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["organization"]["timezone"] == "EST"


@pytest.mark.integration
def test_enterprise_departments_success(
    client, override_enterprise_auth, mock_enterprise_user
):
    """Test departments returns 200."""
    override_enterprise_auth(mock_enterprise_user)
    response = client.get("/api/v1/enterprise/departments")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


@pytest.mark.integration
def test_enterprise_users_list_success(
    client, override_enterprise_auth, mock_enterprise_user
):
    """Test GET /enterprise/users returns 200."""
    override_enterprise_auth(mock_enterprise_user)
    response = client.get("/api/v1/enterprise/users", params={"limit": 50, "offset": 0})
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.integration
def test_enterprise_users_invite_success(
    client, override_enterprise_auth, mock_enterprise_user
):
    """Test POST /enterprise/users/invite returns 201 with invite link."""
    override_enterprise_auth(mock_enterprise_user)
    response = client.post(
        "/api/v1/enterprise/users/invite",
        json={"email": "invited-new@example.com", "role": "user"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "invite_id" in data
    assert "invite_link" in data
    assert "expires_at" in data


@pytest.mark.integration
def test_enterprise_create_organization_self_serve(
    client, override_auth, mock_current_user, sample_user, db_session
):
    """Test POST /enterprise/organizations (self-serve) when user has no org."""
    override_auth(mock_current_user)
    response = client.post(
        "/api/v1/enterprise/organizations",
        json={"name": "My New Org", "domain": "myorg.com"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "My New Org"
    assert data["domain"] == "myorg.com"
    assert "id" in data
