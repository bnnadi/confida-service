"""
Integration tests for complete API flows.
"""
import pytest
from fastapi.testclient import TestClient

class TestIntegrationFlows:
    """Integration tests for complete interview workflows."""
    
    def test_complete_interview_flow(self, client: TestClient):
        """Test complete interview flow from parsing to analysis."""
        # Step 1: Parse job description
        parse_request = {
            "role": "Senior Python Developer",
            "jobDescription": "We are looking for a Senior Python Developer with 5+ years of experience in Django, Flask, and API development. Strong debugging skills required."
        }
        
        parse_response = client.post("/api/v1/parse-jd", json=parse_request)
        assert parse_response.status_code == 200
        questions = parse_response.json()["questions"]
        assert len(questions) > 0
        
        # Step 2: Analyze answer for first question
        analyze_request = {
            "jobDescription": parse_request["jobDescription"],
            "question": questions[0],
            "answer": "I have 5 years of Python experience working with Django and Flask frameworks. I've built REST APIs and handled complex debugging scenarios."
        }
        
        analyze_response = client.post("/api/v1/analyze-answer", json=analyze_request)
        assert analyze_response.status_code == 200
        analysis = analyze_response.json()
        assert "score" in analysis
        assert "improvements" in analysis
    
    def test_multiple_question_analysis_flow(self, client: TestClient):
        """Test analyzing multiple questions in sequence."""
        parse_request = {
            "role": "Full Stack Developer",
            "jobDescription": "Looking for a Full Stack Developer with React and Node.js experience."
        }
        
        # Generate questions
        parse_response = client.post("/api/v1/parse-jd", json=parse_request)
        assert parse_response.status_code == 200
        questions = parse_response.json()["questions"]
        
        # Analyze multiple answers
        for i, question in enumerate(questions[:3]):
            analyze_request = {
                "jobDescription": parse_request["jobDescription"],
                "question": question,
                "answer": f"This is my answer to question {i+1} about my experience."
            }
            
            response = client.post("/api/v1/analyze-answer", json=analyze_request)
            assert response.status_code == 200
            assert "score" in response.json()
    
    def test_service_fallback_behavior(self, client: TestClient):
        """Test that service parameter is respected."""
        request_data = {
            "role": "Software Engineer",
            "jobDescription": "We need a software engineer with strong coding skills."
        }
        
        # Test with specific service
        response = client.post("/api/v1/parse-jd?service=openai", json=request_data)
        assert response.status_code == 200
        
        # Test without service (should use default)
        response = client.post("/api/v1/parse-jd", json=request_data)
        assert response.status_code == 200
    
    def test_health_check_before_api_calls(self, client: TestClient):
        """Test checking health before making API calls."""
        # Check health
        health_response = client.get("/health")
        assert health_response.status_code == 200
        
        # Check readiness
        ready_response = client.get("/ready")
        assert ready_response.status_code == 200
        
        # Make API call
        request_data = {
            "role": "Developer",
            "jobDescription": "Looking for an experienced developer."
        }
        api_response = client.post("/api/v1/parse-jd", json=request_data)
        assert api_response.status_code == 200
    
    def test_admin_endpoints_flow(self, client: TestClient):
        """Test admin endpoint workflow."""
        # Get services status
        services_response = client.get("/api/v1/admin/services")
        assert services_response.status_code == 200
        
        # Get models
        models_response = client.get("/api/v1/admin/models")
        assert models_response.status_code == 200
        
        # Get rate limits
        limits_response = client.get("/api/v1/admin/rate-limits")
        assert limits_response.status_code == 200
        
        # Get health
        health_response = client.get("/api/v1/admin/health")
        assert health_response.status_code == 200


class TestErrorHandlingFlow:
    """Integration tests for error handling."""
    
    def test_invalid_data_flow(self, client: TestClient):
        """Test flow with invalid data at each step."""
        # Invalid parse request
        invalid_parse = {"role": "", "jobDescription": "x"}
        response = client.post("/api/v1/parse-jd", json=invalid_parse)
        assert response.status_code == 422
        
        # Invalid analyze request
        invalid_analyze = {"jobDescription": "x", "question": "", "answer": "x"}
        response = client.post("/api/v1/analyze-answer", json=invalid_analyze)
        assert response.status_code == 422
    
    def test_malformed_json_requests(self, client: TestClient):
        """Test handling of malformed JSON."""
        response = client.post(
            "/api/v1/parse-jd",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

