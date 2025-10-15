"""
Centralized response parsing utilities to eliminate duplication across AI services.
"""

import json
import re
from typing import List, Optional
from app.models.schemas import ParseJDResponse, AnalyzeAnswerResponse, Score
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ResponseParsers:
    """Centralized response parsing utilities for all AI services."""
    
    @staticmethod
    def parse_questions_from_response(response_text: str) -> List[str]:
        """Parse questions from AI response using functional approach."""
        lines = [line.strip() for line in response_text.split('\n') if line.strip()]
        
        def extract_question(line: str) -> Optional[str]:
            """Extract question from line using pattern matching."""
            patterns = [
                (r'^\d+\.\s+(.+)$', lambda m: m.group(1)),  # "1. Question"
                (r'^\(\d+\)\s+(.+)$', lambda m: m.group(1)),  # "(1) Question"
                (r'^(.+)$', lambda m: m.group(1))  # Plain question
            ]
            
            for pattern, extractor in patterns:
                match = re.match(pattern, line)
                if match:
                    question = extractor(match).strip()
                    if question and not question.startswith(('Here', 'These')):
                        return question
            return None
        
        questions = [q for q in map(extract_question, lines) if q]
        return questions[:10]
    
    @staticmethod
    def parse_analysis_response(response_text: str) -> AnalyzeAnswerResponse:
        """Parse analysis with simplified pattern matching."""
        json_patterns = [
            r'\{.*\}',
            r'```json\s*(\{.*?\})\s*```',
            r'```\s*(\{.*?\})\s*```',
        ]
        
        for pattern in json_patterns:
            if analysis := ResponseParsers._try_parse_with_pattern(response_text, pattern):
                return ResponseParsers._build_analysis_response(analysis)
        
        logger.warning("Could not parse JSON from AI response, using fallback")
        return ResponseParsers._get_fallback_analysis()
    
    @staticmethod
    def _try_parse_with_pattern(response_text: str, pattern: str) -> Optional[dict]:
        """Extract pattern matching logic."""
        try:
            json_match = re.search(pattern, response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1) if json_match.groups() else json_match.group()
                return json.loads(json_str)
        except (json.JSONDecodeError, AttributeError) as e:
            logger.debug(f"Failed to parse with pattern {pattern}: {e}")
        return None
    
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
