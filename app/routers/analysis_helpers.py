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
    Shared analysis logic with fallback to single AI service.
    
    Args:
        ai_service: The AI service instance
        request: The analysis request
        question_text: The question text
        role: The job role
        
    Returns:
        Analysis response dictionary
    """
    try:
        from app.services.multi_agent_scoring import multi_agent_scoring_service
        
        # Perform multi-agent analysis
        analysis = await multi_agent_scoring_service.analyze_response(
            response=request.answer,
            question=question_text,
            job_description=request.jobDescription,
            role=role
        )
        
        logger.info(f"Multi-agent analysis completed with overall score: {analysis.overall_score}")
        return convert_to_legacy_format(analysis)
        
    except Exception as e:
        logger.warning(f"Multi-agent analysis failed, falling back to single AI: {e}")
        
        # Fallback to original AI analysis
        if hasattr(ai_service, 'analyze_answer'):
            # Async version
            response = await ai_service.analyze_answer(
                request.jobDescription, 
                request.answer,
                role=role,
                job_description=request.jobDescription
            )
        else:
            # Sync version
            response = ai_service.analyze_answer(
                request.jobDescription, 
                request.answer,
                preferred_service=getattr(request, 'preferred_service', None)
            )
        
        # Convert to dict if it's a Pydantic model
        if hasattr(response, 'dict'):
            return response.dict()
        return response

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
