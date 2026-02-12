"""
Integration tests for Question Bank API endpoints.

Tests the complete flow of question bank management endpoints including
CRUD operations, search, analytics, and admin functionality.
"""
import pytest
from fastapi.testclient import TestClient
from app.database.models import Question
import uuid


class TestQuestionBankEndpoints:
    """Test cases for Question Bank API endpoints."""
    
    @pytest.mark.integration
    def test_create_question_success(self, client, admin_user, override_admin_auth, db_session):
        """Test successful question creation."""
        override_admin_auth({"id": admin_user.id, "email": admin_user.email, "is_admin": True, "role": "admin"})
        question_data = {
            "question_text": "What is Python?",
            "category": "technical",
            "difficulty_level": "medium",
            "compatible_roles": ["Python Developer"],
            "required_skills": ["Python"],
            "industry_tags": ["tech"]
        }
        
        response = client.post("/api/v1/questions", json=question_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["question_text"] == question_data["question_text"]
        assert data["category"] == question_data["category"]
        assert data["difficulty_level"] == question_data["difficulty_level"]
        assert "id" in data
        assert "created_at" in data
    
    @pytest.mark.integration
    def test_create_question_unauthorized(self, client):
        """Test question creation without admin auth."""
        question_data = {
            "question_text": "What is Python?",
            "category": "technical"
        }
        
        response = client.post("/api/v1/questions", json=question_data)
        assert response.status_code == 401
    
    @pytest.mark.integration
    def test_create_question_duplicate(self, client, admin_user, override_admin_auth, db_session):
        """Test creating duplicate question."""
        override_admin_auth({"id": admin_user.id, "email": admin_user.email, "is_admin": True, "role": "admin"})
        question_data = {
            "question_text": "What is Python?",
            "category": "technical"
        }
        
        # Create first question
        response1 = client.post("/api/v1/questions", json=question_data)
        assert response1.status_code == 201
        
        # Try to create duplicate
        response2 = client.post("/api/v1/questions", json=question_data)
        assert response2.status_code == 400
    
    @pytest.mark.integration
    def test_get_questions(self, client, db_session, sample_question):
        """Test getting list of questions."""
        response = client.get("/api/v1/questions")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        assert "id" in data[0]
        assert "question_text" in data[0]
    
    @pytest.mark.integration
    def test_get_questions_with_filters(self, client, db_session, sample_question):
        """Test getting questions with filters."""
        response = client.get(
            "/api/v1/questions",
            params={"category": "technical", "limit": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert data[0]["category"] == "technical"
    
    @pytest.mark.integration
    def test_get_question_by_id(self, client, db_session, sample_question):
        """Test getting a specific question."""
        question_id = str(sample_question.id)
        response = client.get(f"/api/v1/questions/{question_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == question_id
        assert data["question_text"] == sample_question.question_text
    
    @pytest.mark.integration
    def test_get_question_not_found(self, client):
        """Test getting non-existent question."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/questions/{fake_id}")
        assert response.status_code == 404
    
    @pytest.mark.integration
    def test_update_question(self, client, admin_user, override_admin_auth, db_session, sample_question):
        """Test updating a question."""
        override_admin_auth({"id": admin_user.id, "email": admin_user.email, "is_admin": True, "role": "admin"})
        question_id = str(sample_question.id)
        update_data = {
            "category": "updated_category",
            "difficulty_level": "hard"
        }
        
        response = client.put(f"/api/v1/questions/{question_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "updated_category"
        assert data["difficulty_level"] == "hard"
    
    @pytest.mark.integration
    def test_delete_question(self, client, admin_user, override_admin_auth, db_session):
        """Test deleting a question."""
        override_admin_auth({"id": admin_user.id, "email": admin_user.email, "is_admin": True, "role": "admin"})
        # Create a question first
        question = Question(
            question_text="Test question to delete",
            category="test",
            difficulty_level="easy"
        )
        db_session.add(question)
        db_session.commit()
        
        question_id = str(question.id)
        response = client.delete(f"/api/v1/questions/{question_id}")
        
        assert response.status_code == 204
        
        # Verify it's deleted
        get_response = client.get(f"/api/v1/questions/{question_id}")
        assert get_response.status_code == 404
    
    @pytest.mark.integration
    def test_search_questions(self, client, db_session, sample_question):
        """Test searching questions."""
        response = client.get(
            "/api/v1/questions/search",
            params={"query": "Python", "limit": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.integration
    def test_get_question_suggestions(self, client, db_session, sample_question):
        """Test getting question suggestions."""
        response = client.get(
            "/api/v1/questions/suggestions",
            params={
                "role": "Python Developer",
                "job_description": "Looking for Python developer with Django experience",
                "limit": 5
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    @pytest.mark.integration
    def test_get_question_performance(self, client, db_session, sample_question):
        """Test getting question performance analytics."""
        question_id = str(sample_question.id)
        response = client.get(
            "/api/v1/questions/analytics/performance",
            params={"question_id": question_id, "time_period": "30d"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_uses" in data
        assert "time_period" in data
    
    @pytest.mark.integration
    def test_get_usage_stats(self, client, db_session):
        """Test getting usage statistics."""
        response = client.get(
            "/api/v1/questions/analytics/usage",
            params={"time_period": "30d"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "total_questions" in data
        assert "total_uses" in data
        assert "usage_by_category" in data
    
    @pytest.mark.integration
    def test_get_system_overview(self, client, db_session):
        """Test getting system overview."""
        response = client.get("/api/v1/questions/analytics/overview")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_questions" in data
        assert "questions_by_category" in data
        assert "questions_by_difficulty" in data
    
    @pytest.mark.integration
    def test_bulk_import_questions(self, client, admin_user, override_admin_auth, db_session):
        """Test bulk importing questions."""
        override_admin_auth({"id": admin_user.id, "email": admin_user.email, "is_admin": True, "role": "admin"})
        questions_data = [
            {
                "question_text": "Question 1",
                "category": "technical",
                "difficulty_level": "easy"
            },
            {
                "question_text": "Question 2",
                "category": "behavioral",
                "difficulty_level": "medium"
            }
        ]
        
        response = client.post("/api/v1/questions/admin/bulk-import", json=questions_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "imported_count" in data
        assert "failed_count" in data
    
    @pytest.mark.integration
    def test_quality_check(self, client, admin_user, override_admin_auth, db_session):
        """Test running quality check."""
        override_admin_auth({"id": admin_user.id, "email": admin_user.email, "is_admin": True, "role": "admin"})
        response = client.post("/api/v1/questions/admin/quality-check")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_questions" in data
        assert "issues_found" in data
        assert "issues" in data
        assert "recommendations" in data

