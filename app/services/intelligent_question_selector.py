"""
Intelligent question selector with scoring, ranking, and AI fallback integration.
Core logic for selecting the best questions based on role analysis and user context.
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from app.models.role_analysis_models import RoleAnalysis
from app.services.role_analysis_service import RoleAnalysisService
from app.services.question_diversity_engine import QuestionDiversityEngine, Question, QuestionCategory, DifficultyLevel
from app.services.async_question_bank_service import AsyncQuestionBankService
from app.utils.logger import get_logger
from app.utils.metrics import metrics
import time

logger = get_logger(__name__)

@dataclass
class UserContext:
    """User context for personalization."""
    user_id: Optional[str] = None
    previous_questions: List[str] = None
    performance_history: Dict[str, float] = None
    preferred_difficulty: Optional[str] = None
    weak_areas: List[str] = None
    strong_areas: List[str] = None

@dataclass
class QuestionSelectionResult:
    """Result of intelligent question selection."""
    questions: List[Question]
    source: str  # "database", "ai_generated", "hybrid"
    database_hit_rate: float
    ai_generated_count: int
    diversity_score: float
    selection_time: float
    role_analysis: RoleAnalysis

class IntelligentQuestionSelector:
    """Intelligent question selector with scoring, ranking, and AI fallback."""
    
    def __init__(self, db_session=None):
        self.role_analysis_service = RoleAnalysisService()
        self.diversity_engine = QuestionDiversityEngine()
        self.question_bank_service = AsyncQuestionBankService(db_session) if db_session else None
        # AI service will be injected when needed to avoid circular imports
        self.ai_service = None
        
        # Selection configuration
        self.min_database_questions = 5  # Minimum questions to try from database first
        self.target_question_count = 10
        self.ai_fallback_threshold = 0.3  # Use AI if less than 30% of target from database
        
        # Scoring weights
        self.scoring_weights = {
            'role_relevance': 0.4,
            'quality': 0.3,
            'diversity': 0.2,
            'user_preference': 0.1
        }

    async def select_questions(self, 
                             role: str, 
                             job_description: str,
                             user_context: Optional[UserContext] = None,
                             target_count: int = 10) -> QuestionSelectionResult:
        """Orchestrate the question selection process."""
        start_time = time.time()
        
        try:
            logger.info(f"Starting intelligent question selection for role: {role}")
            
            # Step 1: Analyze role
            role_analysis = await self.role_analysis_service.analyze_role(role, job_description)
            
            # Step 2: Get database questions
            database_questions = await self._get_database_questions(role_analysis, user_context)
            
            # Step 3: Apply selection pipeline
            selected_questions = await self._apply_selection_pipeline(
                database_questions, role_analysis, user_context, target_count
            )
            
            return self._build_selection_result(selected_questions, role_analysis, start_time, database_questions)
            
        except Exception as e:
            return await self._handle_selection_error(e, role, job_description, target_count)
    
    async def _get_database_questions(self, role_analysis: RoleAnalysis, user_context: Optional[UserContext] = None) -> List[Question]:
        """Get questions from database with simplified logic."""
        return await self._find_database_questions(role_analysis, user_context)
    
    async def _apply_selection_pipeline(self, questions: List[Question], role_analysis: RoleAnalysis, 
                                      user_context: Optional[UserContext], target_count: int) -> List[Question]:
        """Apply the complete selection pipeline."""
        if not questions:
            return await self._generate_all_ai_questions(role_analysis, target_count)
        
        # Score, diversify, and potentially supplement with AI
        scored = await self._score_questions(questions, role_analysis, user_context)
        diverse = await self._ensure_diversity(scored, role_analysis, user_context)
        
        if len(diverse) < target_count * self.ai_fallback_threshold:
            ai_questions = await self._generate_ai_questions(role_analysis, diverse, target_count)
            diverse.extend(ai_questions)
        
        return diverse[:target_count]
    
    async def _generate_all_ai_questions(self, role_analysis: RoleAnalysis, target_count: int) -> List[Question]:
        """Generate all questions using AI when no database questions available."""
        ai_questions = await self._generate_ai_questions(role_analysis, [], target_count)
        return ai_questions[:target_count]
    
    def _build_selection_result(self, selected_questions: List[Question], role_analysis: RoleAnalysis, 
                              start_time: float, database_questions: List[Question]) -> QuestionSelectionResult:
        """Build the final selection result."""
        selection_time = time.time() - start_time
        database_hit_rate = len(database_questions) / max(1, len(selected_questions))
        diversity_score = self.diversity_engine.calculate_diversity_score(selected_questions)
        
        # Count AI generated questions
        ai_generated_count = sum(1 for q in selected_questions if q.id.startswith('ai_'))
        
        # Determine source
        if ai_generated_count == 0:
            source = "database"
        elif len(database_questions) == 0:
            source = "ai_generated"
        else:
            source = "hybrid"
        
        result = QuestionSelectionResult(
            questions=selected_questions,
            source=source,
            database_hit_rate=database_hit_rate,
            ai_generated_count=ai_generated_count,
            diversity_score=diversity_score,
            selection_time=selection_time,
            role_analysis=role_analysis
        )
        
        # Record metrics
        asyncio.create_task(self._record_selection_metrics(result))
        
        logger.info(f"Question selection completed: {len(selected_questions)} questions, "
                   f"database hit rate: {database_hit_rate:.2%}, "
                   f"diversity score: {diversity_score:.2f}")
        
        return result
    
    async def _handle_selection_error(self, error: Exception, role: str, job_description: str, target_count: int) -> QuestionSelectionResult:
        """Handle selection errors with fallback."""
        logger.error(f"Error in intelligent question selection: {error}")
        return await self._fallback_to_ai_generation(role, job_description, target_count)

    async def _find_database_questions(self, 
                                     role_analysis: RoleAnalysis, 
                                     user_context: Optional[UserContext] = None) -> List[Question]:
        """Find compatible questions from the database."""
        if not self.question_bank_service:
            logger.warning("Question bank service not available, skipping database search")
            return []
        
        try:
            # Get relevant categories and difficulties for the role
            categories = self.role_analysis_service.get_question_categories_for_role(role_analysis)
            difficulties = self.role_analysis_service.get_difficulty_levels_for_role(role_analysis)
            
            # Search for questions matching role requirements
            search_criteria = {
                'role': role_analysis.primary_role,
                'industry': role_analysis.industry.value,
                'seniority_level': role_analysis.seniority_level.value,
                'categories': categories,
                'difficulties': difficulties,
                'skills': role_analysis.required_skills[:5],  # Top 5 skills
                'limit': 50  # Get more than needed for better selection
            }
            
            # Query the question bank
            db_questions = await self.question_bank_service.search_questions_by_criteria(search_criteria)
            
            # Convert to Question objects
            questions = []
            for db_q in db_questions:
                question = Question(
                    id=str(db_q.id),
                    question_text=db_q.question_text,
                    category=QuestionCategory(db_q.category),
                    difficulty_level=DifficultyLevel(db_q.difficulty_level),
                    tags=db_q.tags or [],
                    role_relevance_score=await self._calculate_role_relevance(db_q, role_analysis),
                    quality_score=db_q.quality_score or 0.5
                )
                questions.append(question)
            
            logger.info(f"Found {len(questions)} database questions for role analysis")
            return questions
            
        except Exception as e:
            logger.error(f"Error finding database questions: {e}")
            return []

    async def _score_questions(self, 
                             questions: List[Question], 
                             role_analysis: RoleAnalysis,
                             user_context: Optional[UserContext] = None) -> List[Question]:
        """Score questions based on relevance, quality, and user preferences."""
        for question in questions:
            # Calculate role relevance score
            role_relevance = question.role_relevance_score
            
            # Calculate quality score
            quality_score = question.quality_score
            
            # Calculate diversity score (will be updated after diversity selection)
            diversity_score = 0.5  # Default
            
            # Calculate user preference score
            user_preference_score = await self._calculate_user_preference_score(question, user_context)
            
            # Calculate composite score
            composite_score = (
                role_relevance * self.scoring_weights['role_relevance'] +
                quality_score * self.scoring_weights['quality'] +
                diversity_score * self.scoring_weights['diversity'] +
                user_preference_score * self.scoring_weights['user_preference']
            )
            
            question.composite_score = composite_score
        
        # Sort by composite score
        return sorted(questions, key=lambda q: q.composite_score, reverse=True)

    async def _calculate_role_relevance(self, db_question, role_analysis: RoleAnalysis) -> float:
        """Calculate how relevant a question is to the role."""
        relevance_score = 0.0
        
        # Role match
        if db_question.role and db_question.role.lower() == role_analysis.primary_role.lower():
            relevance_score += 0.3
        
        # Industry match
        if db_question.industry and db_question.industry == role_analysis.industry.value:
            relevance_score += 0.2
        
        # Seniority match
        if db_question.seniority_level and db_question.seniority_level == role_analysis.seniority_level.value:
            relevance_score += 0.2
        
        # Skills match
        if db_question.tags:
            matching_skills = set(db_question.tags) & set(role_analysis.required_skills)
            if matching_skills:
                relevance_score += min(0.3, len(matching_skills) * 0.1)
        
        return min(1.0, relevance_score)

    async def _calculate_user_preference_score(self, 
                                             question: Question, 
                                             user_context: Optional[UserContext] = None) -> float:
        """Calculate user preference score based on history and preferences."""
        if not user_context:
            return 0.5  # Neutral score
        
        score = 0.5  # Base score
        
        # Avoid recently asked questions
        if user_context.previous_questions and question.id in user_context.previous_questions:
            score -= 0.3
        
        # Prefer questions in strong areas
        if user_context.strong_areas:
            matching_areas = set(question.tags) & set(user_context.strong_areas)
            if matching_areas:
                score += 0.2
        
        # Avoid questions in weak areas (unless user wants to practice)
        if user_context.weak_areas:
            matching_areas = set(question.tags) & set(user_context.weak_areas)
            if matching_areas:
                score -= 0.1
        
        # Difficulty preference
        if user_context.preferred_difficulty and question.difficulty_level.value == user_context.preferred_difficulty:
            score += 0.1
        
        return max(0.0, min(1.0, score))

    async def _ensure_diversity(self, 
                              questions: List[Question], 
                              role_analysis: RoleAnalysis,
                              user_context: Optional[UserContext] = None) -> List[Question]:
        """Ensure question diversity using the diversity engine."""
        if not questions:
            return []
        
        # Determine role type for diversity configuration
        role_type = role_analysis.seniority_level.value
        
        # Get user history for diversity
        user_history = user_context.previous_questions if user_context else None
        
        # Apply diversity algorithms
        diverse_questions = await self.diversity_engine.ensure_diversity(
            questions, 
            self.target_question_count,
            role_type,
            user_history
        )
        
        return diverse_questions

    async def _generate_ai_questions(self, 
                                   role_analysis: RoleAnalysis, 
                                   existing_questions: List[Question],
                                   target_count: int) -> List[Question]:
        """Generate AI questions to fill gaps."""
        try:
            # Identify missing question types
            missing_types = self._identify_missing_question_types(existing_questions, role_analysis)
            
            if not missing_types:
                return []
            
            # Generate questions for missing types
            ai_questions = []
            for question_type in missing_types:
                try:
                    # Generate questions using AI service (if available)
                    if self.ai_service is None:
                        # Import here to avoid circular imports
                        from app.services.hybrid_ai_service import HybridAIService
                        self.ai_service = HybridAIService()
                    
                    ai_response = await self.ai_service.generate_interview_questions(
                        role=role_analysis.primary_role,
                        job_description=f"Industry: {role_analysis.industry.value}, "
                                      f"Seniority: {role_analysis.seniority_level.value}, "
                                      f"Skills: {', '.join(role_analysis.required_skills[:5])}",
                        preferred_service="openai"
                    )
                    
                    # Convert AI response to Question objects
                    for i, question_text in enumerate(ai_response.questions[:2]):  # Limit to 2 per type
                        question = Question(
                            id=f"ai_generated_{question_type}_{i}",
                            question_text=question_text,
                            category=QuestionCategory(question_type),
                            difficulty_level=DifficultyLevel.MEDIUM,  # Default difficulty
                            tags=role_analysis.required_skills[:3],
                            role_relevance_score=0.8,  # High relevance for AI-generated
                            quality_score=0.7  # Good quality for AI-generated
                        )
                        ai_questions.append(question)
                        
                except Exception as e:
                    logger.error(f"Error generating AI questions for type {question_type}: {e}")
                    continue
            
            logger.info(f"Generated {len(ai_questions)} AI questions")
            return ai_questions
            
        except Exception as e:
            logger.error(f"Error in AI question generation: {e}")
            return []

    def _identify_missing_question_types(self, 
                                       existing_questions: List[Question], 
                                       role_analysis: RoleAnalysis) -> List[str]:
        """Identify missing question types that should be generated."""
        existing_categories = set(q.category.value for q in existing_questions)
        expected_categories = self.role_analysis_service.get_question_categories_for_role(role_analysis)
        
        missing_categories = []
        for category in expected_categories:
            if category not in existing_categories:
                missing_categories.append(category)
        
        return missing_categories

    async def _record_selection_metrics(self, result: QuestionSelectionResult):
        """Record metrics for question selection."""
        try:
            # Record selection metrics
            metrics.record_ai_service_request(
                service="intelligent_selector",
                operation="question_selection",
                status="success",
                duration=result.selection_time
            )
            
            # Record database hit rate
            if result.database_hit_rate > 0.8:
                hit_rate_category = "high"
            elif result.database_hit_rate > 0.5:
                hit_rate_category = "medium"
            else:
                hit_rate_category = "low"
            
            # This would be a custom metric - you might want to add it to your metrics system
            logger.info(f"Question selection metrics - "
                       f"Source: {result.source}, "
                       f"Database hit rate: {result.database_hit_rate:.2%}, "
                       f"Diversity score: {result.diversity_score:.2f}, "
                       f"AI generated: {result.ai_generated_count}")
            
        except Exception as e:
            logger.error(f"Error recording selection metrics: {e}")

    def _create_question_from_ai_response(self, question_text: str, question_type: str, 
                                        role_analysis: RoleAnalysis, index: int) -> Question:
        """Factory method to create Question objects from AI responses."""
        return Question(
            id=f"ai_{question_type}_{index}",
            question_text=question_text,
            category=QuestionCategory(question_type),
            difficulty_level=self._get_default_difficulty(role_analysis),
            tags=role_analysis.required_skills[:3] if role_analysis else [],
            role_relevance_score=0.8,
            quality_score=0.7
        )
    
    def _get_default_difficulty(self, role_analysis: RoleAnalysis) -> DifficultyLevel:
        """Get default difficulty level based on role analysis."""
        if not role_analysis:
            return DifficultyLevel.MEDIUM
        
        if role_analysis.seniority_level.value in ['junior', 'entry']:
            return DifficultyLevel.EASY
        elif role_analysis.seniority_level.value in ['senior', 'staff', 'principal']:
            return DifficultyLevel.HARD
        else:
            return DifficultyLevel.MEDIUM
    
    async def _fallback_to_ai_generation(self, 
                                       role: str, 
                                       job_description: str, 
                                       target_count: int) -> QuestionSelectionResult:
        """Fallback to AI generation when intelligent selection fails."""
        try:
            logger.warning("Falling back to AI generation due to selection error")
            
            # Generate questions using AI service (if available)
            if self.ai_service is None:
                # Import here to avoid circular imports
                from app.services.hybrid_ai_service import HybridAIService
                self.ai_service = HybridAIService()
            
            ai_response = await self.ai_service.generate_interview_questions(
                role=role,
                job_description=job_description,
                preferred_service="openai"
            )
            
            # Convert to Question objects using factory method
            questions = []
            for i, question_text in enumerate(ai_response.questions[:target_count]):
                question = self._create_question_from_ai_response(
                    question_text, "fallback", None, i
                )
                questions.append(question)
            
            return QuestionSelectionResult(
                questions=questions,
                source="ai_generated",
                database_hit_rate=0.0,
                ai_generated_count=len(questions),
                diversity_score=0.5,  # Default diversity score
                selection_time=0.0,
                role_analysis=RoleAnalysis(
                    primary_role=role,
                    required_skills=[],
                    industry=None,
                    seniority_level=None,
                    company_size=None,
                    tech_stack=[],
                    soft_skills=[],
                    job_function="software_development"
                )
            )
            
        except Exception as e:
            logger.error(f"Error in AI fallback generation: {e}")
            # Return empty result
            return QuestionSelectionResult(
                questions=[],
                source="error",
                database_hit_rate=0.0,
                ai_generated_count=0,
                diversity_score=0.0,
                selection_time=0.0,
                role_analysis=None
            )

    def get_selection_report(self, result: QuestionSelectionResult) -> Dict[str, Any]:
        """Generate a detailed selection report."""
        return {
            "selection_summary": {
                "total_questions": len(result.questions),
                "source": result.source,
                "database_hit_rate": result.database_hit_rate,
                "ai_generated_count": result.ai_generated_count,
                "diversity_score": result.diversity_score,
                "selection_time": result.selection_time
            },
            "role_analysis": {
                "primary_role": result.role_analysis.primary_role if result.role_analysis else "unknown",
                "industry": result.role_analysis.industry.value if result.role_analysis else "unknown",
                "seniority_level": result.role_analysis.seniority_level.value if result.role_analysis else "unknown",
                "required_skills": result.role_analysis.required_skills if result.role_analysis else [],
                "tech_stack": result.role_analysis.tech_stack if result.role_analysis else []
            },
            "question_breakdown": {
                "categories": [q.category.value for q in result.questions],
                "difficulties": [q.difficulty_level.value for q in result.questions],
                "average_relevance_score": sum(q.role_relevance_score for q in result.questions) / max(1, len(result.questions)),
                "average_quality_score": sum(q.quality_score for q in result.questions) / max(1, len(result.questions))
            }
        }
