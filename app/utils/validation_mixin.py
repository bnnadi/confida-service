"""
ValidationMixin class for common validation patterns.
Extracts repetitive validation logic across services.
"""

import re
from typing import List, Tuple, Dict, Any

class ValidationMixin:
    """Mixin class providing common validation methods."""
    
    @staticmethod
    def validate_text_length(text: str, min_length: int = 20, max_length: int = 500) -> bool:
        """Validate text length within specified bounds."""
        return min_length <= len(text) <= max_length
    
    @staticmethod
    def validate_word_count(text: str, min_words: int = 5, max_words: int = 100) -> bool:
        """Validate word count within specified bounds."""
        word_count = len(text.split())
        return min_words <= word_count <= max_words
    
    @staticmethod
    def contains_patterns(text: str, patterns: List[str]) -> bool:
        """Check if text contains any of the specified patterns."""
        text_lower = text.lower()
        return any(pattern in text_lower for pattern in patterns)
    
    @staticmethod
    def contains_regex_patterns(text: str, patterns: List[str]) -> bool:
        """Check if text matches any of the specified regex patterns."""
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)
    
    @staticmethod
    def validate_quality(text: str, min_length: int = 20, max_length: int = 500, 
                        min_words: int = 5, max_words: int = 100) -> Tuple[bool, List[str]]:
        """Comprehensive quality validation with detailed feedback."""
        issues = []
        
        if not ValidationMixin.validate_text_length(text, min_length, max_length):
            issues.append(f"Text length must be between {min_length} and {max_length} characters")
        
        if not ValidationMixin.validate_word_count(text, min_words, max_words):
            issues.append(f"Word count must be between {min_words} and {max_words} words")
        
        return len(issues) == 0, issues
    
    @staticmethod
    def find_matching_items(text: str, item_dict: Dict[Any, List[str]]) -> List[str]:
        """Generic method to find matching items in text using keyword dictionary."""
        text_lower = text.lower()
        matches = []
        for category, items in item_dict.items():
            for item in items:
                if item in text_lower:
                    matches.append(item)
        return list(set(matches))
    
    @staticmethod
    def categorize_by_keywords(text: str, rules: Dict[str, List[str]]) -> str:
        """Categorize text using keyword-based rules."""
        text_lower = text.lower()
        for category, keywords in rules.items():
            if keywords and any(keyword in text_lower for keyword in keywords):
                return category
        return "general"  # default category
