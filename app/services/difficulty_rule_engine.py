"""
Simplified Difficulty Rule Engine

This module provides a simple, data-driven approach to determining question difficulty
without the complexity of the strategy pattern.
"""
from typing import Dict, Any, Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DifficultyRuleEngine:
    """Simplified difficulty determination engine."""
    
    def __init__(self):
        # Simple rule functions instead of strategy pattern
        self.rules = [
            self._check_seniority,
            self._check_keywords,
            self._check_length
        ]
    
    def determine_difficulty(self, question_text: str, role_analysis: Dict[str, Any]) -> str:
        """Determine difficulty using simple rule functions."""
        for rule_func in self.rules:
            try:
                if difficulty := rule_func(question_text, role_analysis):
                    logger.debug(f"Difficulty determined: {difficulty}")
                    return difficulty
            except Exception as e:
                logger.warning(f"Error in rule: {e}")
                continue
        
        return 'medium'  # Default
    
    def _check_seniority(self, question_text: str, role_analysis: Dict[str, Any]) -> Optional[str]:
        """Check seniority-based difficulty."""
        seniority = role_analysis.get('seniority_level', '').lower()
        if seniority in ['junior', 'entry']:
            return 'easy'
        elif seniority in ['senior', 'lead', 'principal']:
            return 'hard'
        return None
    
    def _check_keywords(self, question_text: str, role_analysis: Dict[str, Any]) -> Optional[str]:
        """Check keyword-based difficulty."""
        text_lower = question_text.lower()
        
        # Hard keywords
        hard_keywords = ['architecture', 'scalability', 'performance', 'distributed', 'microservices']
        if any(keyword in text_lower for keyword in hard_keywords):
            return 'hard'
        
        # Easy keywords
        easy_keywords = ['basic', 'simple', 'explain', 'what is', 'define']
        if any(keyword in text_lower for keyword in easy_keywords):
            return 'easy'
        
        return None
    
    def _check_length(self, question_text: str, role_analysis: Dict[str, Any]) -> Optional[str]:
        """Check length-based difficulty."""
        word_count = len(question_text.split())
        if word_count > 50:
            return 'hard'
        elif word_count < 15:
            return 'easy'
        return None


# Global instance
difficulty_rule_engine = DifficultyRuleEngine()