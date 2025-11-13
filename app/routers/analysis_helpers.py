"""
Analysis Helper Functions

Shared utilities for analyzing interview answers and extracting scoring data.
"""
from typing import Dict, Any, Optional


async def perform_analysis_with_fallback(ai_service, request, question_text: str, role: str) -> Dict[str, Any]:
    """
    Perform answer analysis with fallback mechanism.
    
    Args:
        ai_service: AI service client
        request: Analysis request
        question_text: Question text
        role: Job role
        
    Returns:
        Analysis response dictionary
    """
    try:
        if ai_service:
            response = await ai_service.analyze_answer(
                job_description=request.jobDescription,
                question=question_text,
                answer=request.answer,
                role=role
            )
            return response
    except Exception:
        pass
    
    # Fallback response
    return {
        "analysis": "Analysis temporarily unavailable. Please try again later.",
        "score": {"clarity": 5, "confidence": 5},
        "suggestions": []
    }


def extract_enhanced_score(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract enhanced scoring rubric from AI response.
    
    Checks multiple possible locations in the response structure.
    
    Args:
        response: AI service response dictionary
        
    Returns:
        Enhanced scoring rubric dictionary if found, None otherwise
    """
    if "enhanced_rubric" in response:
        return response.get("enhanced_rubric")
    
    multi_agent = response.get("multi_agent_analysis", {})
    if isinstance(multi_agent, dict) and "enhanced_rubric" in multi_agent:
        return multi_agent.get("enhanced_rubric")
    
    return None
