"""
Functional Question Selector for InterviewIQ.

This module implements a functional approach to question selection,
replacing nested loops with clean, composable filter and transform operations.
"""
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from functools import reduce
from app.database.models import Question
from app.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class SelectionContext:
    """Context for functional question selection."""
    role: str
    job_description: str
    target_count: int
    user_preferences: Optional[Dict[str, Any]] = None
    session_history: Optional[List[str]] = None

class QuestionFilter:
    """Functional filter operations for questions."""
    
    @staticmethod
    def by_category(categories: List[str]) -> Callable[[Question], bool]:
        """Filter questions by category."""
        def filter_func(question: Question) -> bool:
            return question.category in categories
        return filter_func
    
    @staticmethod
    def by_difficulty(difficulties: List[str]) -> Callable[[Question], bool]:
        """Filter questions by difficulty level."""
        def filter_func(question: Question) -> bool:
            return question.difficulty_level in difficulties
        return filter_func
    
    @staticmethod
    def by_role_seniority(role: str) -> Callable[[Question], bool]:
        """Filter questions based on role seniority."""
        def filter_func(question: Question) -> bool:
            role_lower = role.lower()
            
            if "senior" in role_lower or "lead" in role_lower:
                return question.difficulty_level in ["medium", "hard"]
            elif "junior" in role_lower or "entry" in role_lower:
                return question.difficulty_level in ["easy", "medium"]
            else:
                return True  # Mid-level roles get all difficulties
        
        return filter_func
    
    @staticmethod
    def by_keywords(job_description: str) -> Callable[[Question], bool]:
        """Filter questions by job description keywords."""
        job_terms = set(job_description.lower().split())
        
        def filter_func(question: Question) -> bool:
            question_terms = set(question.question_text.lower().split())
            common_terms = job_terms.intersection(question_terms)
            
            # Consider compatible if there are common terms or it's a general question
            return len(common_terms) > 0 or question.category in ["behavioral", "general"]
        
        return filter_func
    
    @staticmethod
    def not_recently_used(session_history: Optional[List[str]] = None) -> Callable[[Question], bool]:
        """Filter out recently used questions."""
        if not session_history:
            return lambda q: True
        
        recent_questions = set(session_history)
        
        def filter_func(question: Question) -> bool:
            return str(question.id) not in recent_questions
        
        return filter_func

class QuestionTransformer:
    """Functional transform operations for questions."""
    
    @staticmethod
    def add_relevance_score(job_description: str) -> Callable[[Question], Question]:
        """Add relevance score to questions."""
        job_terms = set(job_description.lower().split())
        
        def transform_func(question: Question) -> Question:
            question_terms = set(question.question_text.lower().split())
            common_terms = job_terms.intersection(question_terms)
            relevance_score = len(common_terms) / max(len(job_terms), 1)
            
            # Add relevance score as a custom attribute
            question._relevance_score = relevance_score
            
            return question
        
        return transform_func
    
    @staticmethod
    def add_diversity_score(selected_questions: List[Question]) -> Callable[[Question], Question]:
        """Add diversity score to questions."""
        # Count existing categories and difficulties
        category_counts = {}
        difficulty_counts = {}
        
        for q in selected_questions:
            category_counts[q.category] = category_counts.get(q.category, 0) + 1
            difficulty_counts[q.difficulty_level] = difficulty_counts.get(q.difficulty_level, 0) + 1
        
        def transform_func(question: Question) -> Question:
            # Calculate diversity score (lower count = higher diversity)
            category_diversity = 1.0 / (category_counts.get(question.category, 0) + 1)
            difficulty_diversity = 1.0 / (difficulty_counts.get(question.difficulty_level, 0) + 1)
            diversity_score = (category_diversity + difficulty_diversity) / 2
            
            # Add diversity score as a custom attribute
            question._diversity_score = diversity_score
            
            return question
        
        return transform_func

