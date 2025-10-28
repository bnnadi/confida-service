"""
Service testing utility to eliminate repetitive testing logic.
"""

from typing import Dict, Any
# Note: AIService removed - using pure microservice architecture

class ServiceTester:
    """Utility class for testing AI services with consistent error handling."""
    
    def __init__(self, ai_client, settings):
        self.ai_client = ai_client
        self.settings = settings
        self.test_data = ("Software Engineer", "We are looking for a software engineer with Python experience.")
    
    async def test_service(self, service_name: str) -> Dict[str, Any]:
        """Test AI service microservice with consistent error handling."""
        try:
            # Test AI service microservice health
            is_healthy = await self.ai_client.health_check()
            if is_healthy:
                return {"status": "success", "service": "ai_service_microservice"}
            else:
                return {"status": "error", "error": "AI service microservice unhealthy"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    async def test_all_services(self) -> Dict[str, Any]:
        """Test AI service microservice."""
        results = {}
        # Test AI service microservice
        results["ai_service_microservice"] = await self.test_service("ai_service_microservice")
        return results
