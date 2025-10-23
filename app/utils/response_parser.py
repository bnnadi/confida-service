"""
Consolidated Response Parser for Confida

This module combines all response parsing functionality into a single, flexible parser
that handles different types of AI responses with quality validation and error handling.
"""
import json
import re
from typing import List, Optional, Dict, Any, Tuple, Callable
from dataclasses import dataclass
from app.utils.logger import get_logger
from app.utils.validation import ValidationService

logger = get_logger(__name__)


@dataclass
class ParsingStrategy:
    """Represents a parsing strategy with weight and requirements."""
    name: str
    func: Callable
    weight: float = 1.0
    required: bool = False


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
        """Validate question quality and return issues if any."""
        issues = []
        
        # Use validation service for basic quality checks
        validation_service = ValidationService()
        _, basic_issues = validation_service.validate_quality(
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
        """Check if text is unclear or poorly formatted."""
        # Check for excessive repetition
        words = text.lower().split()
        if len(words) > 10:
            word_counts = {}
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
            
            # If any word appears more than 30% of the time, it's unclear
            max_repetition = max(word_counts.values()) if word_counts else 0
            if max_repetition > len(words) * 0.3:
                return True
        
        # Check for excessive punctuation
        if text.count('?') > 3 or text.count('!') > 3:
            return True
        
        return False


class ResponseParser:
    """Consolidated response parser with strategy pattern and quality validation."""
    
    def __init__(self, config_path: Optional[str] = None):
        # Load configuration from file or use defaults
        self.config = self._load_config(config_path)
        
        # Quality validator
        self.quality_validator = QualityValidator()
    
    def _load_config(self, _config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load parsing configuration - simplified version."""
        # Simple configuration since strategy pattern was removed
        return {
            'quality_validation': {
                'enabled': True,
                'min_questions': 1,
                'max_questions': 20
            }
        }
    
    
    def parse_questions(self, response_text: str, min_questions: int = 1) -> List[str]:
        """Simple parsing with fallback chain."""
        try:
            # Try JSON first
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                questions = data.get('questions', [])
                if len(questions) >= min_questions:
                    return questions
            
            # Try simple list parsing
            questions = re.findall(r'^\d+\.\s*(.+)$', response_text, re.MULTILINE)
            if len(questions) >= min_questions:
                return questions
            
            # Fallback
            return self._get_fallback_questions()
            
        except Exception as e:
            logger.error(f"Error parsing questions: {e}")
            return self._get_fallback_questions()
    
    def parse_analysis(self, response_text: str) -> Dict[str, Any]:
        """
        Parse analysis response from AI.
        
        Args:
            response_text: Raw AI response text
            
        Returns:
            Dictionary with analysis results
        """
        try:
            logger.info(f"Parsing analysis from response (length: {len(response_text)})")
            
            # Try JSON parsing first
            try:
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
                if json_match:
                    analysis_data = json.loads(json_match.group(1))
                    return self._validate_analysis(analysis_data)
            except Exception as e:
                logger.debug(f"JSON parsing failed: {e}")
            
            # Try to extract structured data from text
            analysis = self._extract_analysis_from_text(response_text)
            return self._validate_analysis(analysis)
            
        except Exception as e:
            logger.error(f"Error parsing analysis: {e}")
            return self._get_fallback_analysis()
    
    
    def _validate_questions(self, questions: List[str]) -> List[str]:
        """Validate question quality and filter out poor questions."""
        validated = []
        
        for question in questions:
            is_valid, issues = self.quality_validator.validate_question_quality(question)
            if is_valid:
                validated.append(question)
            else:
                logger.debug(f"Question filtered out due to quality issues: {issues}")
        
        return validated
    
    def _extract_analysis_from_text(self, text: str) -> Dict[str, Any]:
        """Extract analysis data from unstructured text."""
        analysis = {
            'analysis': text,
            'score': {'overall': 7.0},
            'suggestions': []
        }
        
        # Try to extract score
        score_match = re.search(r'(?:score|rating):\s*(\d+(?:\.\d+)?)', text, re.IGNORECASE)
        if score_match:
            analysis['score']['overall'] = float(score_match.group(1))
        
        # Try to extract suggestions
        suggestion_patterns = [
            r'(?:suggestion|recommendation|improvement):\s*(.+?)(?=\n|$)',
            r'•\s*(.+?)(?=\n|$)',
            r'-\s*(.+?)(?=\n|$)'
        ]
        
        for pattern in suggestion_patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            for match in matches:
                suggestion = match.strip()
                if suggestion and len(suggestion) > 5:
                    analysis['suggestions'].append(suggestion)
        
        return analysis
    
    def _validate_analysis(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and normalize analysis data."""
        # Ensure required fields exist
        if 'analysis' not in analysis:
            analysis['analysis'] = 'Analysis not available'
        
        if 'score' not in analysis:
            analysis['score'] = {'overall': 7.0}
        
        if 'suggestions' not in analysis:
            analysis['suggestions'] = []
        
        # Validate score range
        if 'overall' in analysis['score']:
            score = analysis['score']['overall']
            if not isinstance(score, (int, float)) or score < 0 or score > 10:
                analysis['score']['overall'] = 7.0
        
        return analysis
    
    def _get_fallback_questions(self) -> List[str]:
        """Get fallback questions when parsing fails."""
        return [
            "Tell me about yourself and your background.",
            "What interests you most about this role?",
            "Describe a challenging project you've worked on.",
            "How do you approach problem-solving?",
            "What are your career goals?"
        ]
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """Get fallback analysis when parsing fails."""
        return {
            'analysis': 'Unable to parse analysis from response.',
            'score': {'overall': 7.0},
            'suggestions': ['Please try again with a clearer response.']
        }
