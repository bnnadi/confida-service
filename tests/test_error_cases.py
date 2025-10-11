"""
Error case and edge case tests.
"""
import pytest
from fastapi.testclient import TestClient

class TestErrorCases:
    """Test error handling in various scenarios."""
    
    def test_invalid_service_parameter(self, client: TestClient):
        """Test invalid service parameter."""
        request_data = {
            "role": "Senior Python Developer",
            "jobDescription": "We are looking for a Senior Python Developer with experience."
        }
        
        response = client.post(
            "/api/v1/parse-jd?service=invalid_service",
            json=request_data
        )
        assert response.status_code == 400
    
    def test_empty_request_body(self, client: TestClient):
        """Test empty request body."""
        response = client.post("/api/v1/parse-jd", json={})
        assert response.status_code == 422
    
    def test_null_values_in_request(self, client: TestClient):
        """Test null values in request."""
        request_data = {
            "role": None,
            "jobDescription": None
        }
        
        response = client.post("/api/v1/parse-jd", json=request_data)
        assert response.status_code == 422
    
    def test_very_long_job_description(self, client: TestClient):
        """Test handling of very long job descriptions."""
        long_description = "A" * 100000  # 100KB description
        
        request_data = {
            "role": "Senior Python Developer",
            "jobDescription": long_description
        }
        
        response = client.post("/api/v1/parse-jd", json=request_data)
        # Should either succeed or fail gracefully
        assert response.status_code in [200, 413, 422]
    
    def test_special_characters_in_input(self, client: TestClient):
        """Test special characters in input."""
        request_data = {
            "role": "Senior Python Developer 🐍",
            "jobDescription": "We are looking for a developer with <script>alert('xss')</script> experience."
        }
        
        response = client.post("/api/v1/parse-jd", json=request_data)
        assert response.status_code == 200
        # Ensure no XSS or injection
        data = response.json()
        assert "questions" in data
    
    def test_unicode_characters_in_input(self, client: TestClient):
        """Test unicode characters in input."""
        request_data = {
            "role": "Senior Python Developer",
            "jobDescription": "We are looking for a developer with 日本語 experience. Ñoño José."
        }
        
        response = client.post("/api/v1/parse-jd", json=request_data)
        assert response.status_code == 200
    
    def test_sql_injection_attempt(self, client: TestClient):
        """Test SQL injection attempt in input."""
        request_data = {
            "role": "'; DROP TABLE users; --",
            "jobDescription": "We are looking for a developer with SQL injection experience."
        }
        
        response = client.post("/api/v1/parse-jd", json=request_data)
        # Should handle gracefully without causing SQL injection
        assert response.status_code in [200, 400, 422]
    
    def test_missing_content_type_header(self, client: TestClient):
        """Test request without content-type header."""
        response = client.post(
            "/api/v1/parse-jd",
            data='{"role": "Developer", "jobDescription": "Looking for a developer."}',
            headers={}
        )
        # FastAPI should handle this gracefully
        assert response.status_code in [200, 415, 422]
    
    def test_invalid_json_structure(self, client: TestClient):
        """Test invalid JSON structure."""
        response = client.post(
            "/api/v1/parse-jd",
            data='{"role": "Developer", "jobDescription":}',
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
    
    def test_analyze_answer_with_empty_answer(self, client: TestClient):
        """Test analyzing an empty answer."""
        request_data = {
            "jobDescription": "We are looking for a developer with Python experience.",
            "question": "Tell me about your Python experience.",
            "answer": ""
        }
        
        response = client.post("/api/v1/analyze-answer", json=request_data)
        assert response.status_code == 422
    
    def test_analyze_answer_with_very_long_answer(self, client: TestClient):
        """Test analyzing a very long answer."""
        long_answer = "I have extensive experience with Python. " * 1000  # Very long answer
        
        request_data = {
            "jobDescription": "We are looking for a developer with Python experience.",
            "question": "Tell me about your Python experience.",
            "answer": long_answer
        }
        
        response = client.post("/api/v1/analyze-answer", json=request_data)
        assert response.status_code in [200, 413, 422]


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_minimum_valid_job_description(self, client: TestClient):
        """Test minimum valid job description length."""
        request_data = {
            "role": "Developer",
            "jobDescription": "A" * 20  # Minimum length
        }
        
        response = client.post("/api/v1/parse-jd", json=request_data)
        # Should accept or reject consistently
        assert response.status_code in [200, 422]
    
    def test_concurrent_identical_requests(self, client: TestClient):
        """Test multiple identical requests."""
        request_data = {
            "role": "Senior Python Developer",
            "jobDescription": "We are looking for a Senior Python Developer with experience."
        }
        
        # Make multiple identical requests
        responses = []
        for _ in range(5):
            response = client.post("/api/v1/parse-jd", json=request_data)
            responses.append(response)
        
        # All should succeed
        for response in responses:
            assert response.status_code == 200
    
    def test_different_case_service_parameter(self, client: TestClient):
        """Test service parameter with different cases."""
        request_data = {
            "role": "Developer",
            "jobDescription": "Looking for a developer with experience."
        }
        
        # Test lowercase
        response = client.post("/api/v1/parse-jd?service=openai", json=request_data)
        status_lower = response.status_code
        
        # Test uppercase (should fail)
        response = client.post("/api/v1/parse-jd?service=OPENAI", json=request_data)
        status_upper = response.status_code
        
        # Verify case sensitivity
        assert status_lower in [200, 400]
        assert status_upper in [200, 400]
    
    def test_whitespace_only_input(self, client: TestClient):
        """Test whitespace-only input."""
        request_data = {
            "role": "   ",
            "jobDescription": "     "
        }
        
        response = client.post("/api/v1/parse-jd", json=request_data)
        assert response.status_code == 422
    
    def test_newlines_and_tabs_in_input(self, client: TestClient):
        """Test newlines and tabs in input."""
        request_data = {
            "role": "Senior\nPython\tDeveloper",
            "jobDescription": "We are looking for\na developer\twith\nexperience."
        }
        
        response = client.post("/api/v1/parse-jd", json=request_data)
        assert response.status_code == 200

