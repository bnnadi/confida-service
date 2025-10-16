"""
Base Agent Class

This module provides a base class for all analysis agents to eliminate code duplication
and provide consistent functionality across different agent types.
"""
import json
import re
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
    
    def _parse_ai_response(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI response into structured data - shared across all agents."""
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Fallback parsing
                return self._fallback_parse(ai_response)
        except Exception as e:
            logger.warning(f"Failed to parse AI response: {e}")
            return self._fallback_parse(ai_response)
    
    def _fallback_parse(self, response: str) -> Dict[str, Any]:
        """Fallback parsing when JSON parsing fails - to be overridden by subclasses."""
        return {
            "score": 7,
            "confidence": 0.6,
            "strengths": ["Response provided"],
            "weaknesses": ["Analysis parsing failed"],
            "improvement_suggestions": ["Provide more detailed analysis"]
        }
    
    def _create_fallback_analysis(self, response: str, question: str, base_score: float = 7.0):
        """Create fallback analysis when agent analysis fails."""
        return {
            "score": base_score,
            "feedback": f"Basic {self.name.lower()} analysis - detailed analysis temporarily unavailable",
            "confidence": 0.5,
            "details": {"fallback": True, "response_length": len(response)},
            "recommendations": [f"Detailed {self.name.lower()} analysis temporarily unavailable"]
        }
