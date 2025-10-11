"""
Centralized response parsing utilities to eliminate duplication across AI services.
"""

import json
import re
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
        """Parse analysis from AI response with improved error handling."""
        # Try multiple JSON extraction methods
        json_patterns = [
            r'\{.*\}',  # Original pattern
            r'```json\s*(\{.*?\})\s*```',  # Markdown code blocks
            r'```\s*(\{.*?\})\s*```',  # Generic code blocks
        ]
        
        for pattern in json_patterns:
            try:
                json_match = re.search(pattern, response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1) if json_match.groups() else json_match.group()
                    analysis = json.loads(json_str)
                    return ResponseParsers._build_analysis_response(analysis)
            except (json.JSONDecodeError, AttributeError) as e:
                logger.debug(f"Failed to parse with pattern {pattern}: {e}")
                continue
        
        logger.warning("Could not parse JSON from AI response, using fallback")
        return ResponseParsers._get_fallback_analysis()
    
    @staticmethod
    def _build_analysis_response(analysis: dict) -> AnalyzeAnswerResponse:
        """Build analysis response from parsed JSON."""
        score_data = analysis.get("score", {})
        return AnalyzeAnswerResponse(
            score=Score(
                clarity=score_data.get("clarity", 5),
                confidence=score_data.get("confidence", 5)
            ),
            missingKeywords=analysis.get("missingKeywords", []),
            improvements=analysis.get("improvements", []),
            idealAnswer=analysis.get("idealAnswer", "")
        )
    
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
