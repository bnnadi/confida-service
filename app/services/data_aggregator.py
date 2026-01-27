"""
Data Aggregator Service for Confida.

This service provides efficient data aggregation capabilities for dashboard
and analytics endpoints, with caching support for performance optimization.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from app.database.models import (
    InterviewSession, Question, Answer, User, AnalyticsEvent, UserPerformance, SessionQuestion
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DataAggregator:
    """Service for aggregating dashboard and analytics data."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _to_uuid(self, user_id):
        """Convert user_id to UUID if it's a string."""
        import uuid as uuid_lib
        if isinstance(user_id, str):
            return uuid_lib.UUID(user_id)
        return user_id
    
    def get_user_sessions_summary(
        self, 
        user_id: str, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get summary of user sessions."""
        user_id = self._to_uuid(user_id)
        query = self.db.query(InterviewSession).filter(InterviewSession.user_id == user_id)
        
        if start_date:
            query = query.filter(InterviewSession.created_at >= start_date)
        if end_date:
            query = query.filter(InterviewSession.created_at <= end_date)
        
        sessions = query.all()
        
        if not sessions:
            return {
                "total_sessions": 0,
                "completed_sessions": 0,
                "active_sessions": 0,
                "average_score": 0.0,
                "completion_rate": 0.0
            }
        
        completed = len([s for s in sessions if s.status == "completed"])
        active = len([s for s in sessions if s.status == "active"])
        
        # Calculate average score from overall_score field
        scores = []
        for session in sessions:
            if session.overall_score and isinstance(session.overall_score, dict):
                if "overall" in session.overall_score:
                    scores.append(float(session.overall_score["overall"]))
                elif "average" in session.overall_score:
                    scores.append(float(session.overall_score["average"]))
            elif session.overall_score and isinstance(session.overall_score, (int, float)):
                scores.append(float(session.overall_score))
        
        avg_score = sum(scores) / len(scores) if scores else 0.0
        completion_rate = (completed / len(sessions) * 100) if sessions else 0.0
        
        return {
            "total_sessions": len(sessions),
            "completed_sessions": completed,
            "active_sessions": active,
            "average_score": avg_score,
            "completion_rate": completion_rate
        }
    
    def get_user_progress_data(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get user progress data over time."""
        user_id = self._to_uuid(user_id)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        sessions = self.db.query(InterviewSession).filter(
            and_(
                InterviewSession.user_id == user_id,
                InterviewSession.created_at >= start_date,
                InterviewSession.created_at <= end_date
            )
        ).order_by(InterviewSession.created_at).all()
        
        if not sessions:
            return {
                "skill_progression": {},
                "difficulty_progression": [],
                "time_progression": [],
                "overall_trend": "stable"
            }
        
        # Get skill progression
        skill_scores = defaultdict(list)
        difficulty_scores = []
        time_points = []
        
        for session in sessions:
            # Extract scores by category/skill
            if session.overall_score and isinstance(session.overall_score, dict):
                for skill, score in session.overall_score.items():
                    if isinstance(score, (int, float)):
                        skill_scores[skill].append(float(score))
            
            # Get difficulty from questions
            session_questions = self.db.query(SessionQuestion).filter(
                SessionQuestion.session_id == session.id
            ).all()
            
            if session_questions:
                avg_difficulty = 0.0
                for sq in session_questions:
                    question = self.db.query(Question).filter(Question.id == sq.question_id).first()
                    if question:
                        difficulty_map = {"easy": 1.0, "medium": 2.0, "hard": 3.0}
                        avg_difficulty += difficulty_map.get(question.difficulty_level, 2.0)
                avg_difficulty = avg_difficulty / len(session_questions) if session_questions else 0.0
                difficulty_scores.append(avg_difficulty)
            
            time_points.append(session.created_at)
        
        # Calculate overall trend
        if len(sessions) >= 2:
            first_half = sessions[:len(sessions)//2]
            second_half = sessions[len(sessions)//2:]
            
            first_scores = []
            second_scores = []
            
            for s in first_half:
                if s.overall_score and isinstance(s.overall_score, dict):
                    if "overall" in s.overall_score:
                        first_scores.append(float(s.overall_score["overall"]))
            
            for s in second_half:
                if s.overall_score and isinstance(s.overall_score, dict):
                    if "overall" in s.overall_score:
                        second_scores.append(float(s.overall_score["overall"]))
            
            if first_scores and second_scores:
                first_avg = sum(first_scores) / len(first_scores)
                second_avg = sum(second_scores) / len(second_scores)
                
                if second_avg > first_avg * 1.05:
                    trend = "improving"
                elif second_avg < first_avg * 0.95:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        return {
            "skill_progression": {skill: scores for skill, scores in skill_scores.items()},
            "difficulty_progression": difficulty_scores,
            "time_progression": time_points,
            "overall_trend": trend
        }
    
    def get_recent_activity(
        self,
        user_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent user activity."""
        user_id = self._to_uuid(user_id)
        activities = []
        
        # Get recent sessions
        recent_sessions = self.db.query(InterviewSession).filter(
            InterviewSession.user_id == user_id
        ).order_by(desc(InterviewSession.created_at)).limit(limit).all()
        
        for session in recent_sessions:
            activities.append({
                "activity_type": "session_" + session.status,
                "activity_date": session.created_at,
                "activity_data": {
                    "session_id": str(session.id),
                    "role": session.role,
                    "status": session.status,
                    "total_questions": session.total_questions,
                    "completed_questions": session.completed_questions
                }
            })
        
        # Get recent analytics events
        recent_events = self.db.query(AnalyticsEvent).filter(
            AnalyticsEvent.user_id == user_id
        ).order_by(desc(AnalyticsEvent.created_at)).limit(limit).all()
        
        for event in recent_events:
            activities.append({
                "activity_type": event.event_type,
                "activity_date": event.created_at,
                "activity_data": event.event_data or {}
            })
        
        # Sort by date and return top N
        activities.sort(key=lambda x: x["activity_date"], reverse=True)
        return activities[:limit]
    
    def get_current_streak(self, user_id: str) -> int:
        """Calculate current consecutive days with activity."""
        user_id = self._to_uuid(user_id)
        end_date = datetime.utcnow().date()
        current_date = end_date
        streak = 0
        
        while True:
            start_datetime = datetime.combine(current_date, datetime.min.time())
            end_datetime = datetime.combine(current_date, datetime.max.time())
            
            # Check for sessions on this date
            has_activity = self.db.query(InterviewSession).filter(
                and_(
                    InterviewSession.user_id == user_id,
                    InterviewSession.created_at >= start_datetime,
                    InterviewSession.created_at <= end_datetime
                )
            ).first() is not None
            
            if not has_activity:
                break
            
            streak += 1
            current_date = current_date - timedelta(days=1)
            
            # Limit streak calculation to last 365 days
            if streak >= 365:
                break
        
        return streak
    
    def get_skill_breakdown(self, user_id: str, days: int = 30) -> Dict[str, float]:
        """Get skill breakdown by category."""
        user_id = self._to_uuid(user_id)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        sessions = self.db.query(InterviewSession).filter(
            and_(
                InterviewSession.user_id == user_id,
                InterviewSession.created_at >= start_date,
                InterviewSession.created_at <= end_date,
                InterviewSession.status == "completed"
            )
        ).all()
        
        skill_totals = defaultdict(list)
        
        for session in sessions:
            if session.overall_score and isinstance(session.overall_score, dict):
                for skill, score in session.overall_score.items():
                    if isinstance(score, (int, float)):
                        skill_totals[skill].append(float(score))
        
        return {
            skill: sum(scores) / len(scores) if scores else 0.0
            for skill, scores in skill_totals.items()
        }
    
    def get_performance_metrics_detailed(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get detailed performance metrics."""
        user_id = self._to_uuid(user_id)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        sessions = self.db.query(InterviewSession).filter(
            and_(
                InterviewSession.user_id == user_id,
                InterviewSession.created_at >= start_date,
                InterviewSession.created_at <= end_date
            )
        ).all()
        
        if not sessions:
            return {
                "total_sessions": 0,
                "completed_sessions": 0,
                "average_score": 0.0,
                "best_score": 0.0,
                "worst_score": 0.0,
                "completion_rate": 0.0,
                "average_session_duration": 0.0,
                "total_questions_answered": 0
            }
        
        completed = len([s for s in sessions if s.status == "completed"])
        scores = []
        
        for session in sessions:
            if session.overall_score and isinstance(session.overall_score, dict):
                if "overall" in session.overall_score:
                    scores.append(float(session.overall_score["overall"]))
                elif "average" in session.overall_score:
                    scores.append(float(session.overall_score["average"]))
            elif session.overall_score and isinstance(session.overall_score, (int, float)):
                scores.append(float(session.overall_score))
        
        # Calculate session durations
        durations = []
        for session in sessions:
            if session.updated_at and session.created_at:
                duration = (session.updated_at - session.created_at).total_seconds() / 60  # minutes
                durations.append(duration)
        
        total_questions = sum(s.completed_questions for s in sessions)
        
        return {
            "total_sessions": len(sessions),
            "completed_sessions": completed,
            "average_score": sum(scores) / len(scores) if scores else 0.0,
            "best_score": max(scores) if scores else 0.0,
            "worst_score": min(scores) if scores else 0.0,
            "completion_rate": (completed / len(sessions) * 100) if sessions else 0.0,
            "average_session_duration": sum(durations) / len(durations) if durations else 0.0,
            "total_questions_answered": total_questions
        }
    
    def get_trend_data(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get trend data for performance metrics."""
        user_id = self._to_uuid(user_id)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        sessions = self.db.query(InterviewSession).filter(
            and_(
                InterviewSession.user_id == user_id,
                InterviewSession.created_at >= start_date,
                InterviewSession.created_at <= end_date
            )
        ).order_by(InterviewSession.created_at).all()
        
        if not sessions:
            return {
                "score_trend": [],
                "completion_trend": [],
                "skill_trends": {},
                "trend_direction": "stable",
                "trend_percentage": 0.0
            }
        
        score_trend = []
        completion_trend = []
        skill_trends = defaultdict(list)
        
        for session in sessions:
            date = session.created_at.date()
            
            # Score trend
            score = None
            if session.overall_score and isinstance(session.overall_score, dict):
                if "overall" in session.overall_score:
                    score = float(session.overall_score["overall"])
                elif "average" in session.overall_score:
                    score = float(session.overall_score["average"])
            elif session.overall_score and isinstance(session.overall_score, (int, float)):
                score = float(session.overall_score)
            
            if score is not None:
                score_trend.append({
                    "date": date.isoformat(),
                    "value": score
                })
                
                # Skill trends
                if session.overall_score and isinstance(session.overall_score, dict):
                    for skill, skill_score in session.overall_score.items():
                        if isinstance(skill_score, (int, float)) and skill != "overall" and skill != "average":
                            skill_trends[skill].append({
                                "date": date.isoformat(),
                                "value": float(skill_score)
                            })
            
            # Completion trend
            completion_trend.append({
                "date": date.isoformat(),
                "value": 1 if session.status == "completed" else 0
            })
        
        # Calculate trend direction
        if len(score_trend) >= 2:
            first_half = score_trend[:len(score_trend)//2]
            second_half = score_trend[len(score_trend)//2:]
            
            first_avg = sum(p["value"] for p in first_half) / len(first_half)
            second_avg = sum(p["value"] for p in second_half) / len(second_half)
            
            if second_avg > first_avg * 1.05:
                direction = "improving"
                percentage = ((second_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0.0
            elif second_avg < first_avg * 0.95:
                direction = "declining"
                percentage = ((first_avg - second_avg) / first_avg * 100) if first_avg > 0 else 0.0
            else:
                direction = "stable"
                percentage = 0.0
        else:
            direction = "stable"
            percentage = 0.0
        
        return {
            "score_trend": score_trend,
            "completion_trend": completion_trend,
            "skill_trends": dict(skill_trends),
            "trend_direction": direction,
            "trend_percentage": percentage
        }
    
    def get_user_insights(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get personalized user insights."""
        user_id = self._to_uuid(user_id)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        sessions = self.db.query(InterviewSession).filter(
            and_(
                InterviewSession.user_id == user_id,
                InterviewSession.created_at >= start_date,
                InterviewSession.created_at <= end_date
            )
        ).all()
        
        if not sessions:
            return {
                "strengths": [],
                "weaknesses": [],
                "recommendations": ["Start practicing to get personalized insights"],
                "milestones": [],
                "next_goals": []
            }
        
        # Analyze strengths and weaknesses
        skill_scores = defaultdict(list)
        
        for session in sessions:
            if session.overall_score and isinstance(session.overall_score, dict):
                for skill, score in session.overall_score.items():
                    if isinstance(score, (int, float)) and skill not in ["overall", "average"]:
                        skill_scores[skill].append(float(score))
        
        skill_averages = {
            skill: sum(scores) / len(scores)
            for skill, scores in skill_scores.items()
        }
        
        if skill_averages:
            sorted_skills = sorted(skill_averages.items(), key=lambda x: x[1], reverse=True)
            strengths = [skill for skill, score in sorted_skills[:3] if score >= 7.0]
            weaknesses = [skill for skill, score in sorted_skills[-3:] if score < 6.0]
        else:
            strengths = []
            weaknesses = []
        
        # Generate recommendations
        recommendations = []
        if weaknesses:
            recommendations.append(f"Focus on improving: {', '.join(weaknesses)}")
        
        completed_sessions = len([s for s in sessions if s.status == "completed"])
        if completed_sessions < 5:
            recommendations.append("Complete more practice sessions to build confidence")
        
        avg_score = sum(skill_averages.values()) / len(skill_averages) if skill_averages else 0.0
        if avg_score < 6.0:
            recommendations.append("Review your answers and practice more frequently")
        
        # Milestones
        milestones = []
        if completed_sessions >= 10:
            milestones.append({
                "title": "10 Sessions Completed",
                "description": "Great progress! Keep practicing",
                "achieved_at": datetime.utcnow().isoformat()
            })
        
        if avg_score >= 8.0:
            milestones.append({
                "title": "High Performer",
                "description": "You're scoring above average!",
                "achieved_at": datetime.utcnow().isoformat()
            })
        
        # Next goals
        next_goals = []
        if completed_sessions < 10:
            next_goals.append({
                "title": "Complete 10 Sessions",
                "description": f"You're {10 - completed_sessions} sessions away",
                "target": 10
            })
        
        if avg_score < 7.0:
            next_goals.append({
                "title": "Reach 7.0 Average Score",
                "description": f"Current average: {avg_score:.1f}",
                "target": 7.0
            })
        
        return {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "recommendations": recommendations,
            "milestones": milestones,
            "next_goals": next_goals
        }

