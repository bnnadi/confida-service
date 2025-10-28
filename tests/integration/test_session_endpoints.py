"""
Integration tests for session API endpoints.

Tests the complete flow of session-related endpoints including
session creation, management, and question handling.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import json


class TestSessionEndpoints:
    """Test cases for session API endpoints."""
    
    @pytest.mark.integration
    def test_create_session_success(self, client, sample_user, sample_parse_request, mock_ai_client):
        """Test successful session creation."""
        # Arrange
        session_data = {
            "role": "Python Developer",
            "job_description": "Looking for Python developer with Django experience"
        }
        
        with patch('app.routers.interview.get_ai_client_dependency', return_value=mock_ai_client):
            # Act
            response = client.post(
                f"/api/v1/sessions/?user_id={sample_user.id}",
                json=session_data
            )
            
            # Assert
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
            assert data["total_questions"] > 0
            assert data["completed_questions"] == 0
    
    @pytest.mark.integration
    def test_create_session_missing_user_id(self, client):
        """Test session creation without user_id."""
        # Arrange
        session_data = {
            "role": "Python Developer",
            "job_description": "Looking for Python developer"
        }
        
        # Act
        response = client.post("/api/v1/sessions/", json=session_data)
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.integration
    def test_create_session_invalid_user_id(self, client):
        """Test session creation with invalid user_id."""
        # Arrange
        session_data = {
            "role": "Python Developer",
            "job_description": "Looking for Python developer"
        }
        invalid_user_id = "invalid-uuid"
        
        # Act
        response = client.post(
            f"/api/v1/sessions/?user_id={invalid_user_id}",
            json=session_data
        )
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.integration
    def test_create_session_missing_fields(self, client, sample_user):
        """Test session creation with missing required fields."""
        # Arrange
        session_data = {
            "role": "Python Developer"
            # Missing job_description
        }
        
        # Act
        response = client.post(
            f"/api/v1/sessions/?user_id={sample_user.id}",
            json=session_data
        )
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.integration
    def test_create_session_empty_fields(self, client, sample_user):
        """Test session creation with empty fields."""
        # Arrange
        session_data = {
            "role": "",
            "job_description": ""
        }
        
        # Act
        response = client.post(
            f"/api/v1/sessions/?user_id={sample_user.id}",
            json=session_data
        )
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.integration
    def test_get_session_success(self, client, sample_interview_session):
        """Test successful session retrieval."""
        # Act
        response = client.get(f"/api/v1/sessions/{sample_interview_session.id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "user_id" in data
        assert "role" in data
        assert "job_description" in data
        assert "status" in data
        assert "total_questions" in data
        assert "completed_questions" in data
        assert "created_at" in data
        assert data["id"] == str(sample_interview_session.id)
        assert data["user_id"] == str(sample_interview_session.user_id)
    
    @pytest.mark.integration
    def test_get_session_not_found(self, client):
        """Test session retrieval for non-existent session."""
        # Arrange
        non_existent_id = "550e8400-e29b-41d4-a716-446655440999"
        
        # Act
        response = client.get(f"/api/v1/sessions/{non_existent_id}")
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    @pytest.mark.integration
    def test_get_session_invalid_id(self, client):
        """Test session retrieval with invalid ID format."""
        # Arrange
        invalid_id = "invalid-uuid"
        
        # Act
        response = client.get(f"/api/v1/sessions/{invalid_id}")
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.integration
    def test_list_sessions_success(self, client, sample_user, generate_test_sessions):
        """Test successful session listing."""
        # Act
        response = client.get(f"/api/v1/sessions/?user_id={sample_user.id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert isinstance(data["sessions"], list)
        assert data["total"] >= 0
        assert data["page"] == 1
        assert data["size"] == 10
    
    @pytest.mark.integration
    def test_list_sessions_with_pagination(self, client, sample_user, generate_test_sessions):
        """Test session listing with pagination."""
        # Act
        response = client.get(f"/api/v1/sessions/?user_id={sample_user.id}&page=1&size=5")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert data["page"] == 1
        assert data["size"] == 5
        assert len(data["sessions"]) <= 5
    
    @pytest.mark.integration
    def test_list_sessions_missing_user_id(self, client):
        """Test session listing without user_id."""
        # Act
        response = client.get("/api/v1/sessions/")
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.integration
    def test_list_sessions_invalid_user_id(self, client):
        """Test session listing with invalid user_id."""
        # Arrange
        invalid_user_id = "invalid-uuid"
        
        # Act
        response = client.get(f"/api/v1/sessions/?user_id={invalid_user_id}")
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.integration
    def test_update_session_success(self, client, sample_interview_session):
        """Test successful session update."""
        # Arrange
        update_data = {
            "status": "completed",
            "completed_questions": 5
        }
        
        # Act
        response = client.put(
            f"/api/v1/sessions/{sample_interview_session.id}",
            json=update_data
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "status" in data
        assert "completed_questions" in data
        assert data["id"] == str(sample_interview_session.id)
        assert data["status"] == update_data["status"]
        assert data["completed_questions"] == update_data["completed_questions"]
    
    @pytest.mark.integration
    def test_update_session_not_found(self, client):
        """Test session update for non-existent session."""
        # Arrange
        non_existent_id = "550e8400-e29b-41d4-a716-446655440999"
        update_data = {
            "status": "completed"
        }
        
        # Act
        response = client.put(
            f"/api/v1/sessions/{non_existent_id}",
            json=update_data
        )
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    @pytest.mark.integration
    def test_update_session_invalid_id(self, client):
        """Test session update with invalid ID format."""
        # Arrange
        invalid_id = "invalid-uuid"
        update_data = {
            "status": "completed"
        }
        
        # Act
        response = client.put(
            f"/api/v1/sessions/{invalid_id}",
            json=update_data
        )
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.integration
    def test_delete_session_success(self, client, sample_interview_session):
        """Test successful session deletion."""
        # Act
        response = client.delete(f"/api/v1/sessions/{sample_interview_session.id}")
        
        # Assert
        assert response.status_code == 204
        
        # Verify session is deleted
        get_response = client.get(f"/api/v1/sessions/{sample_interview_session.id}")
        assert get_response.status_code == 404
    
    @pytest.mark.integration
    def test_delete_session_not_found(self, client):
        """Test session deletion for non-existent session."""
        # Arrange
        non_existent_id = "550e8400-e29b-41d4-a716-446655440999"
        
        # Act
        response = client.delete(f"/api/v1/sessions/{non_existent_id}")
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    @pytest.mark.integration
    def test_delete_session_invalid_id(self, client):
        """Test session deletion with invalid ID format."""
        # Arrange
        invalid_id = "invalid-uuid"
        
        # Act
        response = client.delete(f"/api/v1/sessions/{invalid_id}")
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.integration
    def test_get_session_questions_success(self, client, sample_interview_session, sample_session_question):
        """Test successful session questions retrieval."""
        # Act
        response = client.get(f"/api/v1/sessions/{sample_interview_session.id}/questions")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert "total" in data
        assert isinstance(data["questions"], list)
        assert data["total"] >= 0
    
    @pytest.mark.integration
    def test_get_session_questions_not_found(self, client):
        """Test session questions retrieval for non-existent session."""
        # Arrange
        non_existent_id = "550e8400-e29b-41d4-a716-446655440999"
        
        # Act
        response = client.get(f"/api/v1/sessions/{non_existent_id}/questions")
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    @pytest.mark.integration
    def test_get_session_questions_invalid_id(self, client):
        """Test session questions retrieval with invalid ID format."""
        # Arrange
        invalid_id = "invalid-uuid"
        
        # Act
        response = client.get(f"/api/v1/sessions/{invalid_id}/questions")
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.integration
    def test_add_question_to_session_success(self, client, sample_interview_session, sample_question):
        """Test successful question addition to session."""
        # Arrange
        question_data = {
            "question_id": str(sample_question.id),
            "question_order": 1,
            "session_specific_context": {"role": "senior_developer", "focus": "technical_skills"}
        }
        
        # Act
        response = client.post(
            f"/api/v1/sessions/{sample_interview_session.id}/questions",
            json=question_data
        )
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "session_id" in data
        assert "question_id" in data
        assert "question_order" in data
        assert "session_specific_context" in data
        assert data["session_id"] == str(sample_interview_session.id)
        assert data["question_id"] == str(sample_question.id)
        assert data["question_order"] == question_data["question_order"]
    
    @pytest.mark.integration
    def test_add_question_to_session_not_found(self, client, sample_question):
        """Test question addition to non-existent session."""
        # Arrange
        non_existent_id = "550e8400-e29b-41d4-a716-446655440999"
        question_data = {
            "question_id": str(sample_question.id),
            "question_order": 1
        }
        
        # Act
        response = client.post(
            f"/api/v1/sessions/{non_existent_id}/questions",
            json=question_data
        )
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    @pytest.mark.integration
    def test_add_question_to_session_invalid_question_id(self, client, sample_interview_session):
        """Test question addition with invalid question ID."""
        # Arrange
        invalid_question_id = "invalid-uuid"
        question_data = {
            "question_id": invalid_question_id,
            "question_order": 1
        }
        
        # Act
        response = client.post(
            f"/api/v1/sessions/{sample_interview_session.id}/questions",
            json=question_data
        )
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.integration
    def test_remove_question_from_session_success(self, client, sample_interview_session, sample_session_question):
        """Test successful question removal from session."""
        # Act
        response = client.delete(
            f"/api/v1/sessions/{sample_interview_session.id}/questions/{sample_session_question.id}"
        )
        
        # Assert
        assert response.status_code == 204
        
        # Verify question is removed
        get_response = client.get(f"/api/v1/sessions/{sample_interview_session.id}/questions")
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["total"] == 0
    
    @pytest.mark.integration
    def test_remove_question_from_session_not_found(self, client, sample_interview_session):
        """Test question removal for non-existent session question."""
        # Arrange
        non_existent_id = "550e8400-e29b-41d4-a716-446655440999"
        
        # Act
        response = client.delete(
            f"/api/v1/sessions/{sample_interview_session.id}/questions/{non_existent_id}"
        )
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    @pytest.mark.integration
    def test_remove_question_from_session_invalid_id(self, client, sample_interview_session):
        """Test question removal with invalid ID format."""
        # Arrange
        invalid_id = "invalid-uuid"
        
        # Act
        response = client.delete(
            f"/api/v1/sessions/{sample_interview_session.id}/questions/{invalid_id}"
        )
        
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.integration
    def test_session_creation_with_ai_service_error(self, client, sample_user):
        """Test session creation when AI service fails."""
        # Arrange
        session_data = {
            "role": "Python Developer",
            "job_description": "Looking for Python developer"
        }
        
        mock_ai_client = AsyncMock()
        mock_ai_client.generate_questions.side_effect = Exception("AI service error")
        
        with patch('app.routers.interview.get_ai_client_dependency', return_value=mock_ai_client):
            # Act
            response = client.post(
                f"/api/v1/sessions/?user_id={sample_user.id}",
                json=session_data
            )
            
            # Assert
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
    
    @pytest.mark.integration
    def test_session_creation_with_database_error(self, client, sample_user, mock_ai_client):
        """Test session creation when database fails."""
        # Arrange
        session_data = {
            "role": "Python Developer",
            "job_description": "Looking for Python developer"
        }
        
        with patch('app.routers.interview.get_ai_client_dependency', return_value=mock_ai_client):
            with patch('app.database.connection.get_db') as mock_get_db:
                mock_db = mock_get_db.return_value
                mock_db.add.side_effect = Exception("Database error")
                
                # Act
                response = client.post(
                    f"/api/v1/sessions/?user_id={sample_user.id}",
                    json=session_data
                )
                
                # Assert
                assert response.status_code == 500
                data = response.json()
                assert "detail" in data
