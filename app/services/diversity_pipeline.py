"""
Diversity Pipeline for question selection.
Replaces complex monolithic diversity logic with clean pipeline pattern.
"""

import random
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from app.models.question_models import Question, QuestionCategory, DifficultyLevel
from app.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class PipelineStep:
    """Represents a step in the diversity pipeline."""
    name: str
    func: Callable
    required: bool = True
    weight: float = 1.0

class DiversityPipeline:
    """Pipeline for processing questions through diversity steps."""
    
    def __init__(self):
        self.steps = []
        self.config = {
            'target_count': 10,
            'role_type': 'mid',
            'user_history': None
        }
    
    def add_step(self, step: PipelineStep):
        """Add a step to the pipeline."""
        self.steps.append(step)
        return self
    
    def execute(self, questions: List[Question], **config) -> List[Question]:
        """Execute the pipeline with given configuration."""
        self.config.update(config)
        
        if not questions:
            logger.warning("No questions provided to diversity pipeline")
            return []
        
        logger.info(f"Starting diversity pipeline with {len(questions)} questions")
        
        current_questions = questions
        
        for step in self.steps:
            try:
                logger.debug(f"Executing step: {step.name}")
                current_questions = step.func(current_questions, **self.config)
                
                if not current_questions and step.required:
                    logger.error(f"Required step {step.name} failed, returning empty result")
                    return []
                    
            except Exception as e:
                logger.error(f"Error in step {step.name}: {e}")
                if step.required:
                    return []
                continue
        
        logger.info(f"Diversity pipeline completed with {len(current_questions)} questions")
        return current_questions

class QuestionDiversityPipeline:
    """Specialized pipeline for question diversity operations."""
    
    def __init__(self):
        self.pipeline = DiversityPipeline()
        self._setup_default_pipeline()
    
    def _setup_default_pipeline(self):
        """Setup the default diversity pipeline steps."""
        self.pipeline.add_step(PipelineStep(
            name="filter_recent",
            func=self._filter_recent_questions,
            required=False
        )).add_step(PipelineStep(
            name="score_questions",
            func=self._score_questions,
            required=True
        )).add_step(PipelineStep(
            name="select_diverse",
            func=self._select_diverse_questions,
            required=True
        )).add_step(PipelineStep(
            name="shuffle",
            func=self._shuffle_questions,
            required=False
        ))
    
    def ensure_diversity(self, questions: List[Question], target_count: int = 10,
                        role_type: str = 'mid', user_history: Optional[List[str]] = None) -> List[Question]:
        """Ensure question diversity using pipeline approach."""
        return self.pipeline.execute(
            questions,
            target_count=target_count,
            role_type=role_type,
            user_history=user_history
        )
    
    def _filter_recent_questions(self, questions: List[Question], **config) -> List[Question]:
        """Filter out recently asked questions."""
        user_history = config.get('user_history')
        if not user_history:
            return questions
        
        recent_question_ids = set(user_history[-20:])  # Last 20 questions
        filtered = [q for q in questions if q.id not in recent_question_ids]
        
        logger.debug(f"Filtered {len(questions) - len(filtered)} recent questions")
        return filtered
    
    def _score_questions(self, questions: List[Question], **config) -> List[Question]:
        """Score questions based on relevance and quality."""
        role_type = config.get('role_type', 'mid')
        
        for question in questions:
            # Calculate composite score
            relevance_score = getattr(question, 'role_relevance_score', 0.5)
            quality_score = getattr(question, 'quality_score', 0.5)
            history_score = getattr(question, 'user_history_score', 0.5)
            
            # Weighted composite score
            composite_score = (
                relevance_score * 0.5 +
                quality_score * 0.3 +
                history_score * 0.2
            )
            
            # Store score for later use
            question.diversity_score = composite_score
        
        # Sort by score (highest first)
        questions.sort(key=lambda q: getattr(q, 'diversity_score', 0), reverse=True)
        
        logger.debug(f"Scored {len(questions)} questions")
        return questions
    
    def _select_diverse_questions(self, questions: List[Question], **config) -> List[Question]:
        """Select diverse questions based on categories and difficulties."""
        target_count = config.get('target_count', 10)
        role_type = config.get('role_type', 'mid')
        
        if len(questions) <= target_count:
            return questions
        
        # Simple diversity selection - can be enhanced
        selected = []
        categories_seen = set()
        difficulties_seen = set()
        
        for question in questions:
            if len(selected) >= target_count:
                break
            
            category = getattr(question, 'category', 'general')
            difficulty = getattr(question, 'difficulty_level', 'medium')
            
            # Prefer questions from unseen categories/difficulties
            if (category not in categories_seen or 
                difficulty not in difficulties_seen or 
                len(selected) < target_count * 0.7):
                
                selected.append(question)
                categories_seen.add(category)
                difficulties_seen.add(difficulty)
        
        logger.debug(f"Selected {len(selected)} diverse questions from {len(questions)} candidates")
        return selected
    
    def _shuffle_questions(self, questions: List[Question], **config) -> List[Question]:
        """Shuffle questions to avoid predictable patterns."""
        shuffled = questions.copy()
        random.shuffle(shuffled)
        return shuffled
