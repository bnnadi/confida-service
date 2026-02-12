"""
Integration tests for interview API endpoints.

Tests the complete flow of interview-related endpoints including
question generation, answer analysis, and session management.
"""
import pytest
from unittest.mock import AsyncMock


class TestInterviewEndpoints:
    """Test cases for interview API endpoints."""
    
    @pytest.mark.integration
    def test_parse_job_description_success(self, client, sample_parse_request, mock_ai_client, override_auth, override_ai_client):
        """Test successful job description parsing."""
        # Arrange
        override_auth({"id": 1, "email": "test@example.com", "is_admin": False})
        override_ai_client(mock_ai_client)
        # Act
        response = client.post("/api/v1/parse-jd", json=sample_parse_request)
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert len(data["questions"]) == 5
    
    @pytest.mark.integration
    def test_parse_job_description_missing_fields(self, client, override_auth):
        """Test job description parsing with missing required fields."""
        # Arrange
        override_auth({"id": 1, "email": "test@example.com", "is_admin": False})
        invalid_request = {
            "role": "Python Developer"
            # Missing jobDescription
        }
        # Act
        response = client.post("/api/v1/parse-jd", json=invalid_request)
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.integration
    def test_parse_job_description_empty_fields(self, client, override_auth):
        """Test job description parsing with empty fields."""
        # Arrange
        override_auth({"id": 1, "email": "test@example.com", "is_admin": False})
        invalid_request = {
            "role": "",
            "jobDescription": ""
        }
        # Act
        response = client.post("/api/v1/parse-jd", json=invalid_request)
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.integration
    def test_analyze_answer_success(
        self, client, sample_analyze_request, mock_ai_client, override_auth, override_ai_client,
        sample_user, sample_interview_session, sample_session_question, sample_question
    ):
        """Test successful answer analysis.
        
        Requires full session setup: sample_question linked to sample_interview_session
        for the user. The analyze endpoint validates question access via DB.
        """
        # Arrange
        override_auth({"id": sample_user.id, "email": sample_user.email, "is_admin": False})
        override_ai_client(mock_ai_client)
        # Act
        response = client.post(
            f"/api/v1/analyze-answer?question_id={sample_question.id}",
            json=sample_analyze_request
        )
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert "analysis" in data
        assert "service_used" in data
    
    @pytest.mark.integration
    def test_analyze_answer_missing_fields(self, client, override_auth):
        """Test answer analysis with missing required fields."""
        # Arrange
        override_auth({"id": 1, "email": "test@example.com", "is_admin": False})
        invalid_request = {
            "jobDescription": "Looking for Python developer",
            "question": "What is your Python experience?"
            # Missing answer
        }
        # Act
        response = client.post("/api/v1/analyze-answer", json=invalid_request)
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.integration
    def test_analyze_answer_empty_answer(self, client, override_auth):
        """Test answer analysis with empty answer."""
        # Arrange
        override_auth({"id": 1, "email": "test@example.com", "is_admin": False})
        invalid_request = {
            "jobDescription": "Looking for Python developer",
            "question": "What is your Python experience?",
            "answer": ""
        }
        # Act
        response = client.post("/api/v1/analyze-answer", json=invalid_request)
        # Assert
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.integration
    def test_health_check(self, client, mock_ai_client, override_ai_client):
        """Test getting available AI services."""
        # Arrange
        override_ai_client(mock_ai_client)
        # Act
        response = client.get("/api/v1/services")
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "ai_service_microservice" in data
        assert "status" in data
        assert data["status"] == "healthy"
        assert "url" in data["ai_service_microservice"]
    
    # Note: list_models tests removed - endpoint doesn't exist in pure microservice architecture
    
    @pytest.mark.integration
    def test_parse_job_description_with_preferred_service(self, client, sample_parse_request, mock_ai_client, override_auth, override_ai_client):
        """Test job description parsing with preferred service."""
        # Arrange
        override_auth({"id": 1, "email": "test@example.com", "is_admin": False})
        override_ai_client(mock_ai_client)
        sample_parse_request["preferredService"] = "anthropic"
        # Act
        response = client.post("/api/v1/parse-jd", json=sample_parse_request)
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
    
    @pytest.mark.integration
    def test_analyze_answer_with_preferred_service(
        self, client, sample_analyze_request, mock_ai_client, override_auth, override_ai_client,
        sample_user, sample_question, sample_interview_session, sample_session_question
    ):
        """Test answer analysis with preferred service."""
        # Arrange
        override_auth({"id": sample_user.id, "email": sample_user.email, "is_admin": False})
        override_ai_client(mock_ai_client)
        sample_analyze_request["preferredService"] = "anthropic"
        # Act
        response = client.post(
            f"/api/v1/analyze-answer?question_id={sample_question.id}",
            json=sample_analyze_request
        )
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert "service_used" in data
    
    @pytest.mark.integration
    def test_parse_job_description_large_input(self, client, mock_ai_client, override_auth, override_ai_client):
        """Test job description parsing with large input."""
        # Arrange
        override_auth({"id": 1, "email": "test@example.com", "is_admin": False})
        override_ai_client(mock_ai_client)
        large_request = {
            "role": "Senior Python Developer",
            "jobDescription": "We are looking for a Senior Python Developer with extensive experience in web development, API design, database optimization, microservices architecture, cloud computing, DevOps practices, and team leadership. The ideal candidate should have strong debugging skills, experience with performance optimization, and the ability to mentor junior developers. " * 10  # Large job description
        }
        # Act
        response = client.post("/api/v1/parse-jd", json=large_request)
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert len(data["questions"]) > 0
    
    @pytest.mark.integration
    def test_analyze_answer_large_input(
        self, client, mock_ai_client, override_auth, override_ai_client,
        sample_user, sample_question, sample_interview_session, sample_session_question
    ):
        """Test answer analysis with large input."""
        # Arrange
        override_auth({"id": sample_user.id, "email": sample_user.email, "is_admin": False})
        override_ai_client(mock_ai_client)
        large_request = {
            "jobDescription": "We are looking for a Senior Python Developer with extensive experience.",
            "question": "What is your experience with Python web frameworks?",
            "answer": "I have extensive experience with Python web frameworks including Django, Flask, FastAPI, and Pyramid. I've worked on large-scale applications with millions of users, implemented complex business logic, optimized database queries, and designed RESTful APIs. " * 5  # Large answer
        }
        # Act
        response = client.post(
            f"/api/v1/analyze-answer?question_id={sample_question.id}",
            json=large_request
        )
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert "improvements" in data
    
    @pytest.mark.integration
    def test_parse_job_description_special_characters(self, client, mock_ai_client, override_auth, override_ai_client):
        """Test job description parsing with special characters."""
        # Arrange
        override_auth({"id": 1, "email": "test@example.com", "is_admin": False})
        override_ai_client(mock_ai_client)
        special_request = {
            "role": "Python Developer (Senior Level)",
            "jobDescription": "We're looking for a Python Developer with 5+ years of experience. Must have: Django/Flask, PostgreSQL, Redis, Docker, AWS. Salary: $80k-$120k. Benefits: Health, Dental, 401k."
        }
        # Act
        response = client.post("/api/v1/parse-jd", json=special_request)
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert len(data["questions"]) > 0
    
    @pytest.mark.integration
    def test_analyze_answer_special_characters(
        self, client, mock_ai_client, override_auth, override_ai_client,
        sample_user, sample_question, sample_interview_session, sample_session_question
    ):
        """Test answer analysis with special characters."""
        # Arrange
        override_auth({"id": sample_user.id, "email": sample_user.email, "is_admin": False})
        override_ai_client(mock_ai_client)
        special_request = {
            "jobDescription": "We're looking for a Python Developer with 5+ years of experience.",
            "question": "What's your experience with Python web frameworks?",
            "answer": "I've worked with Django, Flask, and FastAPI. I've built APIs that handle 10k+ requests/second and used PostgreSQL, Redis, and Docker. I'm familiar with AWS services like EC2, S3, and RDS."
        }
        # Act
        response = client.post(
            f"/api/v1/analyze-answer?question_id={sample_question.id}",
            json=special_request
        )
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert "improvements" in data
    
    @pytest.mark.integration
    def test_parse_job_description_unicode(self, client, mock_ai_client, override_auth, override_ai_client):
        """Test job description parsing with unicode characters."""
        # Arrange
        override_auth({"id": 1, "email": "test@example.com", "is_admin": False})
        override_ai_client(mock_ai_client)
        unicode_request = {
            "role": "Python Developer",
            "jobDescription": "We're looking for a Python Developer with experience in web development, API design, and database optimization. The ideal candidate should have strong problem-solving skills and be able to work in a fast-paced environment. 🚀"
        }
        # Act
        response = client.post("/api/v1/parse-jd", json=unicode_request)
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "questions" in data
        assert len(data["questions"]) > 0
    
    @pytest.mark.integration
    def test_analyze_answer_unicode(
        self, client, mock_ai_client, override_auth, override_ai_client,
        sample_user, sample_question, sample_interview_session, sample_session_question
    ):
        """Test answer analysis with unicode characters."""
        # Arrange
        override_auth({"id": sample_user.id, "email": sample_user.email, "is_admin": False})
        override_ai_client(mock_ai_client)
        unicode_request = {
            "jobDescription": "We're looking for a Python Developer with experience in web development.",
            "question": "What's your experience with Python web frameworks?",
            "answer": "I have 5 years of experience with Django and Flask. I've built several web applications and APIs. I'm passionate about clean code and best practices! 💻"
        }
        # Act
        response = client.post(
            f"/api/v1/analyze-answer?question_id={sample_question.id}",
            json=unicode_request
        )
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "score" in data
        assert "improvements" in data
    
    @pytest.mark.integration
    def test_parse_job_description_malformed_json(self, client, override_auth):
        """Test job description parsing with malformed JSON."""
        # Arrange
        override_auth({"id": 1, "email": "test@example.com", "is_admin": False})
        malformed_json = '{"role": "Python Developer", "jobDescription": "Looking for Python developer"'  # Missing closing brace
        # Act
        response = client.post(
            "/api/v1/parse-jd",
            data=malformed_json,
            headers={"Content-Type": "application/json"}
        )
        # Assert
        assert response.status_code == 422
    
    @pytest.mark.integration
    def test_analyze_answer_malformed_json(self, client, override_auth):
        """Test answer analysis with malformed JSON."""
        # Arrange
        override_auth({"id": 1, "email": "test@example.com", "is_admin": False})
        malformed_json = '{"jobDescription": "Looking for Python developer", "question": "What is your experience?", "answer": "I have 5 years of experience"'  # Missing closing brace
        # Act
        response = client.post(
            "/api/v1/analyze-answer",
            data=malformed_json,
            headers={"Content-Type": "application/json"}
        )
        # Assert
        assert response.status_code == 422
    
    @pytest.mark.integration
    def test_parse_job_description_wrong_content_type(self, client, override_auth):
        """Test job description parsing with wrong content type."""
        # Arrange
        override_auth({"id": 1, "email": "test@example.com", "is_admin": False})
        request_data = {
            "role": "Python Developer",
            "jobDescription": "Looking for Python developer"
        }
        # Act
        response = client.post(
            "/api/v1/parse-jd",
            data=request_data,
            headers={"Content-Type": "text/plain"}
        )
        # Assert
        assert response.status_code == 422
    
    @pytest.mark.integration
    def test_analyze_answer_wrong_content_type(self, client, override_auth):
        """Test answer analysis with wrong content type."""
        # Arrange
        override_auth({"id": 1, "email": "test@example.com", "is_admin": False})
        request_data = {
            "jobDescription": "Looking for Python developer",
            "question": "What is your experience?",
            "answer": "I have 5 years of experience"
        }
        # Act
        response = client.post(
            "/api/v1/analyze-answer",
            data=request_data,
            headers={"Content-Type": "text/plain"}
        )
        # Assert
        assert response.status_code == 422
    
    @pytest.mark.integration
    def test_parse_job_description_ai_service_error(self, client, sample_parse_request, override_auth, override_ai_client):
        """Test job description parsing when AI service fails."""
        # Arrange
        mock_ai_client = AsyncMock()
        mock_ai_client.generate_questions_structured = AsyncMock(side_effect=Exception("AI service error"))
        override_auth({"id": 1, "email": "test@example.com", "is_admin": False})
        override_ai_client(mock_ai_client)
        # Act
        response = client.post("/api/v1/parse-jd", json=sample_parse_request)
        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.integration
    def test_analyze_answer_ai_service_error(
        self, client, sample_analyze_request, override_auth, override_ai_client,
        sample_user, sample_question, sample_interview_session, sample_session_question
    ):
        """Test answer analysis when AI service fails."""
        # Arrange
        mock_ai_client = AsyncMock()
        mock_ai_client.analyze_answer = AsyncMock(side_effect=Exception("AI service error"))
        override_auth({"id": sample_user.id, "email": sample_user.email, "is_admin": False})
        override_ai_client(mock_ai_client)
        # Act
        response = client.post(
            f"/api/v1/analyze-answer?question_id={sample_question.id}",
            json=sample_analyze_request
        )
        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.integration
    def test_get_services_ai_service_error(self, client, override_ai_client):
        """Test getting services when AI service fails."""
        # Arrange
        mock_ai_client = AsyncMock()
        mock_ai_client.health_check = AsyncMock(side_effect=Exception("AI service error"))
        override_ai_client(mock_ai_client)
        # Act
        response = client.get("/api/v1/services")
        # Assert
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
    
    # Note: list_models error test removed - endpoint doesn't exist in pure microservice architecture
