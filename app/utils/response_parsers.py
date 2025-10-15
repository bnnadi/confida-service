"""
Centralized response parsing utilities to eliminate duplication across AI services.
Enhanced with quality validation, content safety, and robust error handling.
"""

import json
import re
from typing import List, Optional, Dict, Any, Tuple
from app.models.schemas import ParseJDResponse, AnalyzeAnswerResponse, Score
from app.utils.logger import get_logger
from app.utils.validation_mixin import ValidationMixin

logger = get_logger(__name__)


class QualityValidator:
    """Validates question quality and content safety."""
    
    # Content safety patterns
    INAPPROPRIATE_PATTERNS = [
        r'\b(sex|sexual|nude|naked|porn|xxx)\b',
        r'\b(violence|kill|murder|suicide|bomb|terrorist)\b',
        r'\b(drug|alcohol|cocaine|marijuana|weed)\b',
        r'\b(racist|sexist|homophobic|discriminatory)\b',
        r'\b(hate|hateful|offensive|insulting)\b'
    ]
    
    # AI failure patterns
    AI_FAILURE_PATTERNS = [
        r'\b(I cannot|I\'m sorry|I apologize|I don\'t know)\b',
        r'\b(unable to|can\'t help|not allowed|forbidden)\b',
        r'\b(error|failed|invalid|unsupported)\b',
        r'\b(please try again|contact support|technical issue)\b'
    ]
    
    # Quality thresholds
    MIN_QUESTION_LENGTH = 20
    MAX_QUESTION_LENGTH = 500
    MIN_WORD_COUNT = 5
    MAX_WORD_COUNT = 100
    
    @classmethod
    def validate_question_quality(cls, question: str) -> Tuple[bool, List[str]]:
        """Validate question quality and return (is_valid, issues)."""
        issues = []
        
        # Use ValidationMixin for basic quality checks
        is_valid, basic_issues = ValidationMixin.validate_quality(
            question, 
            cls.MIN_QUESTION_LENGTH, 
            cls.MAX_QUESTION_LENGTH,
            cls.MIN_WORD_COUNT, 
            cls.MAX_WORD_COUNT
        )
        issues.extend(basic_issues)
        
        # Content safety validation
        if cls._contains_inappropriate_content(question):
            issues.append("Question contains inappropriate content")
        
        # AI failure detection
        if cls._detects_ai_failure(question):
            issues.append("Question appears to be an AI failure response")
        
        # Clarity validation
        if cls._is_unclear(question):
            issues.append("Question is unclear or poorly formatted")
        
        return len(issues) == 0, issues
    
    @classmethod
    def _contains_inappropriate_content(cls, text: str) -> bool:
        """Check if text contains inappropriate content."""
        text_lower = text.lower()
        return any(re.search(pattern, text_lower, re.IGNORECASE) for pattern in cls.INAPPROPRIATE_PATTERNS)
    
    @classmethod
    def _detects_ai_failure(cls, text: str) -> bool:
        """Detect AI failure patterns."""
        text_lower = text.lower()
        return any(re.search(pattern, text_lower, re.IGNORECASE) for pattern in cls.AI_FAILURE_PATTERNS)
    
    @classmethod
    def _is_unclear(cls, text: str) -> bool:
        """Check if question is unclear or poorly formatted."""
        # Check for common unclear patterns
        unclear_patterns = [
            r'^\s*$',  # Empty or whitespace only
            r'^[^\?]*$',  # No question mark
            r'^[A-Z\s]+$',  # All caps (shouting)
            r'^\d+\.?\s*$',  # Just a number
            r'^[^\w\s\?]',  # Starts with special character
        ]
        
        return any(re.match(pattern, text.strip()) for pattern in unclear_patterns)


