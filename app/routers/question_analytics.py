"""
Question Analytics API for Phase 2: Gradual Database Enhancement

This module provides API endpoints for monitoring and analyzing
the performance of the hybrid question generation system.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from app.database.connection import get_db_session
from app.database.question_database_models import (
    QuestionGenerationLog, QuestionTemplate, QuestionMatch, QuestionFeedback
)
from app.dependencies import get_current_user_required
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/question-analytics", tags=["Question Analytics"])

@router.get("/generation-stats")
async def get_generation_statistics(
    days: int = Query(7, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db_session)
):
    """Get comprehensive statistics about question generation methods."""
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get generation logs
        logs = db.query(QuestionGenerationLog).filter(
            and_(
                QuestionGenerationLog.created_at >= start_date,
                QuestionGenerationLog.created_at <= end_date
            )
        ).all()
        
        if not logs:
            return {
                "message": f"No generation data found for the last {days} days",
                "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
                "total_generations": 0
            }
        
        # Calculate statistics
        total_generations = len(logs)
        total_questions = sum(log.questions_generated for log in logs)
        total_db_questions = sum(log.questions_from_database for log in logs)
        total_ai_questions = sum(log.questions_from_ai for log in logs)
        total_tokens = sum(log.tokens_used or 0 for log in logs)
        total_cost = sum(log.estimated_cost or 0.0 for log in logs)
        
        # Method distribution
        method_counts = {}
        for log in logs:
            method_counts[log.generation_method] = method_counts.get(log.generation_method, 0) + 1
        
        # AI service distribution
        ai_service_counts = {}
        for log in logs:
            if log.ai_service_used:
                ai_service_counts[log.ai_service_used] = ai_service_counts.get(log.ai_service_used, 0) + 1
        
        # Performance metrics
        avg_processing_time = sum(log.processing_time_ms for log in logs) / total_generations
        avg_match_quality = sum(log.match_quality_score or 0 for log in logs) / total_generations
        
        # Cost savings calculation
        # Estimate what it would have cost to generate all questions with AI
        estimated_ai_cost = total_questions * 0.02  # Rough estimate: $0.02 per question
        cost_savings = estimated_ai_cost - total_cost
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "summary": {
                "total_generations": total_generations,
                "total_questions_generated": total_questions,
                "database_questions": total_db_questions,
                "ai_questions": total_ai_questions,
                "database_usage_percentage": (total_db_questions / total_questions * 100) if total_questions > 0 else 0,
                "ai_usage_percentage": (total_ai_questions / total_questions * 100) if total_questions > 0 else 0
            },
            "cost_analysis": {
                "total_tokens_used": total_tokens,
                "total_cost": round(total_cost, 4),
                "estimated_ai_cost": round(estimated_ai_cost, 4),
                "cost_savings": round(cost_savings, 4),
                "savings_percentage": round((cost_savings / estimated_ai_cost * 100) if estimated_ai_cost > 0 else 0, 2)
            },
            "method_distribution": method_counts,
            "ai_service_distribution": ai_service_counts,
            "performance_metrics": {
                "average_processing_time_ms": round(avg_processing_time, 2),
                "average_match_quality": round(avg_match_quality, 3)
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting generation statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/database-performance")
async def get_database_performance(
    days: int = Query(7, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db_session)
):
    """Get performance metrics for the question database."""
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get question templates
        total_questions = db.query(QuestionTemplate).filter(
            QuestionTemplate.is_active == True
        ).count()
        
        # Get question matches
        matches = db.query(QuestionMatch).filter(
            and_(
                QuestionMatch.created_at >= start_date,
                QuestionMatch.created_at <= end_date
            )
        ).all()
        
        # Calculate match statistics
        total_matches = len(matches)
        avg_confidence = sum(match.confidence_level for match in matches) / total_matches if total_matches > 0 else 0
        avg_match_score = sum(match.match_score for match in matches) / total_matches if total_matches > 0 else 0
        
        # Most used questions
        most_used_questions = db.query(
            QuestionTemplate.id,
            QuestionTemplate.question_text,
            QuestionTemplate.usage_count,
            QuestionTemplate.quality_score
        ).filter(
            QuestionTemplate.is_active == True
        ).order_by(desc(QuestionTemplate.usage_count)).limit(10).all()
        
        # Question type distribution
        type_distribution = db.query(
            QuestionTemplate.question_type,
            func.count(QuestionTemplate.id).label('count')
        ).filter(
            QuestionTemplate.is_active == True
        ).group_by(QuestionTemplate.question_type).all()
        
        # Difficulty distribution
        difficulty_distribution = db.query(
            QuestionTemplate.difficulty_level,
            func.count(QuestionTemplate.id).label('count')
        ).filter(
            QuestionTemplate.is_active == True
        ).group_by(QuestionTemplate.difficulty_level).all()
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "database_overview": {
                "total_active_questions": total_questions,
                "total_matches_last_period": total_matches,
                "average_confidence": round(avg_confidence, 3),
                "average_match_score": round(avg_match_score, 3)
            },
            "question_distribution": {
                "by_type": [{"type": item.question_type, "count": item.count} for item in type_distribution],
                "by_difficulty": [{"difficulty": item.difficulty_level, "count": item.count} for item in difficulty_distribution]
            },
            "most_used_questions": [
                {
                    "id": str(q.id),
                    "question_text": q.question_text[:100] + "..." if len(q.question_text) > 100 else q.question_text,
                    "usage_count": q.usage_count,
                    "quality_score": q.quality_score
                }
                for q in most_used_questions
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting database performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cost-optimization")
async def get_cost_optimization_metrics(
    days: int = Query(30, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db_session)
):
    """Get cost optimization metrics and trends."""
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get daily cost data
        daily_costs = db.query(
            func.date(QuestionGenerationLog.created_at).label('date'),
            func.sum(QuestionGenerationLog.estimated_cost).label('total_cost'),
            func.sum(QuestionGenerationLog.tokens_used).label('total_tokens'),
            func.count(QuestionGenerationLog.id).label('generation_count'),
            func.sum(QuestionGenerationLog.questions_from_database).label('db_questions'),
            func.sum(QuestionGenerationLog.questions_from_ai).label('ai_questions')
        ).filter(
            and_(
                QuestionGenerationLog.created_at >= start_date,
                QuestionGenerationLog.created_at <= end_date
            )
        ).group_by(func.date(QuestionGenerationLog.created_at)).order_by('date').all()
        
        # Calculate trends
        total_cost = sum(day.total_cost or 0 for day in daily_costs)
        total_tokens = sum(day.total_tokens or 0 for day in daily_costs)
        total_generations = sum(day.generation_count for day in daily_costs)
        total_db_questions = sum(day.db_questions for day in daily_costs)
        total_ai_questions = sum(day.ai_questions for day in daily_costs)
        
        # Calculate cost per question
        total_questions = total_db_questions + total_ai_questions
        cost_per_question = total_cost / total_questions if total_questions > 0 else 0
        
        # Calculate efficiency metrics
        db_efficiency = (total_db_questions / total_questions * 100) if total_questions > 0 else 0
        ai_efficiency = (total_ai_questions / total_questions * 100) if total_questions > 0 else 0
        
        # Estimate potential savings
        estimated_ai_only_cost = total_questions * 0.02  # $0.02 per question estimate
        potential_savings = estimated_ai_only_cost - total_cost
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "cost_summary": {
                "total_cost": round(total_cost, 4),
                "total_tokens": total_tokens,
                "total_generations": total_generations,
                "cost_per_question": round(cost_per_question, 4),
                "cost_per_generation": round(total_cost / total_generations, 4) if total_generations > 0 else 0
            },
            "efficiency_metrics": {
                "database_usage_percentage": round(db_efficiency, 2),
                "ai_usage_percentage": round(ai_efficiency, 2),
                "database_questions": total_db_questions,
                "ai_questions": total_ai_questions,
                "total_questions": total_questions
            },
            "savings_analysis": {
                "estimated_ai_only_cost": round(estimated_ai_only_cost, 4),
                "actual_cost": round(total_cost, 4),
                "cost_savings": round(potential_savings, 4),
                "savings_percentage": round((potential_savings / estimated_ai_only_cost * 100) if estimated_ai_only_cost > 0 else 0, 2)
            },
            "daily_trends": [
                {
                    "date": day.date.isoformat(),
                    "total_cost": round(day.total_cost or 0, 4),
                    "total_tokens": day.total_tokens or 0,
                    "generation_count": day.generation_count,
                    "db_questions": day.db_questions,
                    "ai_questions": day.ai_questions,
                    "db_percentage": round((day.db_questions / (day.db_questions + day.ai_questions) * 100) if (day.db_questions + day.ai_questions) > 0 else 0, 2)
                }
                for day in daily_costs
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting cost optimization metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/question-feedback")
async def get_question_feedback_analytics(
    days: int = Query(30, description="Number of days to analyze"),
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db_session)
):
    """Get analytics on user feedback for generated questions."""
    try:
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Get feedback data
        feedback_data = db.query(QuestionFeedback).filter(
            and_(
                QuestionFeedback.created_at >= start_date,
                QuestionFeedback.created_at <= end_date
            )
        ).all()
        
        if not feedback_data:
            return {
                "message": f"No feedback data found for the last {days} days",
                "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
                "total_feedback": 0
            }
        
        # Calculate average scores
        total_feedback = len(feedback_data)
        avg_relevance = sum(f.relevance_score for f in feedback_data) / total_feedback
        avg_difficulty = sum(f.difficulty_appropriateness for f in feedback_data) / total_feedback
        avg_quality = sum(f.quality_score for f in feedback_data) / total_feedback
        avg_satisfaction = sum(f.overall_satisfaction for f in feedback_data) / total_feedback
        
        # Score distribution
        score_distributions = {
            "relevance": {},
            "difficulty": {},
            "quality": {},
            "satisfaction": {}
        }
        
        for feedback in feedback_data:
            for score_type in score_distributions:
                score = getattr(feedback, f"{score_type}_score" if score_type != "satisfaction" else "overall_satisfaction")
                score_distributions[score_type][score] = score_distributions[score_type].get(score, 0) + 1
        
        # Recent feedback trends
        recent_feedback = db.query(QuestionFeedback).filter(
            and_(
                QuestionFeedback.created_at >= start_date,
                QuestionFeedback.created_at <= end_date
            )
        ).order_by(desc(QuestionFeedback.created_at)).limit(10).all()
        
        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "summary": {
                "total_feedback": total_feedback,
                "average_scores": {
                    "relevance": round(avg_relevance, 2),
                    "difficulty_appropriateness": round(avg_difficulty, 2),
                    "quality": round(avg_quality, 2),
                    "overall_satisfaction": round(avg_satisfaction, 2)
                }
            },
            "score_distributions": score_distributions,
            "recent_feedback": [
                {
                    "id": str(f.id),
                    "created_at": f.created_at.isoformat(),
                    "relevance_score": f.relevance_score,
                    "difficulty_score": f.difficulty_appropriateness,
                    "quality_score": f.quality_score,
                    "satisfaction_score": f.overall_satisfaction,
                    "feedback_text": f.feedback_text[:200] + "..." if f.feedback_text and len(f.feedback_text) > 200 else f.feedback_text
                }
                for f in recent_feedback
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting question feedback analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/optimization-recommendations")
async def get_optimization_recommendations(
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db_session)
):
    """Get recommendations for optimizing the question generation system."""
    try:
        recommendations = []
        
        # Get recent performance data
        recent_logs = db.query(QuestionGenerationLog).filter(
            QuestionGenerationLog.created_at >= datetime.now() - timedelta(days=7)
        ).all()
        
        if not recent_logs:
            return {
                "message": "Insufficient data for recommendations",
                "recommendations": []
            }
        
        # Calculate current metrics
        total_generations = len(recent_logs)
        total_questions = sum(log.questions_generated for log in recent_logs)
        total_db_questions = sum(log.questions_from_database for log in recent_logs)
        total_ai_questions = sum(log.questions_from_ai for log in recent_logs)
        db_usage_percentage = (total_db_questions / total_questions * 100) if total_questions > 0 else 0
        
        # Generate recommendations based on metrics
        if db_usage_percentage < 30:
            recommendations.append({
                "type": "database_expansion",
                "priority": "high",
                "title": "Expand Question Database",
                "description": f"Only {db_usage_percentage:.1f}% of questions are coming from the database. Consider adding more questions to reduce AI costs.",
                "impact": "High cost savings potential",
                "action": "Run question database seeder to add more questions"
            })
        
        if db_usage_percentage > 80:
            recommendations.append({
                "type": "quality_improvement",
                "priority": "medium",
                "title": "Improve Question Quality",
                "description": f"High database usage ({db_usage_percentage:.1f}%) is good, but ensure question quality remains high.",
                "impact": "Maintain user satisfaction",
                "action": "Review and update existing questions based on feedback"
            })
        
        # Check for high AI costs
        total_cost = sum(log.estimated_cost or 0 for log in recent_logs)
        if total_cost > 10:  # More than $10 in a week
            recommendations.append({
                "type": "cost_optimization",
                "priority": "high",
                "title": "Optimize AI Usage",
                "description": f"High AI costs detected (${total_cost:.2f} in 7 days). Consider improving question matching or adding more database questions.",
                "impact": "Significant cost reduction",
                "action": "Review token optimization settings and question matching algorithms"
            })
        
        # Check for low match quality
        avg_match_quality = sum(log.match_quality_score or 0 for log in recent_logs) / total_generations
        if avg_match_quality < 0.6:
            recommendations.append({
                "type": "matching_improvement",
                "priority": "medium",
                "title": "Improve Question Matching",
                "description": f"Low average match quality ({avg_match_quality:.2f}). Consider refining matching algorithms.",
                "impact": "Better user experience",
                "action": "Review and improve question matching criteria"
            })
        
        # Check for slow processing
        avg_processing_time = sum(log.processing_time_ms for log in recent_logs) / total_generations
        if avg_processing_time > 5000:  # More than 5 seconds
            recommendations.append({
                "type": "performance_optimization",
                "priority": "medium",
                "title": "Optimize Processing Speed",
                "description": f"Slow average processing time ({avg_processing_time:.0f}ms). Consider performance optimizations.",
                "impact": "Better user experience",
                "action": "Review database queries and caching strategies"
            })
        
        return {
            "analysis_period": "Last 7 days",
            "current_metrics": {
                "total_generations": total_generations,
                "database_usage_percentage": round(db_usage_percentage, 2),
                "average_match_quality": round(avg_match_quality, 3),
                "average_processing_time_ms": round(avg_processing_time, 2),
                "total_cost": round(total_cost, 4)
            },
            "recommendations": recommendations
        }
        
    except Exception as e:
        logger.error(f"Error getting optimization recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))
