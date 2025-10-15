"""
Validation Pipeline for question bank validation.
Replaces monolithic validation with clean pipeline pattern.
"""

from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass
from app.database.models import Question
from app.utils.logger import get_logger

logger = get_logger(__name__)

@dataclass
class ValidationStep:
    """Represents a validation step in the pipeline."""
    name: str
    validator_func: Callable
    required: bool = True
    weight: float = 1.0

class ValidationPipeline:
    """Pipeline for processing validation steps."""
    
    def __init__(self):
        self.steps = []
        self.results = {
            "total_questions": 0,
            "valid_questions": 0,
            "issues_found": 0,
            "quality_score": 0.0,
            "issues": []
        }
    
    def add_step(self, step: ValidationStep):
        """Add a validation step to the pipeline."""
        self.steps.append(step)
        return self
    
    def execute(self, questions: List[Question]) -> Dict[str, Any]:
        """Execute the validation pipeline."""
        self.results["total_questions"] = len(questions)
        
        if not questions:
            logger.warning("No questions provided for validation")
            return self.results
        
        logger.info(f"Starting validation pipeline with {len(questions)} questions")
        
        for step in self.steps:
            try:
                logger.debug(f"Executing validation step: {step.name}")
                step_results = step.validator_func(questions)
                
                if step_results:
                    self._merge_results(step_results, step.weight)
                
            except Exception as e:
                logger.error(f"Error in validation step {step.name}: {e}")
                if step.required:
                    self.results["issues"].append({
                        "type": "validation_error",
                        "step": step.name,
                        "message": f"Validation step failed: {str(e)}"
                    })
        
        self._calculate_final_score()
        logger.info("Validation pipeline completed")
        return self.results
    
    def _merge_results(self, step_results: Dict[str, Any], weight: float):
        """Merge results from a validation step."""
        if "issues" in step_results:
            for issue in step_results["issues"]:
                issue["weight"] = weight
                self.results["issues"].append(issue)
                self.results["issues_found"] += 1
    
    def _calculate_final_score(self):
        """Calculate final quality score."""
        total_issues = self.results["issues_found"]
        total_questions = self.results["total_questions"]
        
        if total_questions == 0:
            self.results["quality_score"] = 0.0
        else:
            # Calculate score based on issues per question
            issues_per_question = total_issues / total_questions
            self.results["quality_score"] = max(0.0, 1.0 - (issues_per_question * 0.1))
        
        self.results["valid_questions"] = total_questions - total_issues

class QuestionBankValidationPipeline:
    """Specialized validation pipeline for question bank."""
    
    def __init__(self):
        self.pipeline = ValidationPipeline()
        self._setup_validation_steps()
    
    def _setup_validation_steps(self):
        """Setup the validation pipeline steps."""
        self.pipeline.add_step(ValidationStep(
            name="text_validation",
            validator_func=self._validate_question_text,
            required=True,
            weight=1.0
        )).add_step(ValidationStep(
            name="metadata_validation",
            validator_func=self._validate_metadata,
            required=True,
            weight=0.8
        )).add_step(ValidationStep(
            name="category_validation",
            validator_func=self._validate_categories,
            required=False,
            weight=0.6
        )).add_step(ValidationStep(
            name="difficulty_validation",
            validator_func=self._validate_difficulty_levels,
            required=False,
            weight=0.6
        )).add_step(ValidationStep(
            name="duplicate_validation",
            validator_func=self._validate_duplicates,
            required=False,
            weight=0.4
        ))
    
    def run_validation(self, questions: List[Question]) -> Dict[str, Any]:
        """Run comprehensive validation using pipeline."""
        return self.pipeline.execute(questions)
    
    def _validate_question_text(self, questions: List[Question]) -> Dict[str, Any]:
        """Validate question text quality."""
        issues = []
        
        for question in questions:
            text = question.question_text or ""
            
            # Text length validation
            if len(text.strip()) < 10:
                issues.append({
                    "type": "text_validation",
                    "question_id": str(question.id),
                    "message": "Question text is too short or empty"
                })
            elif len(text) > 1000:
                issues.append({
                    "type": "text_validation",
                    "question_id": str(question.id),
                    "message": f"Question text is too long ({len(text)} characters)"
                })
            
            # Punctuation validation
            if text and not text.endswith(('?', '.', '!')):
                issues.append({
                    "type": "text_validation",
                    "question_id": str(question.id),
                    "message": "Question should end with proper punctuation"
                })
        
        return {"issues": issues}
    
    def _validate_metadata(self, questions: List[Question]) -> Dict[str, Any]:
        """Validate question metadata."""
        issues = []
        
        for question in questions:
            # Check required fields
            if not question.category:
                issues.append({
                    "type": "metadata_validation",
                    "question_id": str(question.id),
                    "message": "Missing category"
                })
            
            if not question.difficulty_level:
                issues.append({
                    "type": "metadata_validation",
                    "question_id": str(question.id),
                    "message": "Missing difficulty level"
                })
        
        return {"issues": issues}
    
    def _validate_categories(self, questions: List[Question]) -> Dict[str, Any]:
        """Validate question categories."""
        issues = []
        valid_categories = {"technical", "behavioral", "system_design", "leadership", "problem_solving"}
        
        for question in questions:
            if question.category and question.category not in valid_categories:
                issues.append({
                    "type": "category_validation",
                    "question_id": str(question.id),
                    "message": f"Invalid category: {question.category}"
                })
        
        return {"issues": issues}
    
    def _validate_difficulty_levels(self, questions: List[Question]) -> Dict[str, Any]:
        """Validate difficulty levels."""
        issues = []
        valid_difficulties = {"easy", "medium", "hard"}
        
        for question in questions:
            if question.difficulty_level and question.difficulty_level not in valid_difficulties:
                issues.append({
                    "type": "difficulty_validation",
                    "question_id": str(question.id),
                    "message": f"Invalid difficulty level: {question.difficulty_level}"
                })
        
        return {"issues": issues}
    
    def _validate_duplicates(self, questions: List[Question]) -> Dict[str, Any]:
        """Validate for duplicate questions."""
        issues = []
        seen_texts = set()
        
        for question in questions:
            text = question.question_text.lower().strip()
            if text in seen_texts:
                issues.append({
                    "type": "duplicate_validation",
                    "question_id": str(question.id),
                    "message": "Duplicate question text found"
                })
            else:
                seen_texts.add(text)
        
        return {"issues": issues}
