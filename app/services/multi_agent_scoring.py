"""
Multi-Agent Scoring Service

This service provides comprehensive answer analysis using specialized AI agents
for different aspects of interview responses, enabling detailed feedback and scoring.
"""
import asyncio
from typing import List, Dict, Any, Optional
# Import agents only when needed to avoid circular imports
from app.models.scoring_models import (
    MultiAgentAnalysis, AgentScore, ScoringWeights, 
    ContentAnalysis, DeliveryAnalysis, TechnicalAnalysis
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

class MultiAgentScoringService:
    """Service for multi-agent answer analysis and scoring."""
    
    def __init__(self):
        # Import agents dynamically to avoid circular imports
        from app.services.agents.content_agent import ContentAnalysisAgent
        from app.services.agents.delivery_agent import DeliveryAnalysisAgent
        from app.services.agents.technical_agent import TechnicalAnalysisAgent
        
        self.content_agent = ContentAnalysisAgent()
        self.delivery_agent = DeliveryAnalysisAgent()
        self.technical_agent = TechnicalAnalysisAgent()
        self.default_weights = ScoringWeights()
    
    async def analyze_response(
        self, 
        response: str, 
        question: str,
        job_description: str,
        role: str = "",
        weights: Optional[ScoringWeights] = None
    ) -> MultiAgentAnalysis:
        """
        Analyze response using multiple specialized agents.
        
        Args:
            response: The candidate's answer text
            question: The interview question
            job_description: Job description for context
            role: Job role for specialized analysis
            weights: Custom scoring weights (optional)
            
        Returns:
            MultiAgentAnalysis with comprehensive scoring and feedback
        """
        try:
            logger.info(f"Starting multi-agent analysis for role: {role}")
            
            # Use custom weights or defaults
            scoring_weights = weights or self.default_weights
            
            # Run agents in parallel
            tasks = [
                self.content_agent.analyze(response, question, job_description, role),
                self.delivery_agent.analyze(response, question, job_description),
                self.technical_agent.analyze(response, question, job_description, role)
            ]
            
            content_analysis, delivery_analysis, technical_analysis = await asyncio.gather(*tasks)
            
            # Simple score calculation
            overall_score = (
                content_analysis.score * scoring_weights.content_weight +
                delivery_analysis.score * scoring_weights.delivery_weight +
                technical_analysis.score * scoring_weights.technical_weight
            )
            
            # Generate recommendations and analysis
            recommendations = self._get_top_recommendations(content_analysis, delivery_analysis, technical_analysis)
            strengths = self._get_strengths(content_analysis, delivery_analysis, technical_analysis)
            improvements = self._get_improvements(content_analysis, delivery_analysis, technical_analysis)
            
            # Create multi-agent analysis result
            analysis = MultiAgentAnalysis(
                content_agent=self._create_agent_score(content_analysis),
                delivery_agent=self._create_agent_score(delivery_analysis),
                technical_agent=self._create_agent_score(technical_analysis),
                overall_score=round(overall_score, 2),
                recommendations=recommendations,
                strengths=strengths,
                areas_for_improvement=improvements,
                analysis_metadata={
                    "role": role,
                    "response_length": len(response),
                    "weights_used": scoring_weights.dict()
                }
            )
            
            logger.info(f"Multi-agent analysis completed. Overall score: {overall_score:.2f}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error in multi-agent analysis: {e}")
            # Return fallback analysis
            return self._create_fallback_analysis(response, question, job_description, role)
    
    def _get_top_recommendations(self, content_analysis, delivery_analysis, technical_analysis) -> List[str]:
        """Get top recommendations from all agents."""
        recommendations = []
        
        if content_analysis.score < 7.0:
            recommendations.extend(content_analysis.recommendations)
        if delivery_analysis.score < 7.0:
            recommendations.extend(delivery_analysis.recommendations)
        if technical_analysis.score < 7.0:
            recommendations.extend(technical_analysis.recommendations)
        
        return list(dict.fromkeys(recommendations))[:5]
    
    def _get_strengths(self, content_analysis, delivery_analysis, technical_analysis) -> List[str]:
        """Get strengths from high-scoring agents."""
        strengths = []
        if content_analysis.score >= 8.0:
            strengths.append("Strong content relevance and completeness")
        if delivery_analysis.score >= 8.0:
            strengths.append("Clear and confident communication")
        if technical_analysis.score >= 8.0:
            strengths.append("Excellent technical knowledge")
        return strengths
    
    def _get_improvements(self, content_analysis, delivery_analysis, technical_analysis) -> List[str]:
        """Get improvement areas from low-scoring agents."""
        improvements = []
        if content_analysis.score < 6.0:
            improvements.append("Content relevance and structure")
        if delivery_analysis.score < 6.0:
            improvements.append("Communication clarity and confidence")
        if technical_analysis.score < 6.0:
            improvements.append("Technical knowledge and depth")
        return improvements
    
    
    def _classify_question_type(self, question: str) -> str:
        """Classify the type of question for specialized analysis."""
        question_lower = question.lower()
        
        if any(keyword in question_lower for keyword in ["tell me about", "describe", "explain"]):
            return "behavioral"
        elif any(keyword in question_lower for keyword in ["how would you", "design", "implement", "algorithm"]):
            return "technical"
        elif any(keyword in question_lower for keyword in ["system", "architecture", "scale", "performance"]):
            return "system_design"
        else:
            return "general"
    
    def _create_agent_score(self, analysis) -> AgentScore:
        """Create AgentScore from analysis result."""
        return AgentScore(
            score=analysis.score,
            feedback=analysis.feedback,
            confidence=analysis.confidence,
            details=analysis.details
        )
    
    def _create_fallback_analysis(
        self, 
        response: str, 
        question: str, 
        job_description: str, 
        role: str
    ) -> MultiAgentAnalysis:
        """Create a fallback analysis when multi-agent analysis fails."""
        logger.warning("Creating fallback analysis due to multi-agent failure")
        
        # Simple fallback scoring based on response length and basic criteria
        base_score = min(10.0, max(1.0, len(response) / 50))  # Rough scoring based on length
        
        # Create fallback agent score template
        fallback_agent = AgentScore(
            score=base_score,
            feedback="Basic analysis - detailed analysis unavailable",
            confidence=0.5,
            details={"fallback": True}
        )
        
        return MultiAgentAnalysis(
            content_agent=fallback_agent,
            delivery_agent=fallback_agent,
            technical_agent=fallback_agent,
            overall_score=base_score,
            recommendations=["Detailed analysis temporarily unavailable. Please try again."],
            strengths=["Response provided"],
            areas_for_improvement=["Analysis system needs attention"],
            analysis_metadata={
                "role": role,
                "fallback": True,
                "error": "Multi-agent analysis failed"
            }
        )
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """Get status of all agents."""
        try:
            status = {
                "content_agent": await self.content_agent.health_check(),
                "delivery_agent": await self.delivery_agent.health_check(),
                "technical_agent": await self.technical_agent.health_check(),
                "overall_status": "healthy"
            }
            
            # Check if any agent is unhealthy
            for agent_name, agent_status in status.items():
                if agent_name != "overall_status" and not agent_status.get("healthy", False):
                    status["overall_status"] = "degraded"
                    break
            
            return status
            
        except Exception as e:
            logger.error(f"Error checking agent status: {e}")
            return {
                "content_agent": {"healthy": False, "error": str(e)},
                "delivery_agent": {"healthy": False, "error": str(e)},
                "technical_agent": {"healthy": False, "error": str(e)},
                "overall_status": "unhealthy"
            }


# Global multi-agent scoring service instance
# Global service instance - created lazily to avoid circular imports
_multi_agent_scoring_service = None

def get_multi_agent_scoring_service():
    """Get the global multi-agent scoring service instance."""
    global _multi_agent_scoring_service
    if _multi_agent_scoring_service is None:
        _multi_agent_scoring_service = MultiAgentScoringService()
    return _multi_agent_scoring_service

# For backward compatibility - use lazy loading
def multi_agent_scoring_service():
    return get_multi_agent_scoring_service()
