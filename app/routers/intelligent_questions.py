"""
API endpoints for intelligent question selection system.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.hybrid_ai_service import HybridAIService
from app.services.intelligent_question_selector import IntelligentQuestionSelector, UserContext
from app.services.question_diversity_engine import QuestionDiversityEngine
from app.models.intelligent_question_models import (
    QuestionSelectionRequest, QuestionSelectionResponse, UserContextModel,
    QuestionModel, RoleAnalysisModel, DiversityReport, IntelligentQuestionStats,
    QuestionSearchCriteria, QuestionBankStats, PerformanceMetrics
)
from app.utils.logger import get_logger
from app.utils.metrics import metrics
import time

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/intelligent-questions", tags=["intelligent-questions"])

@router.post("/select", response_model=QuestionSelectionResponse)
async def select_intelligent_questions(
    request: QuestionSelectionRequest,
    db: Session = Depends(get_db)
):
    """Select intelligent questions using role analysis and diversity algorithms."""
    try:
        start_time = time.time()
        
        # Initialize services
        ai_service = HybridAIService(db)
        selector = IntelligentQuestionSelector(db)
        
        # Convert user context
        user_context = None
        if request.user_context:
            user_context = UserContext(
                user_id=request.user_context.user_id,
                previous_questions=request.user_context.previous_questions,
                performance_history=request.user_context.performance_history,
                preferred_difficulty=request.user_context.preferred_difficulty.value if request.user_context.preferred_difficulty else None,
                weak_areas=request.user_context.weak_areas,
                strong_areas=request.user_context.strong_areas
            )
        
        # Select questions using intelligent selector
        selection_result = await selector.select_questions(
            role=request.role,
            job_description=request.job_description,
            user_context=user_context,
            target_count=request.target_count
        )
        
        # Convert to response format
        questions = [
            QuestionModel(
                id=q.id,
                question_text=q.question_text,
                category=q.category,
                difficulty_level=q.difficulty_level,
                tags=q.tags,
                role_relevance_score=q.role_relevance_score,
                quality_score=q.quality_score,
                user_history_score=q.user_history_score,
                source=selection_result.source
            ) for q in selection_result.questions
        ]
        
        role_analysis = RoleAnalysisModel(
            primary_role=selection_result.role_analysis.primary_role,
            required_skills=selection_result.role_analysis.required_skills,
            industry=selection_result.role_analysis.industry,
            seniority_level=selection_result.role_analysis.seniority_level,
            company_size=selection_result.role_analysis.company_size,
            tech_stack=selection_result.role_analysis.tech_stack,
            soft_skills=selection_result.role_analysis.soft_skills,
            job_function=selection_result.role_analysis.job_function,
            experience_years=selection_result.role_analysis.experience_years,
            education_requirements=selection_result.role_analysis.education_requirements or [],
            certifications=selection_result.role_analysis.certifications or []
        )
        
        response = QuestionSelectionResponse(
            questions=questions,
            source=selection_result.source,
            database_hit_rate=selection_result.database_hit_rate,
            ai_generated_count=selection_result.ai_generated_count,
            diversity_score=selection_result.diversity_score,
            selection_time=selection_result.selection_time,
            role_analysis=role_analysis,
            metadata={
                "request_time": time.time() - start_time,
                "prefer_database": request.prefer_database,
                "enable_ai_fallback": request.enable_ai_fallback
            }
        )
        
        # Record metrics
        metrics.record_ai_service_request(
            service="intelligent_selector",
            operation="question_selection",
            status="success",
            duration=response.selection_time
        )
        
        logger.info(f"Intelligent question selection completed: {len(questions)} questions selected")
        return response
        
    except Exception as e:
        logger.error(f"Error in intelligent question selection: {e}")
        metrics.record_ai_service_request(
            service="intelligent_selector",
            operation="question_selection",
            status="error",
            duration=time.time() - start_time
        )
        raise HTTPException(status_code=500, detail=f"Failed to select intelligent questions: {str(e)}")

@router.post("/generate-intelligent", response_model=Dict[str, Any])
async def generate_intelligent_questions(
    role: str,
    job_description: str,
    user_context: Optional[UserContextModel] = None,
    target_count: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Generate questions using intelligent selection with AI fallback."""
    try:
        start_time = time.time()
        
        # Initialize AI service
        ai_service = HybridAIService(db)
        
        # Convert user context
        user_context_obj = None
        if user_context:
            user_context_obj = UserContext(
                user_id=user_context.user_id,
                previous_questions=user_context.previous_questions,
                performance_history=user_context.performance_history,
                preferred_difficulty=user_context.preferred_difficulty.value if user_context.preferred_difficulty else None,
                weak_areas=user_context.weak_areas,
                strong_areas=user_context.strong_areas
            )
        
        # Generate intelligent questions
        result = await ai_service.generate_intelligent_questions(
            role=role,
            job_description=job_description,
            user_context=user_context_obj,
            target_count=target_count
        )
        
        # Add request metadata
        result["request_time"] = time.time() - start_time
        result["endpoint"] = "generate-intelligent"
        
        logger.info(f"Intelligent question generation completed: {len(result.get('questions', []))} questions")
        return result
        
    except Exception as e:
        logger.error(f"Error in intelligent question generation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate intelligent questions: {str(e)}")

