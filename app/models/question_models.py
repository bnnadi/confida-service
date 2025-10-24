"""
Question models for diversity engine and other services.
Separated to avoid circular imports.
"""

from typing import List
from dataclasses import dataclass
from enum import Enum
from .intelligent_question_models import QuestionCategory

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
