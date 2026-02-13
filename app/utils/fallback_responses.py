"""
Centralized fallback responses to eliminate duplication across AI services.
"""

from app.models.schemas import ParseJDResponse, AnalyzeAnswerResponse


class FallbackResponses:
    """Centralized fallback responses for all AI services."""
    
    @staticmethod
    def get_fallback_questions(role: str) -> ParseJDResponse:
        """Get fallback questions if all AI services fail."""
        return ParseJDResponse(questions=[
            f"Tell me about your experience with {role}",
            "Describe a challenging project you've worked on",
            "How do you handle tight deadlines?",
            "What's your approach to problem-solving?",
            "How do you stay updated with industry trends?",
            "Tell me about a time you had to learn a new technology quickly",
            "How do you handle conflicting priorities?",
            "What's your experience with code review?",
            "How do you ensure code quality?",
            "Describe a situation where you had to mentor junior developers"
        ])
    
    @staticmethod
    def get_fallback_analysis(
        job_description: str = "",
        answer: str = "",
    ) -> AnalyzeAnswerResponse:
        """Get fallback analysis if all AI services fail."""
        return AnalyzeAnswerResponse(
            analysis="Unable to complete analysis. Please try again.",
            score={"clarity": 5, "confidence": 5},
            suggestions=[
                "Provide more specific examples",
                "Include quantifiable results",
                "Add more technical details",
                "Demonstrate problem-solving approach"
            ],
            jobDescription=job_description,
            answer=answer,
            service_used="fallback"
        )
