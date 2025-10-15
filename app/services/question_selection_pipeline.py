"""
Question Selection Pipeline for InterviewIQ.

This module implements a pipeline pattern for question selection,
replacing complex nested logic with clean, composable components.
"""
from typing import List, Dict, Any, Optional, Protocol
from dataclasses import dataclass
from abc import ABC, abstractmethod
from app.database.models import Question
from app.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class SelectionContext:
    """Context for question selection pipeline."""
    role: str
    job_description: str
    target_count: int
    user_preferences: Optional[Dict[str, Any]] = None
    session_history: Optional[List[str]] = None

@dataclass
class SelectionResult:
    """Result of question selection pipeline."""
    questions: List[Question]
    selection_metadata: Dict[str, Any]
    pipeline_steps: List[str]

class PipelineStep(ABC):
    """Base class for pipeline steps."""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def process(self, questions: List[Question], context: SelectionContext) -> List[Question]:
        """Process questions through this pipeline step."""
        pass

class RoleAnalyzer(PipelineStep):
    """Analyzes role requirements and filters questions accordingly."""
    
    def __init__(self):
        super().__init__("role_analyzer")
    
    def process(self, questions: List[Question], context: SelectionContext) -> List[Question]:
        """Filter questions based on role analysis."""
        logger.debug(f"Role analysis for: {context.role}")
        
        # Simple role-based filtering
        role_lower = context.role.lower()
        
        if "senior" in role_lower or "lead" in role_lower:
            # Prefer harder questions for senior roles
            filtered = [q for q in questions if q.difficulty_level in ["medium", "hard"]]
        elif "junior" in role_lower or "entry" in role_lower:
            # Prefer easier questions for junior roles
            filtered = [q for q in questions if q.difficulty_level in ["easy", "medium"]]
        else:
            # Default to all questions for mid-level roles
            filtered = questions
        
        logger.debug(f"Role analysis filtered {len(questions)} -> {len(filtered)} questions")
        return filtered

class CompatibilityFilter(PipelineStep):
    """Filters questions based on compatibility with job requirements."""
    
    def __init__(self):
        super().__init__("compatibility_filter")
    
    def process(self, questions: List[Question], context: SelectionContext) -> List[Question]:
        """Filter questions based on job description compatibility."""
        logger.debug("Applying compatibility filter")
        
        # Extract key terms from job description
        job_terms = set(context.job_description.lower().split())
        
        compatible_questions = []
        for question in questions:
            # Simple compatibility check based on category and metadata
            if self._is_compatible(question, job_terms):
                compatible_questions.append(question)
        
        logger.debug(f"Compatibility filter: {len(questions)} -> {len(compatible_questions)} questions")
        return compatible_questions
    
    def _is_compatible(self, question: Question, job_terms: set) -> bool:
        """Check if question is compatible with job terms."""
        # Simple compatibility logic
        question_terms = set(question.question_text.lower().split())
        common_terms = job_terms.intersection(question_terms)
        
        # If there are common terms, consider it compatible
        return len(common_terms) > 0 or question.category in ["behavioral", "general"]

class DiversityEnsurer(PipelineStep):
    """Ensures question diversity across categories and difficulties."""
    
    def __init__(self):
        super().__init__("diversity_ensurer")
    
    def process(self, questions: List[Question], context: SelectionContext) -> List[Question]:
        """Ensure diversity in selected questions."""
        logger.debug("Ensuring question diversity")
        
        if len(questions) <= context.target_count:
            return questions
        
        # Group questions by category and difficulty
        grouped = self._group_questions(questions)
        
        # Select diverse questions
        diverse_questions = self._select_diverse_questions(grouped, context.target_count)
        
        logger.debug(f"Diversity ensurer: {len(questions)} -> {len(diverse_questions)} questions")
        return diverse_questions
    
    def _group_questions(self, questions: List[Question]) -> Dict[str, List[Question]]:
        """Group questions by category and difficulty."""
        grouped = {}
        for question in questions:
            key = f"{question.category}_{question.difficulty_level}"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(question)
        return grouped
    
    def _select_diverse_questions(self, grouped: Dict[str, List[Question]], target_count: int) -> List[Question]:
        """Select diverse questions from groups."""
        selected = []
        groups = list(grouped.keys())
        
        # Round-robin selection to ensure diversity
        while len(selected) < target_count and groups:
            for group_key in groups[:]:
                if len(selected) >= target_count:
                    break
                
                if grouped[group_key]:
                    selected.append(grouped[group_key].pop(0))
                else:
                    groups.remove(group_key)
        
        return selected

class QualityRanker(PipelineStep):
    """Ranks questions by quality and relevance."""
    
    def __init__(self):
        super().__init__("quality_ranker")
    
    def process(self, questions: List[Question], context: SelectionContext) -> List[Question]:
        """Rank questions by quality and relevance."""
        logger.debug("Ranking questions by quality")
        
        # Sort by usage count (prefer less used questions) and quality
        ranked = sorted(questions, key=lambda q: (q.usage_count, -getattr(q, 'quality_score', 0)))
        
        # Take top questions up to target count
        result = ranked[:context.target_count]
        
        logger.debug(f"Quality ranker: {len(questions)} -> {len(result)} questions")
        return result

class QuestionSelectionPipeline:
    """Main pipeline for question selection."""
    
    def __init__(self):
        self.steps = [
            RoleAnalyzer(),
            CompatibilityFilter(),
            DiversityEnsurer(),
            QualityRanker()
        ]
    
    def process(self, questions: List[Question], context: SelectionContext) -> SelectionResult:
        """Process questions through the entire pipeline."""
        logger.info(f"Starting question selection pipeline for role: {context.role}")
        
        current_questions = questions
        executed_steps = []
        metadata = {
            "initial_count": len(questions),
            "target_count": context.target_count,
            "role": context.role
        }
        
        # Execute each pipeline step
        for step in self.steps:
            try:
                current_questions = step.process(current_questions, context)
                executed_steps.append(step.name)
                
                metadata[f"{step.name}_output_count"] = len(current_questions)
                
                logger.debug(f"Step {step.name} completed: {len(current_questions)} questions")
                
            except Exception as e:
                logger.error(f"Pipeline step {step.name} failed: {e}")
                # Continue with remaining questions
                continue
        
        metadata["final_count"] = len(current_questions)
        metadata["executed_steps"] = executed_steps
        
        result = SelectionResult(
            questions=current_questions,
            selection_metadata=metadata,
            pipeline_steps=executed_steps
        )
        
        logger.info(f"Pipeline completed: {len(current_questions)} questions selected")
        return result
