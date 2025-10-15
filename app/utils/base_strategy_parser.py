"""
Base Strategy Parser for unified strategy-based parsing.
Eliminates duplicate strategy execution logic across different parsers.
"""

import re
from typing import List, Any, Optional, Callable
from dataclasses import dataclass
from app.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class ParsingStrategy:
    """Represents a parsing strategy with weight and metadata."""
    name: str
    func: Callable
    weight: float
    min_results: int = 1
    required: bool = False

class BaseStrategyParser:
    """Base class for strategy-based parsing with unified execution logic."""
    
    # Compile patterns once at class level for better performance
    FAILURE_PATTERNS = [
        re.compile(r'\b(I cannot|I\'m sorry|I apologize|I don\'t know)\b', re.IGNORECASE),
        re.compile(r'\b(unable to|can\'t help|not allowed|forbidden)\b', re.IGNORECASE),
        re.compile(r'\b(error|failed|invalid|unsupported)\b', re.IGNORECASE),
        re.compile(r'\b(please try again|contact support|technical issue)\b', re.IGNORECASE)
    ]
    
    def __init__(self, strategies: List[ParsingStrategy], fallback_func: Callable):
        self.strategies = strategies
        self.fallback_func = fallback_func
    
    def parse_with_strategies(self, input_data: str, min_results: int = 1) -> Any:
        """Unified strategy execution with fallback."""
        if self._detects_failure(input_data):
            logger.warning("Failure pattern detected, using fallback")
            return self.fallback_func()
        
        sorted_strategies = sorted(self.strategies, key=lambda s: s.weight, reverse=True)
        
        for strategy in sorted_strategies:
            try:
                result = strategy.func(input_data)
                if result and self._meets_minimum_requirements(result, min_results):
                    logger.info(f"Successfully parsed using {strategy.name} strategy")
                    return self._limit_results(result)
            except Exception as e:
                logger.debug(f"Strategy {strategy.name} failed: {e}")
                continue
        
        logger.warning("All strategies failed, using fallback")
        return self.fallback_func()
    
    def _detects_failure(self, text: str) -> bool:
        """Detect failure patterns in input text."""
        return any(pattern.search(text) for pattern in self.FAILURE_PATTERNS)
    
    def _meets_minimum_requirements(self, result: Any, min_results: int) -> bool:
        """Check if result meets minimum requirements."""
        if isinstance(result, list):
            return len(result) >= min_results
        return bool(result)
    
    def _limit_results(self, result: Any) -> Any:
        """Limit results if needed."""
        if isinstance(result, list) and len(result) > 10:
            return result[:10]
        return result

class PatternMatchingMixin:
    """Mixin for common pattern matching operations."""
    
    @staticmethod
    def extract_json_patterns(text: str) -> List[str]:
        """Extract JSON patterns from text."""
        patterns = [
            r'```json\s*(\{.*?\})\s*```',
            r'```\s*(\{.*?\})\s*```',
            r'(\{[^{}]*"questions"[^{}]*\})',
            r'(\{[^{}]*"items"[^{}]*\})',
            r'(\{[^{}]*"score"[^{}]*\})'
        ]
        
        matches = []
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                matches.append(match.group(1) if match.groups() else match.group())
        
        return matches
    
    @staticmethod
    def extract_list_patterns(text: str) -> List[str]:
        """Extract list patterns from text."""
        patterns = [
            r'(\d+\.\s+[^\n]+(?:\n(?!(?:\d+\.|\n\n))[^\n]+)*)',
            r'(\d+\)\s+[^\n]+(?:\n(?!(?:\d+\)|\n\n))[^\n]+)*)',
            r'(\d+-\s+[^\n]+(?:\n(?!(?:\d+-|\n\n))[^\n]+)*)',
            r'(\*\s+[^\n]+(?:\n(?!(?:\*|\n\n))[^\n]+)*)',
            r'(-\s+[^\n]+(?:\n(?!(?:-|\n\n))[^\n]+)*)',
            r'(\+\s+[^\n]+(?:\n(?!(?:\+|\n\n))[^\n]+)*)'
        ]
        
        items = []
        for pattern in patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            for match in matches:
                # Clean up the item
                item = re.sub(r'^\d+[\.\)\-]\s*|^[\*\+\-]\s*', '', match.strip())
                if item and len(item) > 10:
                    items.append(item)
        
        return items
    
    @staticmethod
    def extract_line_by_line(text: str) -> List[str]:
        """Extract items line by line."""
        lines = text.split('\n')
        items = []
        
        for line in lines:
            line = line.strip()
            if (line and 
                len(line) > 20 and 
                ('?' in line or 'how' in line.lower() or 'what' in line.lower()) and
                not line.startswith(('#', '//', '/*', '*', '-', '+'))):
                items.append(line)
        
        return items