class QuestionSorter:
    """Functional sorting operations for questions."""
    
    @staticmethod
    def by_relevance() -> Callable[[Question], float]:
        """Sort by relevance score."""
        def sort_key(question: Question) -> float:
            return getattr(question, '_relevance_score', 0.0)
        return sort_key
    
    @staticmethod
    def by_diversity() -> Callable[[Question], float]:
        """Sort by diversity score."""
        def sort_key(question: Question) -> float:
            return getattr(question, '_diversity_score', 0.0)
        return sort_key
    
    @staticmethod
    def by_usage_count() -> Callable[[Question], int]:
        """Sort by usage count (prefer less used questions)."""
        def sort_key(question: Question) -> int:
            return question.usage_count
        return sort_key
    
    @staticmethod
    def by_quality_score() -> Callable[[Question], float]:
        """Sort by quality score."""
        def sort_key(question: Question) -> float:
            return getattr(question, 'quality_score', 0.0)
        return sort_key

class FunctionalQuestionSelector:
    """Functional question selector using composable operations."""
    
    def __init__(self):
        self.filter = QuestionFilter()
        self.transform = QuestionTransformer()
        self.sort = QuestionSorter()
    
    def select_questions(self, questions: List[Question], context: SelectionContext) -> List[Question]:
        """Select questions using functional approach."""
        logger.info(f"Selecting questions for role: {context.role}")
        
        # Create filter chain
        filters = [
            self.filter.by_role_seniority(context.role),
            self.filter.by_keywords(context.job_description),
            self.filter.not_recently_used(context.session_history)
        ]
        
        # Apply filters
        filtered_questions = self._apply_filters(questions, filters)
        
        # Apply transformations
        transformed_questions = self._apply_transforms(filtered_questions, context)
        
        # Sort and select
        selected_questions = self._sort_and_select(transformed_questions, context.target_count)
        
        logger.info(f"Selected {len(selected_questions)} questions from {len(questions)} candidates")
        return selected_questions
    
    def _apply_filters(self, questions: List[Question], filters: List[Callable[[Question], bool]]) -> List[Question]:
        """Apply all filters to questions."""
        return [q for q in questions if all(filter_func(q) for filter_func in filters)]
    
    def _apply_transforms(self, questions: List[Question], context: SelectionContext) -> List[Question]:
        """Apply transformations to questions."""
        # Add relevance scores
        relevance_transform = self.transform.add_relevance_score(context.job_description)
        questions_with_relevance = [relevance_transform(q) for q in questions]
        
        # Add diversity scores (initially empty selection)
        diversity_transform = self.transform.add_diversity_score([])
        questions_with_diversity = [diversity_transform(q) for q in questions_with_relevance]
        
        return questions_with_diversity
    
    def _sort_and_select(self, questions: List[Question], target_count: int) -> List[Question]:
        """Sort questions and select top candidates."""
        if len(questions) <= target_count:
            return questions
        
        # Multi-criteria sorting: relevance + diversity + quality - usage
        def combined_sort_key(question: Question) -> Tuple[float, float, float, int]:
            relevance = getattr(question, '_relevance_score', 0.0)
            diversity = getattr(question, '_diversity_score', 0.0)
            quality = getattr(question, 'quality_score', 0.0)
            usage = question.usage_count
            
            # Higher relevance, diversity, quality = better; lower usage = better
            return (-relevance, -diversity, -quality, usage)
        
        sorted_questions = sorted(questions, key=combined_sort_key)
        return sorted_questions[:target_count]
    
    def select_with_pipeline(self, questions: List[Question], context: SelectionContext) -> List[Question]:
        """Select questions using a functional pipeline approach."""
        logger.info(f"Functional pipeline selection for role: {context.role}")
        
        # Define pipeline steps
        pipeline = [
            # Filter steps
            lambda qs: [q for q in qs if self.filter.by_role_seniority(context.role)(q)],
            lambda qs: [q for q in qs if self.filter.by_keywords(context.job_description)(q)],
            lambda qs: [q for q in qs if self.filter.not_recently_used(context.session_history)(q)],
            
            # Transform steps
            lambda qs: [self.transform.add_relevance_score(context.job_description)(q) for q in qs],
            
            # Sort and select
            lambda qs: sorted(qs, key=self.sort.by_relevance(), reverse=True)[:context.target_count]
        ]
        
        # Execute pipeline
        result = reduce(lambda acc, step: step(acc), pipeline, questions)
        
        logger.info(f"Pipeline selected {len(result)} questions from {len(questions)} candidates")
        return result
