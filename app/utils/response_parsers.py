"""
Centralized response parsing utilities to eliminate duplication across AI services.
"""

import json
from typing import List
from app.models.schemas import ParseJDResponse, AnalyzeAnswerResponse, Score
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ResponseParsers:
    """Centralized response parsing utilities for all AI services."""
    
    @staticmethod
    def parse_questions_from_response(response_text: str) -> List[str]:
        """Parse questions from AI response - extracted from multiple files."""
        lines = [line.strip() for line in response_text.split('\n') if line.strip()]
        questions = []
        
        for line in lines:
            # Remove numbering if present
            if '. ' in line:
                question = line.split('. ', 1)[-1]
            elif ') ' in line:
                question = line.split(') ', 1)[-1]
            else:
                question = line
            
            # Clean up the question
            question = question.strip()
            if question and not question.startswith(('Here', 'These')):
                questions.append(question)
        
        # Limit to 10 questions
        return questions[:10]
    
    @staticmethod
    def parse_analysis_response(response_text: str) -> AnalyzeAnswerResponse:
        """Parse analysis from AI response."""
        try:
            # Try to extract JSON from the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                analysis = json.loads(json_str)
                
                return AnalyzeAnswerResponse(
                    score=Score(
                        clarity=analysis.get("score", {}).get("clarity", 5),
                        confidence=analysis.get("score", {}).get("confidence", 5)
                    ),
                    missingKeywords=analysis.get("missingKeywords", []),
                    improvements=analysis.get("improvements", []),
                    idealAnswer=analysis.get("idealAnswer", "")
                )
        except Exception as e:
            logger.error(f"Error parsing analysis response: {e}")
        
        return ResponseParsers._get_fallback_analysis()
    
    @staticmethod
    def _get_fallback_analysis() -> AnalyzeAnswerResponse:
        """Fallback analysis if parsing fails."""
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
