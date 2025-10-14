"""
Integration tests for interview API endpoints.

Tests the complete flow of interview-related endpoints including
question generation, answer analysis, and session management.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import json


class TestInterviewEndpoints:
    """Test cases for interview API endpoints."""
    
    @pytest.mark.integration
    def test_parse_job_description_success(self, client, sample_parse_request, mock_ai_service):
        """Test successful job description parsing."""
        # Arrange
        with patch('app.routers.interview.get_ai_service', return_value=mock_ai_service):
            # Act
            response = client.post("/api/v1/parse-jd", json=sample_parse_request)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "questions" in data
            assert len(data["questions"]) == 5
            assert "service_used" in data
            assert "timestamp" in data
            assert data["service_used"] == "openai"
    
    @pytest.mark.integration
    def test_parse_job_description_missing_fields(self, client):
        """Test job description parsing with missing required fields."""
        # Arrange
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
    def test_parse_job_description_empty_fields(self, client):
        """Test job description parsing with empty fields."""
        # Arrange
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
    def test_analyze_answer_success(self, client, sample_analyze_request, mock_ai_service):
        """Test successful answer analysis."""
        # Arrange
        with patch('app.routers.interview.get_ai_service', return_value=mock_ai_service):
            # Act
            response = client.post("/api/v1/analyze-answer", json=sample_analyze_request)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "score" in data
            assert "missingKeywords" in data
            assert "improvements" in data
            assert "idealAnswer" in data
            assert "service_used" in data
            assert "timestamp" in data
            
            # Check score structure
            score = data["score"]
            assert "clarity" in score
            assert "confidence" in score
            assert "relevance" in score
            assert "overall" in score
            assert all(0 <= v <= 10 for v in score.values())
    
    @pytest.mark.integration
    def test_analyze_answer_missing_fields(self, client):
        """Test answer analysis with missing required fields."""
        # Arrange
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
    def test_analyze_answer_empty_answer(self, client):
        """Test answer analysis with empty answer."""
        # Arrange
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
    def test_get_available_services(self, client, mock_ai_service):
        """Test getting available AI services."""
        # Arrange
        with patch('app.routers.interview.get_ai_service', return_value=mock_ai_service):
            # Act
            response = client.get("/api/v1/services")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "available_services" in data
            assert "service_priority" in data
            assert "service_status" in data
            assert "question_bank_stats" in data
            
            # Check service status
            service_status = data["service_status"]
            assert "openai" in service_status
            assert "anthropic" in service_status
            assert "ollama" in service_status
            
            # Check question bank stats
            question_bank_stats = data["question_bank_stats"]
            assert "total_questions" in question_bank_stats
            assert "questions_by_category" in question_bank_stats
            assert "questions_by_difficulty" in question_bank_stats
    
    @pytest.mark.integration
    def test_list_models(self, client, mock_ai_service):
        """Test listing available models."""
        # Arrange
        with patch('app.routers.interview.get_ai_service', return_value=mock_ai_service):
            # Act
            response = client.get("/api/v1/models")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "models" in data
            assert "default_models" in data
            
            # Check models structure
            models = data["models"]
            assert "openai" in models
            assert "anthropic" in models
            assert "ollama" in models
            
            # Check default models
            default_models = data["default_models"]
            assert "openai" in default_models
            assert "anthropic" in default_models
            assert "ollama" in default_models
    
    @pytest.mark.integration
    def test_list_models_with_service_filter(self, client, mock_ai_service):
        """Test listing models for specific service."""
        # Arrange
        with patch('app.routers.interview.get_ai_service', return_value=mock_ai_service):
            # Act
            response = client.get("/api/v1/models?service=openai")
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "models" in data
            assert "default_models" in data
    
    @pytest.mark.integration
    def test_parse_job_description_with_preferred_service(self, client, sample_parse_request, mock_ai_service):
        """Test job description parsing with preferred service."""
        # Arrange
        sample_parse_request["preferredService"] = "anthropic"
        
        with patch('app.routers.interview.get_ai_service', return_value=mock_ai_service):
            # Act
            response = client.post("/api/v1/parse-jd", json=sample_parse_request)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "questions" in data
            assert "service_used" in data
    
    @pytest.mark.integration
    def test_analyze_answer_with_preferred_service(self, client, sample_analyze_request, mock_ai_service):
        """Test answer analysis with preferred service."""
        # Arrange
        sample_analyze_request["preferredService"] = "anthropic"
        
        with patch('app.routers.interview.get_ai_service', return_value=mock_ai_service):
            # Act
            response = client.post("/api/v1/analyze-answer", json=sample_analyze_request)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "score" in data
            assert "service_used" in data
    
    @pytest.mark.integration
    def test_parse_job_description_large_input(self, client, mock_ai_service):
        """Test job description parsing with large input."""
        # Arrange
        large_request = {
            "role": "Senior Python Developer",
            "jobDescription": "We are looking for a Senior Python Developer with extensive experience in web development, API design, database optimization, microservices architecture, cloud computing, DevOps practices, and team leadership. The ideal candidate should have strong debugging skills, experience with performance optimization, and the ability to mentor junior developers. " * 10  # Large job description
        }
        
        with patch('app.routers.interview.get_ai_service', return_value=mock_ai_service):
            # Act
            response = client.post("/api/v1/parse-jd", json=large_request)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "questions" in data
            assert len(data["questions"]) > 0
    
    @pytest.mark.integration
    def test_analyze_answer_large_input(self, client, mock_ai_service):
        """Test answer analysis with large input."""
        # Arrange
        large_request = {
            "jobDescription": "We are looking for a Senior Python Developer with extensive experience.",
            "question": "What is your experience with Python web frameworks?",
            "answer": "I have extensive experience with Python web frameworks including Django, Flask, FastAPI, and Pyramid. I've worked on large-scale applications with millions of users, implemented complex business logic, optimized database queries, and designed RESTful APIs. " * 5  # Large answer
        }
        
        with patch('app.routers.interview.get_ai_service', return_value=mock_ai_service):
            # Act
            response = client.post("/api/v1/analyze-answer", json=large_request)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "score" in data
            assert "improvements" in data
    
    @pytest.mark.integration
    def test_parse_job_description_special_characters(self, client, mock_ai_service):
        """Test job description parsing with special characters."""
        # Arrange
        special_request = {
            "role": "Python Developer (Senior Level)",
            "jobDescription": "We're looking for a Python Developer with 5+ years of experience. Must have: Django/Flask, PostgreSQL, Redis, Docker, AWS. Salary: $80k-$120k. Benefits: Health, Dental, 401k."
        }
        
        with patch('app.routers.interview.get_ai_service', return_value=mock_ai_service):
            # Act
            response = client.post("/api/v1/parse-jd", json=special_request)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "questions" in data
            assert len(data["questions"]) > 0
    
    @pytest.mark.integration
    def test_analyze_answer_special_characters(self, client, mock_ai_service):
        """Test answer analysis with special characters."""
        # Arrange
        special_request = {
            "jobDescription": "We're looking for a Python Developer with 5+ years of experience.",
            "question": "What's your experience with Python web frameworks?",
            "answer": "I've worked with Django, Flask, and FastAPI. I've built APIs that handle 10k+ requests/second and used PostgreSQL, Redis, and Docker. I'm familiar with AWS services like EC2, S3, and RDS."
        }
        
        with patch('app.routers.interview.get_ai_service', return_value=mock_ai_service):
            # Act
            response = client.post("/api/v1/analyze-answer", json=special_request)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "score" in data
            assert "improvements" in data
    
    @pytest.mark.integration
    def test_parse_job_description_unicode(self, client, mock_ai_service):
        """Test job description parsing with unicode characters."""
        # Arrange
        unicode_request = {
            "role": "Python Developer",
            "jobDescription": "We're looking for a Python Developer with experience in web development, API design, and database optimization. The ideal candidate should have strong problem-solving skills and be able to work in a fast-paced environment. 🚀"
        }
        
        with patch('app.routers.interview.get_ai_service', return_value=mock_ai_service):
            # Act
            response = client.post("/api/v1/parse-jd", json=unicode_request)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "questions" in data
            assert len(data["questions"]) > 0
    
    @pytest.mark.integration
    def test_analyze_answer_unicode(self, client, mock_ai_service):
        """Test answer analysis with unicode characters."""
        # Arrange
        unicode_request = {
            "jobDescription": "We're looking for a Python Developer with experience in web development.",
            "question": "What's your experience with Python web frameworks?",
            "answer": "I have 5 years of experience with Django and Flask. I've built several web applications and APIs. I'm passionate about clean code and best practices! 💻"
        }
        
        with patch('app.routers.interview.get_ai_service', return_value=mock_ai_service):
            # Act
            response = client.post("/api/v1/analyze-answer", json=unicode_request)
            
            # Assert
            assert response.status_code == 200
            data = response.json()
            assert "score" in data
            assert "improvements" in data
    
    @pytest.mark.integration
    def test_parse_job_description_malformed_json(self, client):
        """Test job description parsing with malformed JSON."""
        # Arrange
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
    def test_analyze_answer_malformed_json(self, client):
        """Test answer analysis with malformed JSON."""
        # Arrange
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
    def test_parse_job_description_wrong_content_type(self, client):
        """Test job description parsing with wrong content type."""
        # Arrange
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
    def test_analyze_answer_wrong_content_type(self, client):
        """Test answer analysis with wrong content type."""
        # Arrange
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
    def test_parse_job_description_ai_service_error(self, client, sample_parse_request):
        """Test job description parsing when AI service fails."""
        # Arrange
        mock_ai_service = AsyncMock()
        mock_ai_service.generate_interview_questions.side_effect = Exception("AI service error")
        
        with patch('app.routers.interview.get_ai_service', return_value=mock_ai_service):
            # Act
            response = client.post("/api/v1/parse-jd", json=sample_parse_request)
            
            # Assert
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
    
    @pytest.mark.integration
    def test_analyze_answer_ai_service_error(self, client, sample_analyze_request):
        """Test answer analysis when AI service fails."""
        # Arrange
        mock_ai_service = AsyncMock()
        mock_ai_service.analyze_answer.side_effect = Exception("AI service error")
        
        with patch('app.routers.interview.get_ai_service', return_value=mock_ai_service):
            # Act
            response = client.post("/api/v1/analyze-answer", json=sample_analyze_request)
            
            # Assert
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
    
    @pytest.mark.integration
    def test_get_services_ai_service_error(self, client):
        """Test getting services when AI service fails."""
        # Arrange
        mock_ai_service = AsyncMock()
        mock_ai_service.get_available_services.side_effect = Exception("AI service error")
        
        with patch('app.routers.interview.get_ai_service', return_value=mock_ai_service):
            # Act
            response = client.get("/api/v1/services")
            
            # Assert
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
    
    @pytest.mark.integration
    def test_list_models_ai_service_error(self, client):
        """Test listing models when AI service fails."""
        # Arrange
        mock_ai_service = AsyncMock()
        mock_ai_service.list_models.side_effect = Exception("AI service error")
        
        with patch('app.routers.interview.get_ai_service', return_value=mock_ai_service):
            # Act
            response = client.get("/api/v1/models")
            
            # Assert
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