@router.get("/diversity-report", response_model=DiversityReport)
async def get_diversity_report(
    questions: List[str] = Query(..., description="List of question texts to analyze"),
    db: Session = Depends(get_db)
):
    """Generate diversity report for a set of questions."""
    try:
        # Initialize diversity engine
        diversity_engine = QuestionDiversityEngine()
        
        # Convert question texts to Question objects (simplified)
        from app.services.question_diversity_engine import Question, QuestionCategory, DifficultyLevel
        question_objects = []
        for i, question_text in enumerate(questions):
            question = Question(
                id=f"temp_{i}",
                question_text=question_text,
                category=QuestionCategory.TECHNICAL,  # Default category
                difficulty_level=DifficultyLevel.MEDIUM,  # Default difficulty
                tags=[]
            )
            question_objects.append(question)
        
        # Generate diversity report
        report = diversity_engine.get_diversity_report(question_objects)
        
        return DiversityReport(
            total_questions=report["total_questions"],
            diversity_score=report["diversity_score"],
            category_distribution=report["category_distribution"],
            difficulty_distribution=report["difficulty_distribution"],
            tag_distribution=report["tag_distribution"],
            unique_categories=report["unique_categories"],
            unique_difficulties=report["unique_difficulties"],
            unique_tags=report["unique_tags"]
        )
        
    except Exception as e:
        logger.error(f"Error generating diversity report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate diversity report: {str(e)}")

@router.get("/stats", response_model=IntelligentQuestionStats)
async def get_intelligent_question_stats(
    db: Session = Depends(get_db)
):
    """Get statistics for intelligent question selection."""
    try:
        # This would typically query a metrics database
        # For now, return mock data
        stats = IntelligentQuestionStats(
            total_selections=0,
            database_hit_rate_avg=0.0,
            ai_generation_rate=0.0,
            diversity_score_avg=0.0,
            selection_time_avg=0.0,
            most_common_sources={},
            category_distribution={},
            difficulty_distribution={}
        )
        
        logger.info("Retrieved intelligent question statistics")
        return stats
        
    except Exception as e:
        logger.error(f"Error retrieving statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve statistics: {str(e)}")

@router.get("/question-bank-stats", response_model=QuestionBankStats)
async def get_question_bank_stats(
    db: Session = Depends(get_db)
):
    """Get statistics for the question bank."""
    try:
        # This would typically query the question bank database
        # For now, return mock data
        stats = QuestionBankStats(
            total_questions=0,
            questions_by_category={},
            questions_by_difficulty={},
            questions_by_role={},
            average_quality_score=0.0,
            most_used_tags=[],
            recent_additions=0,
            ai_generated_count=0,
            database_generated_count=0
        )
        
        logger.info("Retrieved question bank statistics")
        return stats
        
    except Exception as e:
        logger.error(f"Error retrieving question bank statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve question bank statistics: {str(e)}")

@router.post("/search-criteria")
async def search_questions_by_criteria(
    criteria: QuestionSearchCriteria,
    db: Session = Depends(get_db)
):
    """Search questions using intelligent criteria."""
    try:
        # Initialize selector
        selector = IntelligentQuestionSelector(db)
        
        # This would use the question bank service to search
        # For now, return mock data
        results = {
            "total_found": 0,
            "questions": [],
            "search_criteria": criteria.dict(),
            "search_time": 0.0
        }
        
        logger.info(f"Question search completed with criteria: {criteria.dict()}")
        return results
        
    except Exception as e:
        logger.error(f"Error searching questions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search questions: {str(e)}")

@router.get("/performance-metrics", response_model=PerformanceMetrics)
async def get_performance_metrics(
    db: Session = Depends(get_db)
):
    """Get performance metrics for intelligent question selection."""
    try:
        # This would typically query metrics from a monitoring system
        # For now, return mock data
        metrics_data = PerformanceMetrics(
            total_requests=0,
            successful_requests=0,
            failed_requests=0,
            average_selection_time=0.0,
            average_database_hit_rate=0.0,
            average_diversity_score=0.0,
            ai_generation_count=0,
            database_selection_count=0,
            hybrid_selection_count=0,
            error_rate=0.0
        )
        
        logger.info("Retrieved performance metrics")
        return metrics_data
        
    except Exception as e:
        logger.error(f"Error retrieving performance metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve performance metrics: {str(e)}")

@router.post("/analyze-role")
async def analyze_role(
    role: str,
    job_description: str,
    db: Session = Depends(get_db)
):
    """Analyze role requirements and return detailed analysis."""
    try:
        # Initialize role analysis service
        from app.services.role_analysis_service import RoleAnalysisService
        role_service = RoleAnalysisService()
        
        # Perform role analysis
        analysis = await role_service.analyze_role(role, job_description)
        
        # Convert to response format
        response = RoleAnalysisModel(
            primary_role=analysis.primary_role,
            required_skills=analysis.required_skills,
            industry=analysis.industry,
            seniority_level=analysis.seniority_level,
            company_size=analysis.company_size,
            tech_stack=analysis.tech_stack,
            soft_skills=analysis.soft_skills,
            job_function=analysis.job_function,
            experience_years=analysis.experience_years,
            education_requirements=analysis.education_requirements or [],
            certifications=analysis.certifications or []
        )
        
        logger.info(f"Role analysis completed for: {role}")
        return response
        
    except Exception as e:
        logger.error(f"Error in role analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze role: {str(e)}")

@router.get("/health")
async def health_check():
    """Health check for intelligent question selection system."""
    return {
        "status": "healthy",
        "service": "intelligent-question-selection",
        "timestamp": time.time(),
        "features": {
            "role_analysis": True,
            "diversity_engine": True,
            "intelligent_selector": True,
            "ai_fallback": True
        }
    }
