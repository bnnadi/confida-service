"""
Question diversity engine for ensuring balanced and diverse question sets.
Implements algorithms to select questions across categories, difficulties, and types.
"""
import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from app.utils.logger import get_logger
from app.models.question_models import Question, QuestionCategory, DifficultyLevel
from app.services.diversity_pipeline import QuestionDiversityPipeline

logger = get_logger(__name__)

# Question models are now imported from app.models.question_models

@dataclass
class DiversityConfig:
    """Configuration for diversity algorithms."""
    target_count: int = 10
    min_per_category: int = 1
    max_per_category: int = 4
    min_per_difficulty: int = 1
    max_per_difficulty: int = 5
    balance_categories: bool = True
    balance_difficulties: bool = True
    prefer_high_quality: bool = True
    avoid_recent_questions: bool = True

class QuestionDiversityEngine:
    """Engine for ensuring question diversity and balance."""
    
    def __init__(self):
        self.diversity_config = DiversityConfig()
        self.pipeline = QuestionDiversityPipeline()
        
        # Category weights for different role types
        self.category_weights = {
            'junior': {
                QuestionCategory.TECHNICAL: 0.4,
                QuestionCategory.BEHAVIORAL: 0.3,
                QuestionCategory.PROBLEM_SOLVING: 0.2,
                QuestionCategory.COMMUNICATION: 0.1
            },
            'mid': {
                QuestionCategory.TECHNICAL: 0.35,
                QuestionCategory.BEHAVIORAL: 0.25,
                QuestionCategory.SYSTEM_DESIGN: 0.2,
                QuestionCategory.PROBLEM_SOLVING: 0.15,
                QuestionCategory.COMMUNICATION: 0.05
            },
            'senior': {
                QuestionCategory.TECHNICAL: 0.3,
                QuestionCategory.SYSTEM_DESIGN: 0.3,
                QuestionCategory.LEADERSHIP: 0.2,
                QuestionCategory.BEHAVIORAL: 0.15,
                QuestionCategory.PROBLEM_SOLVING: 0.05
            },
            'leadership': {
                QuestionCategory.LEADERSHIP: 0.4,
                QuestionCategory.BEHAVIORAL: 0.25,
                QuestionCategory.SYSTEM_DESIGN: 0.2,
                QuestionCategory.TECHNICAL: 0.1,
                QuestionCategory.COMMUNICATION: 0.05
            }
        }
        
        # Difficulty distribution by seniority
        self.difficulty_distribution = {
            'junior': {DifficultyLevel.EASY: 0.6, DifficultyLevel.MEDIUM: 0.4, DifficultyLevel.HARD: 0.0},
            'mid': {DifficultyLevel.EASY: 0.3, DifficultyLevel.MEDIUM: 0.5, DifficultyLevel.HARD: 0.2},
            'senior': {DifficultyLevel.EASY: 0.1, DifficultyLevel.MEDIUM: 0.4, DifficultyLevel.HARD: 0.5},
            'leadership': {DifficultyLevel.EASY: 0.1, DifficultyLevel.MEDIUM: 0.3, DifficultyLevel.HARD: 0.6}
        }

    async def ensure_diversity(self, 
                             questions: List[Question], 
                             target_count: int = 10,
                             role_type: str = 'mid',
                             user_history: Optional[List[str]] = None) -> List[Question]:
        """Ensure question diversity using pipeline approach."""
        try:
            logger.info(f"Ensuring diversity for {len(questions)} questions, target: {target_count}")
            
            # Use the pipeline for clean, testable diversity processing
            return self.pipeline.ensure_diversity(
                questions=questions,
                target_count=target_count,
                role_type=role_type,
                user_history=user_history
            )
            
        except Exception as e:
            logger.error(f"Error in diversity engine: {e}")
            # Fallback to simple selection
            return questions[:target_count] if questions else []

    def _filter_recent_questions(self, questions: List[Question], user_history: List[str]) -> List[Question]:
        """Filter out recently asked questions."""
        recent_question_ids = set(user_history[-20:])  # Last 20 questions
        return [q for q in questions if q.id not in recent_question_ids]

    def _score_questions(self, questions: List[Question], role_type: str) -> List[Question]:
        """Score questions based on relevance, quality, and diversity factors."""
        for question in questions:
            # Calculate composite score
            relevance_score = question.role_relevance_score
            quality_score = question.quality_score
            history_score = question.user_history_score
            
            # Weighted composite score
            composite_score = (
                relevance_score * 0.5 +
                quality_score * 0.3 +
                history_score * 0.2
            )
            
            # Store the composite score in a temporary attribute
            question.composite_score = composite_score
        
        # Sort by composite score (descending)
        return sorted(questions, key=lambda q: q.composite_score, reverse=True)

    async def _select_diverse_questions(self, 
                                      scored_questions: List[Question], 
                                      target_count: int,
                                      role_type: str) -> List[Question]:
        """Select diverse questions using category and difficulty balancing."""
        selected_questions = []
        
        # Get category and difficulty weights for role type
        category_weights = self.category_weights.get(role_type, self.category_weights['mid'])
        difficulty_weights = self.difficulty_distribution.get(role_type, self.difficulty_distribution['mid'])
        
        # Group questions by category and difficulty
        questions_by_category = self._group_by_category(scored_questions)
        questions_by_difficulty = self._group_by_difficulty(scored_questions)
        
        # Calculate target distribution
        category_targets = self._calculate_category_targets(target_count, category_weights)
        difficulty_targets = self._calculate_difficulty_targets(target_count, difficulty_weights)
        
        # Select questions using diversity algorithm
        selected_questions = await self._diversity_selection_algorithm(
            questions_by_category,
            questions_by_difficulty,
            category_targets,
            difficulty_targets,
            target_count
        )
        
        return selected_questions

    def _group_questions(self, questions: List[Question], group_by_attr: str) -> Dict[Any, List[Question]]:
        """Generic method to group questions by any attribute."""
        grouped = {}
        for question in questions:
            key = getattr(question, group_by_attr)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(question)
        return grouped

    def _group_by_category(self, questions: List[Question]) -> Dict[QuestionCategory, List[Question]]:
        """Group questions by category."""
        return self._group_questions(questions, 'category')

    def _group_by_difficulty(self, questions: List[Question]) -> Dict[DifficultyLevel, List[Question]]:
        """Group questions by difficulty level."""
        return self._group_questions(questions, 'difficulty_level')

    def _calculate_category_targets(self, target_count: int, category_weights: Dict[QuestionCategory, float]) -> Dict[QuestionCategory, int]:
        """Calculate target number of questions per category."""
        targets = {}
        remaining = target_count
        
        # Sort categories by weight (descending)
        sorted_categories = sorted(category_weights.items(), key=lambda x: x[1], reverse=True)
        
        for category, weight in sorted_categories:
            target = max(1, int(target_count * weight))
            target = min(target, remaining)
            targets[category] = target
            remaining -= target
        
        return targets

    def _calculate_difficulty_targets(self, target_count: int, difficulty_weights: Dict[DifficultyLevel, float]) -> Dict[DifficultyLevel, int]:
        """Calculate target number of questions per difficulty level."""
        targets = {}
        for difficulty, weight in difficulty_weights.items():
            targets[difficulty] = max(1, int(target_count * weight))
        return targets

    async def _diversity_selection_algorithm(self,
                                           questions_by_category: Dict[QuestionCategory, List[Question]],
                                           questions_by_difficulty: Dict[DifficultyLevel, List[Question]],
                                           category_targets: Dict[QuestionCategory, int],
                                           difficulty_targets: Dict[DifficultyLevel, int],
                                           target_count: int) -> List[Question]:
        """Simplified diversity selection using a scoring approach."""
        all_questions = self._flatten_questions(questions_by_category)
        
        # Score each question for diversity contribution
        scored_questions = []
        for question in all_questions:
            diversity_score = self._calculate_diversity_contribution(
                question, category_targets, difficulty_targets
            )
            scored_questions.append((question, diversity_score))
        
        # Sort by diversity score and select top questions
        scored_questions.sort(key=lambda x: x[1], reverse=True)
        return [q for q, _ in scored_questions[:target_count]]
    
    def _calculate_diversity_contribution(self, question: Question, 
                                        category_targets: Dict[QuestionCategory, int],
                                        difficulty_targets: Dict[DifficultyLevel, int]) -> float:
        """Calculate how much this question contributes to diversity."""
        category_score = 1.0 if question.category in category_targets else 0.5
        difficulty_score = 1.0 if question.difficulty_level in difficulty_targets else 0.5
        return category_score + difficulty_score + question.composite_score

    # Removed complex _adjust_for_difficulty_targets method as it's no longer needed
    # with the simplified diversity selection algorithm

    def _flatten_questions(self, questions_by_category: Dict[QuestionCategory, List[Question]]) -> List[Question]:
        """Flatten grouped questions into a single list."""
        all_questions = []
        for category_questions in questions_by_category.values():
            all_questions.extend(category_questions)
        return all_questions

    def calculate_diversity_score(self, questions: List[Question]) -> float:
        """Calculate diversity score for a set of questions."""
        if not questions:
            return 0.0
        
        # Category diversity
        categories = set(q.category for q in questions)
        category_diversity = len(categories) / len(QuestionCategory)
        
        # Difficulty diversity
        difficulties = set(q.difficulty_level for q in questions)
        difficulty_diversity = len(difficulties) / len(DifficultyLevel)
        
        # Tag diversity
        all_tags = set()
        for question in questions:
            all_tags.update(question.tags)
        tag_diversity = min(1.0, len(all_tags) / (len(questions) * 2))  # Normalize by expected tags
        
        # Overall diversity score
        diversity_score = (category_diversity * 0.4 + 
                          difficulty_diversity * 0.3 + 
                          tag_diversity * 0.3)
        
        return diversity_score

    def get_diversity_report(self, questions: List[Question]) -> Dict[str, Any]:
        """Generate a diversity report for a set of questions."""
        if not questions:
            return {"error": "No questions provided"}
        
        # Category distribution
        category_dist = {}
        for question in questions:
            category = question.category.value
            category_dist[category] = category_dist.get(category, 0) + 1
        
        # Difficulty distribution
        difficulty_dist = {}
        for question in questions:
            difficulty = question.difficulty_level.value
            difficulty_dist[difficulty] = difficulty_dist.get(difficulty, 0) + 1
        
        # Tag distribution
        tag_dist = {}
        for question in questions:
            for tag in question.tags:
                tag_dist[tag] = tag_dist.get(tag, 0) + 1
        
        return {
            "total_questions": len(questions),
            "diversity_score": self.calculate_diversity_score(questions),
            "category_distribution": category_dist,
            "difficulty_distribution": difficulty_dist,
            "tag_distribution": dict(sorted(tag_dist.items(), key=lambda x: x[1], reverse=True)[:10]),
            "unique_categories": len(set(q.category for q in questions)),
            "unique_difficulties": len(set(q.difficulty_level for q in questions)),
            "unique_tags": len(set(tag for q in questions for tag in q.tags))
        }
