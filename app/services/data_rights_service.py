"""
Data rights service for GDPR/CCPA compliance.

Provides user data export (Right to Access) and account deletion (Right to Erasure).
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.database.models import (
    User,
    InterviewSession,
    SessionQuestion,
    Question,
    Answer,
    UserPerformance,
    AnalyticsEvent,
    UserGoal,
    UserConsent,
    ConsentHistory,
    EncryptionKey,
)
from app.utils.uuid_utils import to_uuid
from app.utils.logger import get_logger
from app.services.encryption_service import get_encryption_service

logger = get_logger(__name__)


class DataRightsService:
    """Service for GDPR/CCPA data rights operations."""

    def __init__(self, db: Session):
        self.db = db

    def export_user_data(self, user_id) -> Dict[str, Any]:
        """
        Export all user data for GDPR Right to Access.
        Excludes password_hash and other sensitive internal fields.
        """
        uid = to_uuid(user_id)
        user = self.db.query(User).filter(User.id == uid).first()
        if not user:
            return {"error": "User not found"}

        # User profile (exclude password_hash)
        user_data = {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }

        # Sessions
        sessions = (
            self.db.query(InterviewSession)
            .filter(InterviewSession.user_id == uid)
            .order_by(InterviewSession.created_at.desc())
            .all()
        )
        enc = get_encryption_service()
        uid_str = str(uid)
        sessions_data = []
        for s in sessions:
            job_desc = s.job_description
            if job_desc and enc.is_enabled() and isinstance(job_desc, str):
                dec = enc.decrypt(job_desc, uid_str)
                job_desc = dec if isinstance(dec, str) else str(dec) if dec is not None else job_desc
            sessions_data.append({
                "id": str(s.id),
                "mode": s.mode,
                "role": s.role,
                "job_description": job_desc,
                "status": s.status,
                "total_questions": s.total_questions,
                "completed_questions": s.completed_questions,
                "overall_score": s.overall_score,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            })

        session_ids = [s.id for s in sessions]
        answers_data = []
        answers = (
            self.db.query(Answer)
            .filter(Answer.session_id.in_(session_ids))
            .all()
        )
        for a in answers:
            ans_text = a.answer_text
            ans_score = a.score
            if enc.is_enabled():
                if ans_text and isinstance(ans_text, str):
                    dec = enc.decrypt(ans_text, uid_str)
                    ans_text = dec if isinstance(dec, str) else str(dec) if dec is not None else ans_text
                if ans_score and isinstance(ans_score, str):
                    dec = enc.decrypt(ans_score, uid_str)
                    ans_score = dec if isinstance(dec, dict) else ans_score
            answers_data.append({
                "id": str(a.id),
                "question_id": str(a.question_id),
                "answer_text": ans_text,
                "score": ans_score,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            })

        # Performance
        perf = (
            self.db.query(UserPerformance)
            .filter(UserPerformance.user_id == uid)
            .all()
        )
        performance_data = [
            {
                "id": str(p.id),
                "session_id": str(p.session_id),
                "skill_category": p.skill_category,
                "score": p.score,
                "improvement_rate": p.improvement_rate,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in perf
        ]

        # Analytics events
        events = (
            self.db.query(AnalyticsEvent)
            .filter(AnalyticsEvent.user_id == uid)
            .order_by(AnalyticsEvent.created_at.desc())
            .all()
        )
        analytics_data = [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "event_data": e.event_data,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ]

        # Goals
        goals = self.db.query(UserGoal).filter(UserGoal.user_id == uid).all()
        goals_data = [
            {
                "id": str(g.id),
                "title": g.title,
                "description": g.description,
                "goal_type": g.goal_type,
                "target_value": g.target_value,
                "current_value": g.current_value,
                "status": g.status,
                "created_at": g.created_at.isoformat() if g.created_at else None,
            }
            for g in goals
        ]

        # Consents
        consents = self.db.query(UserConsent).filter(UserConsent.user_id == uid).all()
        consents_data = [
            {
                "consent_type": c.consent_type,
                "granted": c.granted,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in consents
        ]

        return {
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "user": user_data,
            "sessions": sessions_data,
            "answers": answers_data,
            "performance": performance_data,
            "analytics_events": analytics_data,
            "goals": goals_data,
            "consents": consents_data,
        }

    def delete_user_account(self, user_id) -> bool:
        """
        Delete user account and all related data (GDPR Right to Erasure).
        Cascades: sessions, session_questions, user_performance, analytics_events, goals, consents.
        Note: Answers are linked to Questions (shared); we delete answers for questions
        that appear only in this user's sessions to avoid affecting other users.
        """
        uid = to_uuid(user_id)
        user = self.db.query(User).filter(User.id == uid).first()
        if not user:
            return False

        # Crypto-shredding: delete encryption keys before user (INT-31)
        self.db.query(EncryptionKey).filter(EncryptionKey.user_id == uid).delete()

        # Delete answers for this user's sessions (Answer.session_id cascade may be null for legacy)
        session_ids = [s.id for s in self.db.query(InterviewSession).filter(InterviewSession.user_id == uid).all()]
        if session_ids:
            self.db.query(Answer).filter(Answer.session_id.in_(session_ids)).delete(synchronize_session=False)

        # Delete consent history first (no FK from User)
        self.db.query(ConsentHistory).filter(ConsentHistory.user_id == uid).delete()

        # Delete user - cascade will handle: interview_sessions, user_performance,
        # analytics_events, goals, consents (UserConsent), answers with session_id
        self.db.delete(user)
        self.db.commit()

        logger.info(f"User account deleted: {uid}")
        return True
