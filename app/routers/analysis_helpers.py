"""
Analysis Helper Functions

This module provides shared helper functions for answer analysis to eliminate
code duplication between async and sync handlers.
"""
from typing import Dict, Any
from app.utils.logger import get_logger

logger = get_logger(__name__)

async def perform_analysis_with_fallback(ai_service, request, question_text: str, role: str) -> Dict[str, Any]:
    """
    Shared analysis logic using ai-service microservice.
    
    All AI logic is handled by the ai-service microservice.
    No direct LLM calls are made in the API service.
    
    Args:
        ai_service: The AI service client (should be AIServiceClient instance)
        request: The analysis request
        question_text: The question text
        role: The job role
        
    Returns:
        Analysis response dictionary
    """
    # Use ai-service microservice for analysis
    if ai_service:
        try:
            response = await ai_service.analyze_answer(
                job_description=request.jobDescription,
                answer=request.answer,
                question=question_text,
                role=role
            )
            
            # Convert to dict if it's a Pydantic model
            if hasattr(response, 'dict'):
                return response.dict()
            return response
        except Exception as e:
            logger.error(f"AI service analysis failed: {e}")
            raise
    
    # Fallback if no AI service available
    logger.warning("AI service unavailable, returning default response")
    return {
        "analysis": "AI analysis service is currently unavailable. Please try again later.",
        "score": {"clarity": 7.0, "confidence": 7.0, "technical": 7.0, "overall": 7.0},
        "suggestions": ["Service temporarily unavailable", "Please try again in a few moments"],
        "multi_agent_analysis": None
    }

def convert_to_legacy_format(analysis) -> Dict[str, Any]:
    """
    Convert multi-agent analysis to legacy format for compatibility.
    
    Args:
        analysis: MultiAgentAnalysis object
        
    Returns:
        Legacy format response dictionary
    """
    return {
        "analysis": f"Content: {analysis.content_agent.feedback}\n\nDelivery: {analysis.delivery_agent.feedback}\n\nTechnical: {analysis.technical_agent.feedback}",
        "score": {
            "clarity": analysis.delivery_agent.score,
            "confidence": analysis.content_agent.score,
            "technical": analysis.technical_agent.score,
            "overall": analysis.overall_score
        },
        "suggestions": analysis.recommendations,
        "multi_agent_analysis": analysis.dict()
    }
