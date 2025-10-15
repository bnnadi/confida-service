"""
Response Strategy Parser for weighted parsing strategies.
Replaces sequential strategy execution with weighted, prioritized parsing.
"""

import json
import re
from typing import List, Optional, Dict, Any, Tuple, Callable
from dataclasses import dataclass
from app.models.schemas import ParseJDResponse, AnalyzeAnswerResponse, Score
from app.utils.logger import get_logger
from app.utils.base_strategy_parser import BaseStrategyParser, ParsingStrategy, PatternMatchingMixin

logger = get_logger(__name__)

class ResponseStrategyParser(BaseStrategyParser, PatternMatchingMixin):
    """Parser using weighted strategies for robust response parsing."""
    
    def __init__(self):
        # Strategy configuration with defaults
        strategy_configs = [
            ("json_format", self._parse_json_format, 1.0, 3),
            ("numbered_list", self._parse_numbered_list, 0.8, 3),
            ("bullet_list", self._parse_bullet_list, 0.6, 3),
            ("line_by_line", self._parse_line_by_line, 0.4, 2)
        ]
        
        strategies = [
            ParsingStrategy(
                name=name,
                func=func,
                weight=weight,
                min_results=min_results,
                required=False
            )
            for name, func, weight, min_results in strategy_configs
        ]
        
        super().__init__(strategies, self._get_fallback_questions)
    
    def parse_questions_from_response(self, response_text: str) -> List[str]:
        """Parse questions using weighted strategies."""
        return self.parse_with_strategies(response_text, min_results=3)
    
    def _parse_json_format(self, response_text: str) -> List[str]:
        """Parse JSON format responses."""
        json_patterns = self.extract_json_patterns(response_text)
        
        for json_str in json_patterns:
            try:
                data = json.loads(json_str)
                
                # Try different possible keys
                questions = (data.get('questions') or 
                           data.get('items') or 
                           data.get('interview_questions') or
                           data.get('question_list'))
                
                if questions and isinstance(questions, list):
                    return [str(q) for q in questions if q]
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
        
        return []
    
    def _parse_numbered_list(self, response_text: str) -> List[str]:
        """Parse numbered list format."""
        return self.extract_list_patterns(response_text)
    
    def _parse_bullet_list(self, response_text: str) -> List[str]:
        """Parse bullet point format."""
        return self.extract_list_patterns(response_text)
    
    def _parse_line_by_line(self, response_text: str) -> List[str]:
        """Parse line-by-line format."""
        return self.extract_line_by_line(response_text)
    
    def _detects_ai_failure(self, text: str) -> bool:
        """Detect AI failure patterns."""
        failure_patterns = [
            r'\b(I cannot|I\'m sorry|I apologize|I don\'t know)\b',
            r'\b(unable to|can\'t help|not allowed|forbidden)\b',
            r'\b(error|failed|invalid|unsupported)\b',
            r'\b(please try again|contact support|technical issue)\b'
        ]
        
        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in failure_patterns)
    
    def _get_fallback_questions(self) -> List[str]:
        """Get fallback questions when parsing fails."""
        return [
            "Can you walk me through your experience with this technology?",
            "How would you approach solving a complex problem in this area?",
            "What challenges have you faced in your previous projects?",
            "How do you stay updated with the latest developments in this field?",
            "Can you describe a time when you had to learn something new quickly?"
        ]

class AnalysisResponseStrategyParser(BaseStrategyParser, PatternMatchingMixin):
    """Strategy parser for analysis responses."""
    
    def __init__(self):
        strategies = [
            ParsingStrategy(
                name="json_analysis",
                func=self._parse_json_analysis,
                weight=1.0,
                min_results=1,
                required=False
            ),
            ParsingStrategy(
                name="structured_text",
                func=self._parse_structured_text,
                weight=0.7,
                min_results=1,
                required=False
            )
        ]
        super().__init__(strategies, self._get_fallback_analysis)
    
    def parse_analysis_response(self, response_text: str) -> AnalyzeAnswerResponse:
        """Parse analysis response using strategies."""
        return self.parse_with_strategies(response_text, min_results=1)
    
    def _parse_json_analysis(self, response_text: str) -> Optional[AnalyzeAnswerResponse]:
        """Parse JSON analysis format."""
        patterns = [
            r'```json\s*(\{.*?\})\s*```',
            r'```\s*(\{.*?\})\s*```',
            r'(\{[^{}]*"score"[^{}]*\})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response_text, re.DOTALL)
            if match:
                try:
                    json_str = match.group(1)
                    analysis = json.loads(json_str)
                    return self._build_analysis_response(analysis)
                except (json.JSONDecodeError, KeyError, TypeError):
                    continue
        
        return None
    
    def _parse_structured_text(self, response_text: str) -> Optional[AnalyzeAnswerResponse]:
        """Parse structured text format."""
        # Simple text parsing - can be enhanced
        score_match = re.search(r'score[:\s]*(\d+)', response_text, re.IGNORECASE)
        score = int(score_match.group(1)) if score_match else 5
        
        return AnalyzeAnswerResponse(
            score=Score(clarity=score, confidence=score),
            missingKeywords=[],
            improvements=[],
            idealAnswer=""
        )
    
    def _build_analysis_response(self, analysis: dict) -> AnalyzeAnswerResponse:
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
    
    def _get_fallback_analysis(self) -> AnalyzeAnswerResponse:
        """Get fallback analysis when parsing fails."""
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