class ResponseParsers:
    """Centralized response parsing utilities for all AI services."""
    
    @staticmethod
    def parse_questions_from_response(response_text: str) -> List[str]:
        """Parse questions from AI response with enhanced quality validation and error handling."""
        # Early return for AI failure patterns
        if QualityValidator._detects_ai_failure(response_text):
            logger.warning("AI failure pattern detected in response, using fallback")
            return ResponseParsers._get_fallback_questions()
        
        try:
            # Parse response using multiple strategies
            questions = ResponseParsers._parse_with_multiple_strategies(response_text)
            
            # Validate and filter questions
            validated_questions = ResponseParsers._validate_and_filter_questions(questions)
            
            # Return questions if sufficient quality, otherwise fallback
            if len(validated_questions) >= 3:
                logger.info(f"Successfully parsed {len(validated_questions)} high-quality questions")
                return validated_questions[:10]
            else:
                logger.warning(f"Only {len(validated_questions)} valid questions found, using fallback")
                return ResponseParsers._get_fallback_questions()
                
        except Exception as e:
            logger.error(f"Error parsing questions from response: {e}")
            return ResponseParsers._get_fallback_questions()
    
    @staticmethod
    def _parse_with_multiple_strategies(response_text: str) -> List[str]:
        """Parse using multiple strategies for robust extraction."""
        strategies = [
            ResponseParsers._parse_numbered_list,
            ResponseParsers._parse_bullet_list,
            ResponseParsers._parse_markdown_list,
            ResponseParsers._parse_plain_text
        ]
        
        all_questions = []
        for strategy in strategies:
            try:
                questions = strategy(response_text)
                if questions:
                    all_questions.extend(questions)
                    logger.debug(f"Strategy {strategy.__name__} found {len(questions)} questions")
            except Exception as e:
                logger.debug(f"Strategy {strategy.__name__} failed: {e}")
        
        return all_questions
    
    @staticmethod
    def _parse_list_by_pattern(text: str, pattern: str) -> List[str]:
        """Generic list parsing with configurable regex pattern."""
        questions = []
        for line in text.split('\n'):
            match = re.match(pattern, line.strip())
            if match:
                question = match.group(1).strip()
                if question and not question.startswith(('Here', 'These', 'The following')):
                    questions.append(question)
        return questions
    
    @staticmethod
    def _parse_numbered_list(text: str) -> List[str]:
        """Parse numbered list format (1. Question, 2. Question, etc.)."""
        return ResponseParsers._parse_list_by_pattern(text, r'^\s*\d+\.\s+(.+)$')
    
    @staticmethod
    def _parse_bullet_list(text: str) -> List[str]:
        """Parse bullet point format (- Question, * Question, etc.)."""
        return ResponseParsers._parse_list_by_pattern(text, r'^\s*[-*•]\s+(.+)$')
    
    @staticmethod
    def _parse_markdown_list(text: str) -> List[str]:
        """Parse markdown list format."""
        return ResponseParsers._parse_list_by_pattern(text, r'^\s*[-*]\s+(.+)$')
    
    @staticmethod
    def _parse_plain_text(text: str) -> List[str]:
        """Parse plain text format (fallback)."""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        questions = []
        for line in lines:
            # Skip common non-question patterns
            if any(line.startswith(prefix) for prefix in ['Here', 'These', 'The following', 'Based on', 'According to']):
                continue
            
            # Look for question patterns
            if '?' in line and len(line) > 20:
                questions.append(line)
        
        return questions
    
    @staticmethod
    def _validate_and_filter_questions(questions: List[str]) -> List[str]:
        """Validate and filter questions for quality."""
        validated_questions = []
        rejected_count = 0
        
        for question in questions:
            is_valid, issues = QualityValidator.validate_question_quality(question)
            
            if is_valid:
                validated_questions.append(question)
            else:
                rejected_count += 1
                logger.debug(f"Rejected question: {question[:50]}... Issues: {', '.join(issues)}")
        
        if rejected_count > 0:
            logger.info(f"Filtered out {rejected_count} low-quality questions")
        
        return validated_questions
    
    @staticmethod
    def _get_fallback_questions() -> List[str]:
        """Get fallback questions when parsing fails."""
        return [
            "Tell me about your experience with the technologies mentioned in this role.",
            "What challenges have you faced in similar projects?",
            "How do you approach problem-solving in your work?",
            "Describe a time when you had to learn something new quickly.",
            "What interests you most about this position?",
            "How do you stay updated with industry trends?",
            "Describe your ideal work environment.",
            "What are your career goals for the next few years?",
            "How do you handle working under pressure?",
            "What questions do you have about this role?"
        ]
    
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
