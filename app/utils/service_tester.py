"""
Service testing utility to eliminate repetitive testing logic.
"""

from typing import Dict, Any
from app.services.hybrid_ai_service import HybridAIService


class ServiceTester:
    """Utility class for testing AI services with consistent error handling."""
    
    def __init__(self, ai_service: HybridAIService, settings):
        self.ai_service = ai_service
        self.settings = settings
        self.test_data = ("Software Engineer", "We are looking for a software engineer with Python experience.")
    
    def test_service(self, service_name: str) -> Dict[str, Any]:
        """Test a single service with consistent error handling."""
        try:
            test_response = self.ai_service.generate_interview_questions(
                *self.test_data,
                preferred_service=service_name
            )
            return {"status": "success", "questions_count": len(test_response.questions)}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def test_all_services(self) -> Dict[str, Any]:
        """Test all configured services."""
        results = {}
        services = ["ollama", "openai", "anthropic"]
        
        for service in services:
            if getattr(self.settings, f"is_{service}_configured", False):
                results[service] = self.test_service(service)
        
        return results
