"""
Question Analytics Service

Provides analytics and reporting for question bank performance.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from app.database.models import Question, SessionQuestion, Answer
from app.utils.logger import get_logger

logger = get_logger(__name__)


class QuestionAnalyticsService:
    """Service for question analytics and reporting."""
    
    def __init__(self, db: Session):
        """
        Initialize QuestionAnalyticsService.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def get_question_performance(
        self,
        question_id: Optional[str] = None,
        category: Optional[str] = None,
        time_period: str = "30d"
    ) -> Dict[str, Any]:
        """
        Get question performance analytics.
        
        Args:
            question_id: Optional specific question ID
            category: Optional category filter
            time_period: Time period (e.g., "7d", "30d", "90d")
            
        Returns:
            Dictionary with performance data
        """
        try:
            # Parse time period
            days = int(time_period.rstrip('d'))
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Build query - use Question model's pre-calculated metrics
            if question_id:
                from uuid import UUID
                question_uuid = UUID(question_id)
                question = self.db.execute(
                    select(Question).where(Question.id == question_uuid)
                ).scalar_one_or_none()
                
                if not question:
                    return {
                        "question_id": question_id,
                        "category": category,
                        "time_period": time_period,
                        "total_uses": 0,
                        "average_score": None,
                        "success_rate": None,
                        "performance_trend": []
                    }
                
                # Count uses in time period
                total_uses = self.db.execute(
                    select(func.count(SessionQuestion.id)).where(
                        and_(
                            SessionQuestion.question_id == question_uuid,
                            SessionQuestion.created_at >= start_date
                        )
                    )
                ).scalar() or 0
                
                return {
                    "question_id": question_id,
                    "category": category,
                    "time_period": time_period,
                    "total_uses": total_uses,
                    "average_score": float(question.average_score) if question.average_score else None,
                    "success_rate": float(question.success_rate) if question.success_rate else None,
                    "performance_trend": []  # Could be enhanced with time-series data
                }
            elif category:
                # Get questions in category and aggregate their metrics
                questions = self.db.execute(
                    select(Question).where(Question.category == category)
                ).scalars().all()
                
                total_uses = sum(q.usage_count for q in questions)
                avg_scores = [q.average_score for q in questions if q.average_score is not None]
                success_rates = [q.success_rate for q in questions if q.success_rate is not None]
                
                return {
                    "question_id": question_id,
                    "category": category,
                    "time_period": time_period,
                    "total_uses": total_uses,
                    "average_score": float(sum(avg_scores) / len(avg_scores)) if avg_scores else None,
                    "success_rate": float(sum(success_rates) / len(success_rates)) if success_rates else None,
                    "performance_trend": []
                }
            else:
                # Aggregate across all questions
                questions = self.db.execute(select(Question)).scalars().all()
                
                total_uses = sum(q.usage_count for q in questions)
                avg_scores = [q.average_score for q in questions if q.average_score is not None]
                success_rates = [q.success_rate for q in questions if q.success_rate is not None]
                
                return {
                    "question_id": question_id,
                    "category": category,
                    "time_period": time_period,
                    "total_uses": total_uses,
                    "average_score": float(sum(avg_scores) / len(avg_scores)) if avg_scores else None,
                    "success_rate": float(sum(success_rates) / len(success_rates)) if success_rates else None,
                    "performance_trend": []
                }
            
        except Exception as e:
            logger.error(f"Error getting question performance: {e}")
            return {
                "question_id": question_id,
                "category": category,
                "time_period": time_period,
                "total_uses": 0,
                "average_score": None,
                "success_rate": None,
                "performance_trend": []
            }
    
    def get_usage_stats(self, time_period: str = "30d") -> Dict[str, Any]:
        """
        Get question usage statistics.
        
        Args:
            time_period: Time period (e.g., "7d", "30d", "90d")
            
        Returns:
            Dictionary with usage statistics
        """
        try:
            # Parse time period
            days = int(time_period.rstrip('d'))
            start_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            # Total questions
            total_questions = self.db.execute(
                select(func.count(Question.id))
            ).scalar() or 0
            
            # Total uses
            total_uses = self.db.execute(
                select(func.count(SessionQuestion.id)).where(
                    SessionQuestion.created_at >= start_date
                )
            ).scalar() or 0
            
            # Most used questions
            most_used = self.db.execute(
                select(
                    Question.id,
                    Question.question_text,
                    Question.category,
                    func.count(SessionQuestion.id).label('usage_count')
                ).join(
                    SessionQuestion, SessionQuestion.question_id == Question.id
                ).where(
                    SessionQuestion.created_at >= start_date
                ).group_by(
                    Question.id, Question.question_text, Question.category
                ).order_by(
                    func.count(SessionQuestion.id).desc()
                ).limit(10)
            ).all()
            
            # Usage by category
            usage_by_category = self.db.execute(
                select(
                    Question.category,
                    func.count(SessionQuestion.id).label('count')
                ).join(
                    SessionQuestion, SessionQuestion.question_id == Question.id
                ).where(
                    SessionQuestion.created_at >= start_date
                ).group_by(Question.category)
            ).all()
            
            # Usage by difficulty
            usage_by_difficulty = self.db.execute(
                select(
                    Question.difficulty_level,
                    func.count(SessionQuestion.id).label('count')
                ).join(
                    SessionQuestion, SessionQuestion.question_id == Question.id
                ).where(
                    SessionQuestion.created_at >= start_date
                ).group_by(Question.difficulty_level)
            ).all()
            
            return {
                "time_period": time_period,
                "total_questions": total_questions,
                "total_uses": total_uses,
                "most_used_questions": [
                    {
                        "id": str(q.id),
                        "question_text": q.question_text[:100],
                        "category": q.category,
                        "usage_count": q.usage_count
                    }
                    for q in most_used
                ],
                "least_used_questions": [],  # Could be enhanced
                "usage_by_category": {cat: count for cat, count in usage_by_category},
                "usage_by_difficulty": {diff: count for diff, count in usage_by_difficulty}
            }
            
        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            return {
                "time_period": time_period,
                "total_questions": 0,
                "total_uses": 0,
                "most_used_questions": [],
                "least_used_questions": [],
                "usage_by_category": {},
                "usage_by_difficulty": {}
            }
    
    def get_system_overview(self) -> Dict[str, Any]:
        """
        Get system overview analytics.
        
        Returns:
            Dictionary with system overview data
        """
        try:
            # Total questions
            total_questions = self.db.execute(
                select(func.count(Question.id))
            ).scalar() or 0
            
            # Questions by category
            questions_by_category = self.db.execute(
                select(
                    Question.category,
                    func.count(Question.id).label('count')
                ).group_by(Question.category)
            ).all()
            
            # Questions by difficulty
            questions_by_difficulty = self.db.execute(
                select(
                    Question.difficulty_level,
                    func.count(Question.id).label('count')
                ).group_by(Question.difficulty_level)
            ).all()
            
            # Total uses
            total_uses = self.db.execute(
                select(func.count(SessionQuestion.id))
            ).scalar() or 0
            
            # Average success rate
            avg_success_rate = self.db.execute(
                select(func.avg(Question.success_rate))
            ).scalar()
            
            # Top performing questions
            top_performing = self.db.execute(
                select(Question).where(
                    Question.success_rate.isnot(None)
                ).order_by(
                    Question.success_rate.desc(),
                    Question.usage_count.desc()
                ).limit(10)
            ).scalars().all()
            
            return {
                "total_questions": total_questions,
                "questions_by_category": {cat: count for cat, count in questions_by_category},
                "questions_by_difficulty": {diff: count for diff, count in questions_by_difficulty},
                "total_uses": total_uses,
                "average_success_rate": float(avg_success_rate) if avg_success_rate else None,
                "top_performing_questions": [
                    {
                        "id": str(q.id),
                        "question_text": q.question_text[:100],
                        "category": q.category,
                        "success_rate": q.success_rate,
                        "usage_count": q.usage_count
                    }
                    for q in top_performing
                ],
                "recent_activity": []  # Could be enhanced
            }
            
        except Exception as e:
            logger.error(f"Error getting system overview: {e}")
            return {
                "total_questions": 0,
                "questions_by_category": {},
                "questions_by_difficulty": {},
                "total_uses": 0,
                "average_success_rate": None,
                "top_performing_questions": [],
                "recent_activity": []
            }

