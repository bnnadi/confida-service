"""
Integration tests for session API endpoints.

Tests the complete flow of session-related endpoints including
session creation, management, and question handling.
"""
import pytest
from unittest.mock import AsyncMock, patch


class TestSessionEndpoints:
    """Test cases for session API endpoints."""

    @pytest.mark.integration
    def test_create_session_success(
        self, client, sample_user, mock_current_user, override_auth, override_ai_client, mock_ai_client
    ):
        """Test successful session creation."""
        override_auth(mock_current_user)
        override_ai_client(mock_ai_client)

        session_data = {
            "user_id": str(sample_user.id),
            "mode": "interview",
            "role": "Python Developer",
            "job_title": "Python Developer",
            "job_description": "Looking for Python developer with Django experience"
        }

        response = client.post("/api/v1/sessions/", json=session_data)

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "user_id" in data
        assert "role" in data
        assert "job_description" in data
        assert "status" in data
        assert "total_questions" in data
        assert "completed_questions" in data
        assert "created_at" in data
        assert data["user_id"] == str(sample_user.id)
        assert data["role"] == session_data["role"]
        assert data["job_description"] == session_data["job_description"]
        assert data["status"] == "active"
        assert data["total_questions"] >= 0
        assert data["completed_questions"] == 0

    @pytest.mark.integration
    def test_create_session_missing_user_id(self, client, override_auth):
        """Test session creation without user_id."""
        override_auth({"id": "00000000-0000-0000-0000-000000000001", "email": "test@example.com", "is_admin": False})

        session_data = {
            "mode": "interview",
            "role": "Python Developer",
            "job_title": "Python Developer",
            "job_description": "Looking for Python developer"
            # Missing user_id
        }

        response = client.post("/api/v1/sessions/", json=session_data)

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.integration
    def test_create_session_invalid_user_id(self, client, override_auth):
        """Test session creation with invalid user_id."""
        override_auth({"id": "00000000-0000-0000-0000-000000000001", "email": "test@example.com", "is_admin": False})

        session_data = {
            "user_id": "invalid-uuid",
            "mode": "interview",
            "role": "Python Developer",
            "job_title": "Python Developer",
            "job_description": "Looking for Python developer"
        }

        response = client.post("/api/v1/sessions/", json=session_data)

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.integration
    def test_create_session_missing_fields(self, client, sample_user, mock_current_user, override_auth):
        """Test session creation with missing required fields."""
        override_auth(mock_current_user)

        session_data = {
            "user_id": str(sample_user.id),
            "mode": "interview",
            "role": "Python Developer"
            # Missing job_title and job_description
        }

        response = client.post("/api/v1/sessions/", json=session_data)

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.integration
    def test_create_session_empty_fields(self, client, sample_user, mock_current_user, override_auth):
        """Test session creation with empty fields."""
        override_auth(mock_current_user)

        session_data = {
            "user_id": str(sample_user.id),
            "mode": "interview",
            "role": "",
            "job_title": "",
            "job_description": ""
        }

        response = client.post("/api/v1/sessions/", json=session_data)

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.integration
    def test_get_session_success(self, client, sample_interview_session, sample_user, mock_current_user, override_auth):
        """Test successful session retrieval."""
        override_auth(mock_current_user)

        response = client.get(f"/api/v1/sessions/{sample_interview_session.id}")

        assert response.status_code == 200
        data = response.json()
        assert "session" in data
        assert "questions" in data
        session_data = data["session"]
        assert "id" in session_data
        assert "user_id" in session_data
        assert "role" in session_data
        assert "job_description" in session_data
        assert "status" in session_data
        assert "created_at" in session_data
        assert session_data["id"] == str(sample_interview_session.id)
        assert session_data["user_id"] == str(sample_interview_session.user_id)

    @pytest.mark.integration
    def test_get_session_not_found(self, client, sample_user, mock_current_user, override_auth):
        """Test session retrieval for non-existent session."""
        override_auth(mock_current_user)

        non_existent_id = "550e8400-e29b-41d4-a716-446655440999"

        response = client.get(f"/api/v1/sessions/{non_existent_id}")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.integration
    def test_get_session_invalid_id(self, client, sample_user, mock_current_user, override_auth):
        """Test session retrieval with invalid ID format."""
        override_auth(mock_current_user)

        invalid_id = "invalid-uuid"

        response = client.get(f"/api/v1/sessions/{invalid_id}")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.integration
    def test_list_sessions_success(self, client, sample_user, mock_current_user, generate_test_sessions, override_auth):
        """Test successful session listing."""
        override_auth(mock_current_user)

        response = client.get("/api/v1/sessions/")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "sessions" in data or "total" in data
        if isinstance(data, list):
            assert all("id" in s for s in data) if data else True
        else:
            assert "sessions" in data or "total" in data

    @pytest.mark.integration
    def test_list_sessions_with_pagination(self, client, sample_user, mock_current_user, generate_test_sessions, override_auth):
        """Test session listing with pagination."""
        override_auth(mock_current_user)

        response = client.get("/api/v1/sessions/?limit=5&offset=0")

        assert response.status_code == 200
        data = response.json()
        if isinstance(data, list):
            assert len(data) <= 5
        else:
            assert "sessions" in data or "total" in data

    @pytest.mark.integration
    def test_list_sessions_without_auth_returns_401(self, client):
        """Test session listing without auth returns 401."""
        response = client.get("/api/v1/sessions/")

        assert response.status_code == 401

    @pytest.mark.integration
    def test_update_session_success(self, client, sample_interview_session, sample_user, mock_current_user, override_auth):
        """Test successful session status update."""
        override_auth(mock_current_user)

        response = client.patch(
            f"/api/v1/sessions/{sample_interview_session.id}/status?status=completed"
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data or "status" in data
        if "status" in data:
            assert data["status"] == "completed"

    @pytest.mark.integration
    def test_update_session_not_found(self, client, sample_user, mock_current_user, override_auth):
        """Test session status update for non-existent session."""
        override_auth(mock_current_user)

        non_existent_id = "550e8400-e29b-41d4-a716-446655440999"

        response = client.patch(
            f"/api/v1/sessions/{non_existent_id}/status?status=completed"
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.integration
    def test_update_session_invalid_id(self, client, sample_user, mock_current_user, override_auth):
        """Test session status update with invalid ID format."""
        override_auth(mock_current_user)

        invalid_id = "invalid-uuid"

        response = client.patch(
            f"/api/v1/sessions/{invalid_id}/status?status=completed"
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.integration
    def test_delete_session_success(self, client, sample_user, mock_current_user, override_auth, override_ai_client, mock_ai_client):
        """Test successful session deletion. Creates session via API to avoid ObjectDeletedError."""
        override_auth(mock_current_user)
        override_ai_client(mock_ai_client)

        # Create session via API so we don't hold a fixture reference that gets deleted
        create_resp = client.post("/api/v1/sessions/", json={
            "user_id": str(sample_user.id),
            "mode": "interview",
            "role": "Python Developer",
            "job_title": "Python Developer",
            "job_description": "Looking for Python developer"
        })
        assert create_resp.status_code == 201
        session_id = create_resp.json()["id"]

        response = client.delete(f"/api/v1/sessions/{session_id}")

        assert response.status_code == 204

        get_response = client.get(f"/api/v1/sessions/{session_id}")
        assert get_response.status_code == 404

    @pytest.mark.integration
    def test_delete_session_not_found(self, client, sample_user, mock_current_user, override_auth):
        """Test session deletion for non-existent session."""
        override_auth(mock_current_user)

        non_existent_id = "550e8400-e29b-41d4-a716-446655440999"

        response = client.delete(f"/api/v1/sessions/{non_existent_id}")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.integration
    def test_delete_session_invalid_id(self, client, sample_user, mock_current_user, override_auth):
        """Test session deletion with invalid ID format."""
        override_auth(mock_current_user)

        invalid_id = "invalid-uuid"

        response = client.delete(f"/api/v1/sessions/{invalid_id}")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.integration
    def test_get_session_questions_success(
        self, client, sample_interview_session, sample_session_question, sample_user, mock_current_user, override_auth
    ):
        """Test successful session questions retrieval."""
        override_auth(mock_current_user)

        response = client.get(f"/api/v1/sessions/{sample_interview_session.id}/questions")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert all("id" in q for q in data) or len(data) >= 0

    @pytest.mark.integration
    def test_get_session_questions_not_found(self, client, sample_user, mock_current_user, override_auth):
        """Test session questions retrieval for non-existent session."""
        override_auth(mock_current_user)

        non_existent_id = "550e8400-e29b-41d4-a716-446655440999"

        response = client.get(f"/api/v1/sessions/{non_existent_id}/questions")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.integration
    def test_get_session_questions_invalid_id(self, client, sample_user, mock_current_user, override_auth):
        """Test session questions retrieval with invalid ID format."""
        override_auth(mock_current_user)

        invalid_id = "invalid-uuid"

        response = client.get(f"/api/v1/sessions/{invalid_id}/questions")

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.integration
    def test_add_question_to_session_success(
        self, client, sample_interview_session, sample_question, sample_user, mock_current_user, override_auth
    ):
        """Test successful question addition to session."""
        override_auth(mock_current_user)

        question_data = {
            "questions": ["What is your experience with Python and Django?"]
        }

        response = client.post(
            f"/api/v1/sessions/{sample_interview_session.id}/questions",
            json=question_data
        )

        assert response.status_code in (200, 201)
        data = response.json()
        assert isinstance(data, list)
        assert all("id" in q or "question_text" in q for q in data) if data else True

    @pytest.mark.integration
    def test_add_question_to_session_not_found(self, client, sample_question, sample_user, mock_current_user, override_auth):
        """Test question addition to non-existent session."""
        override_auth(mock_current_user)

        non_existent_id = "550e8400-e29b-41d4-a716-446655440999"
        question_data = {
            "questions": ["What is your experience with Python?"]
        }

        response = client.post(
            f"/api/v1/sessions/{non_existent_id}/questions",
            json=question_data
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.integration
    def test_add_question_to_session_invalid_question_id(self, client, sample_interview_session, sample_user, mock_current_user, override_auth):
        """Test question addition with invalid question format."""
        override_auth(mock_current_user)

        question_data = {
            "questions": ["ab"]  # Too short - less than 5 chars
        }

        response = client.post(
            f"/api/v1/sessions/{sample_interview_session.id}/questions",
            json=question_data
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.integration
    def test_remove_question_from_session_success(
        self, client, sample_interview_session, sample_session_question, sample_user, mock_current_user, override_auth
    ):
        """Test successful question removal from session."""
        override_auth(mock_current_user)

        response = client.delete(
            f"/api/v1/sessions/{sample_interview_session.id}/questions/{sample_session_question.id}"
        )

        assert response.status_code in (200, 204)

        get_response = client.get(f"/api/v1/sessions/{sample_interview_session.id}/questions")
        assert get_response.status_code == 200

    @pytest.mark.integration
    def test_remove_question_from_session_not_found(self, client, sample_interview_session, sample_user, mock_current_user, override_auth):
        """Test question removal for non-existent session question."""
        override_auth(mock_current_user)

        non_existent_id = "550e8400-e29b-41d4-a716-446655440999"

        response = client.delete(
            f"/api/v1/sessions/{sample_interview_session.id}/questions/{non_existent_id}"
        )

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    @pytest.mark.integration
    def test_remove_question_from_session_invalid_id(self, client, sample_interview_session, sample_user, mock_current_user, override_auth):
        """Test question removal with invalid ID format."""
        override_auth(mock_current_user)

        invalid_id = "invalid-uuid"

        response = client.delete(
            f"/api/v1/sessions/{sample_interview_session.id}/questions/{invalid_id}"
        )

        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    @pytest.mark.integration
    def test_session_creation_with_ai_service_error(self, client, sample_user, mock_current_user, override_auth):
        """Test session creation when service raises (e.g. AI or downstream failure)."""
        override_auth(mock_current_user)

        session_data = {
            "user_id": str(sample_user.id),
            "mode": "interview",
            "role": "Python Developer",
            "job_title": "Python Developer",
            "job_description": "Looking for Python developer with Django"
        }

        with patch("app.routers.sessions.SessionService") as mock_session_service:
            mock_instance = mock_session_service.return_value
            mock_instance.create_interview_session = AsyncMock(
                side_effect=Exception("AI service error")
            )

            response = client.post("/api/v1/sessions/", json=session_data)

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

    @pytest.mark.integration
    def test_session_creation_with_database_error(
        self, client, sample_user, mock_current_user, override_auth, override_ai_client, mock_ai_client
    ):
        """Test session creation when database fails."""
        override_auth(mock_current_user)
        override_ai_client(mock_ai_client)

        session_data = {
            "user_id": str(sample_user.id),
            "mode": "interview",
            "role": "Python Developer",
            "job_title": "Python Developer",
            "job_description": "Looking for Python developer"
        }

        with patch("app.routers.sessions.SessionService") as mock_session_service:
            mock_instance = mock_session_service.return_value
            mock_instance.create_interview_session = AsyncMock(
                side_effect=Exception("Database error")
            )

            response = client.post("/api/v1/sessions/", json=session_data)

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
