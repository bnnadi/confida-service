"""
Centralized fallback responses to eliminate duplication across AI services.
"""

from app.models.schemas import ParseJDResponse, AnalyzeAnswerResponse, Score


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
    def get_fallback_analysis() -> AnalyzeAnswerResponse:
        """Get fallback analysis if all AI services fail."""
        return AnalyzeAnswerResponse(
            score=Score(clarity=5, confidence=5),
            missingKeywords=["specific examples", "metrics", "technical details"],
            improvements=[
                "Provide more specific examples",
                "Include quantifiable results",
                "Add more technical details",
                "Demonstrate problem-solving approach"
            ],
            idealAnswer="Please provide a more detailed answer with specific examples, measurable outcomes, and technical depth."
        )
