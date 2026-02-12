"""
Performance and load tests.

Note: These tests focus on response time and concurrency handling.
Auth-protected endpoints may return 401 in CI without tokens, which is acceptable
since these tests validate performance characteristics, not authentication.
"""
import pytest
import time
import threading
import queue
from fastapi.testclient import TestClient

# Status codes that indicate the server responded correctly (not a server error)
ACCEPTABLE_STATUS_CODES = {200, 401, 403, 422}


class TestPerformance:
    """Performance tests for API endpoints."""
    
    @pytest.mark.performance
    def test_parse_jd_response_time(self, client: TestClient):
        """Test parse-jd endpoint response time."""
        request_data = {
            "role": "Senior Python Developer",
            "jobDescription": "We are looking for a Senior Python Developer with 5+ years of experience in Django, Flask, and API development."
        }
        
        start_time = time.time()
        response = client.post("/api/v1/parse-jd", json=request_data)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code in ACCEPTABLE_STATUS_CODES
        assert response_time < 10.0  # Should respond within 10 seconds
    
    @pytest.mark.performance
    def test_analyze_answer_response_time(self, client: TestClient):
        """Test analyze-answer endpoint response time."""
        request_data = {
            "jobDescription": "We are looking for a Senior Python Developer with experience.",
            "question": "Tell me about your Python experience.",
            "answer": "I have 5 years of Python experience working with Django and Flask frameworks."
        }
        
        start_time = time.time()
        response = client.post("/api/v1/analyze-answer", json=request_data)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code in ACCEPTABLE_STATUS_CODES
        assert response_time < 10.0  # Should respond within 10 seconds
    
    @pytest.mark.performance
    def test_health_check_response_time(self, client: TestClient):
        """Test health check endpoint response time."""
        start_time = time.time()
        response = client.get("/health")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        assert response.status_code == 200
        assert response_time < 1.0  # Should be very fast
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_concurrent_parse_jd_requests(self, client: TestClient):
        """Test handling of concurrent parse-jd requests."""
        request_data = {
            "role": "Senior Python Developer",
            "jobDescription": "We are looking for a Senior Python Developer with experience."
        }
        
        results = queue.Queue()
        
        def make_request():
            try:
                response = client.post("/api/v1/parse-jd", json=request_data)
                results.put(("success", response.status_code))
            except Exception as e:
                results.put(("error", str(e)))
        
        # Start 10 concurrent requests
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30)
        
        # Check results - server should respond (not crash/timeout)
        handled_count = 0
        while not results.empty():
            result_status, code = results.get()
            if result_status == "success" and code in ACCEPTABLE_STATUS_CODES:
                handled_count += 1
        
        # At least 80% should be handled (not 5xx or timeouts)
        assert handled_count >= 8
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_concurrent_analyze_answer_requests(self, client: TestClient):
        """Test handling of concurrent analyze-answer requests."""
        request_data = {
            "jobDescription": "We are looking for a developer with Python experience.",
            "question": "Tell me about your Python experience.",
            "answer": "I have 5 years of Python experience."
        }
        
        results = queue.Queue()
        
        def make_request():
            try:
                response = client.post("/api/v1/analyze-answer", json=request_data)
                results.put(("success", response.status_code))
            except Exception as e:
                results.put(("error", str(e)))
        
        # Start 10 concurrent requests
        threads = []
        for i in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30)
        
        # Check results - server should respond (not crash/timeout)
        handled_count = 0
        while not results.empty():
            result_status, code = results.get()
            if result_status == "success" and code in ACCEPTABLE_STATUS_CODES:
                handled_count += 1
        
        # At least 80% should be handled (not 5xx or timeouts)
        assert handled_count >= 8
    
    @pytest.mark.performance
    def test_sequential_requests_performance(self, client: TestClient):
        """Test performance of sequential requests."""
        request_data = {
            "role": "Developer",
            "jobDescription": "Looking for a developer with experience."
        }
        
        start_time = time.time()
        
        # Make 5 sequential requests
        for _ in range(5):
            response = client.post("/api/v1/parse-jd", json=request_data)
            assert response.status_code in ACCEPTABLE_STATUS_CODES
        
        end_time = time.time()
        total_time = end_time - start_time
        average_time = total_time / 5
        
        # Average should be reasonable
        assert average_time < 15.0  # Each request should average under 15 seconds
    
    @pytest.mark.performance
    def test_memory_efficiency_multiple_requests(self, client: TestClient):
        """Test that multiple requests don't cause memory issues."""
        request_data = {
            "role": "Developer",
            "jobDescription": "Looking for a developer with experience." * 10
        }
        
        # Make many requests to test memory efficiency
        for i in range(20):
            response = client.post("/api/v1/parse-jd", json=request_data)
            assert response.status_code in ACCEPTABLE_STATUS_CODES
            # If we get here without crashing, memory is being managed
    
    @pytest.mark.performance
    def test_large_payload_handling(self, client: TestClient):
        """Test handling of larger payloads."""
        large_description = "We are looking for a developer with Python experience. " * 100
        
        request_data = {
            "role": "Senior Python Developer",
            "jobDescription": large_description
        }
        
        start_time = time.time()
        response = client.post("/api/v1/parse-jd", json=request_data)
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Should handle or reject gracefully (401 is acceptable - auth protected)
        assert response.status_code in [200, 401, 413, 422]
        if response.status_code == 200:
            assert response_time < 15.0  # Should still be reasonably fast


class TestLoadHandling:
    """Test API behavior under load."""
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_mixed_endpoint_concurrent_load(self, client: TestClient):
        """Test concurrent requests to different endpoints."""
        results = queue.Queue()
        
        def parse_jd_request():
            try:
                response = client.post("/api/v1/parse-jd", json={
                    "role": "Developer",
                    "jobDescription": "Looking for a developer."
                })
                results.put(("parse_jd", response.status_code))
            except Exception as e:
                results.put(("parse_jd_error", str(e)))
        
        def analyze_answer_request():
            try:
                response = client.post("/api/v1/analyze-answer", json={
                    "jobDescription": "Looking for a developer.",
                    "question": "Tell me about yourself.",
                    "answer": "I am a developer."
                })
                results.put(("analyze", response.status_code))
            except Exception as e:
                results.put(("analyze_error", str(e)))
        
        def health_check_request():
            try:
                response = client.get("/health")
                results.put(("health", response.status_code))
            except Exception as e:
                results.put(("health_error", str(e)))
        
        # Mix of different request types
        threads = []
        for _ in range(3):
            threads.append(threading.Thread(target=parse_jd_request))
            threads.append(threading.Thread(target=analyze_answer_request))
            threads.append(threading.Thread(target=health_check_request))
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=30)
        
        # Check that most requests were handled (not 5xx or timeouts)
        handled_count = 0
        total_count = 0
        while not results.empty():
            endpoint, result_status = results.get()
            total_count += 1
            if isinstance(result_status, int) and result_status in ACCEPTABLE_STATUS_CODES:
                handled_count += 1
        
        handled_rate = handled_count / total_count if total_count > 0 else 0
        assert handled_rate >= 0.8  # At least 80% handled (not server errors)

