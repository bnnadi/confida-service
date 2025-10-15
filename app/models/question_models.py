"""
Question models for diversity engine and other services.
Separated to avoid circular imports.
"""

from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

class QuestionCategory(Enum):
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    SYSTEM_DESIGN = "system_design"
    LEADERSHIP = "leadership"
    DATA_ANALYSIS = "data_analysis"
    PROBLEM_SOLVING = "problem_solving"
    COMMUNICATION = "communication"

class DifficultyLevel(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

@dataclass
class Question:
    """Question model for diversity engine."""
    id: str
    question_text: str
    category: QuestionCategory
    difficulty_level: DifficultyLevel
    tags: List[str] = None
    role_relevance_score: float = 0.5
    quality_score: float = 0.5
    user_history_score: float = 0.5
    diversity_score: float = 0.0
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
