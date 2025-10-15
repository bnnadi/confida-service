"""
Base Agent Class

This module provides a base class for all analysis agents to eliminate code duplication
and provide consistent functionality across different agent types.
"""
from typing import Dict, Any
from abc import ABC, abstractmethod
from app.utils.logger import get_logger

logger = get_logger(__name__)

class BaseAgent(ABC):
    """Base class for all analysis agents."""
    
    def __init__(self, name: str):
        self.name = name
    
    async def health_check(self) -> Dict[str, Any]:
        """Standard health check implementation."""
        try:
            test_analysis = await self._run_health_test()
            return {
                "healthy": True,
                "agent_name": self.name,
                "test_score": test_analysis.score,
                "confidence": test_analysis.confidence
            }
        except Exception as e:
            logger.error(f"Health check failed for {self.name}: {e}")
            return {
                "healthy": False,
                "agent_name": self.name,
                "error": str(e)
            }
    
    @abstractmethod
    async def _run_health_test(self):
        """Run agent-specific health test. Override in subclasses."""
        pass
    
    def _create_fallback_analysis(self, response: str, question: str, base_score: float = 7.0):
        """Create fallback analysis when agent analysis fails."""
        return {
            "score": base_score,
            "feedback": f"Basic {self.name.lower()} analysis - detailed analysis temporarily unavailable",
            "confidence": 0.5,
            "details": {"fallback": True, "response_length": len(response)},
            "recommendations": [f"Detailed {self.name.lower()} analysis temporarily unavailable"]
        }
