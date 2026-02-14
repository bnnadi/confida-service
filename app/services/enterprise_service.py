"""
Enterprise Service for organization-scoped analytics and management (INT-49).
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, desc

from app.database.models import (
    User,
    InterviewSession,
    Organization,
    OrganizationSettings,
    Department,
)
from app.models.enterprise_schemas import (
    EnterpriseStatsResponse,
    ActivityItem,
    ActivityResponse,
    PerformerItem,
    PerformersResponse,
    SessionListItem,
    SessionsListResponse,
    SessionDetailResponse,
    AnalyticsResponse,
    TopSkillItem,
    DepartmentStatItem,
    MonthlyTrendItem,
    OrganizationSettingsResponse,
    OrganizationInfo,
    FeaturesConfig,
    NotificationsConfig,
    SecurityConfig,
    DepartmentItem,
    DepartmentsResponse,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Default settings when none stored
DEFAULT_FEATURES = {
    "sso": False,
    "analytics": True,
    "customBranding": False,
    "advancedReporting": True,
    "userManagement": True,
}
DEFAULT_NOTIFICATIONS = {
    "email": True,
    "weekly": True,
    "monthly": True,
    "alerts": True,
}
DEFAULT_SECURITY = {
    "passwordPolicy": "strong",
    "sessionTimeout": 30,
    "twoFactor": False,
    "ipRestrictions": False,
}


def _extract_score(score) -> Optional[float]:
    """Extract numeric score from JSONB overall_score."""
    if score is None:
        return None
    if isinstance(score, (int, float)):
        return float(score)
    if isinstance(score, dict):
        for key in ("overall", "average", "score", "total"):
            if key in score and isinstance(score[key], (int, float)):
                return float(score[key])
    return None


def _session_duration(session: InterviewSession) -> Optional[int]:
    """Get session duration in minutes."""
    if session.duration_minutes is not None:
        return session.duration_minutes
    if session.created_at and session.updated_at:
        delta = session.updated_at - session.created_at
        return int(delta.total_seconds() / 60)
    return None


class EnterpriseService:
    """Service for enterprise organization-scoped data."""

    def __init__(self, db: Session):
        self.db = db

    def get_stats(self, org_id: str) -> EnterpriseStatsResponse:
        """Get dashboard stats for organization."""
        org = self.db.query(Organization).filter(Organization.id == org_id).first()
        org_name = org.name if org else "Unknown"

        total_users = self.db.query(User).filter(
            User.organization_id == org_id,
            User.is_active == True,
        ).count()

        sessions = (
            self.db.query(InterviewSession)
            .filter(InterviewSession.organization_id == org_id)
            .all()
        )
        total_sessions = len(sessions)
        active_sessions = len([s for s in sessions if s.status == "active"])
        scores = [_extract_score(s.overall_score) for s in sessions if _extract_score(s.overall_score) is not None]
        average_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        improvement_rate = 0.0
        if len(sessions) >= 2:
            sorted_sessions = sorted(sessions, key=lambda x: x.created_at or datetime.min.replace(tzinfo=timezone.utc))
            mid = len(sorted_sessions) // 2
            first_scores = [_extract_score(s.overall_score) for s in sorted_sessions[:mid]]
            last_scores = [_extract_score(s.overall_score) for s in sorted_sessions[mid:]]
            first_scores = [s for s in first_scores if s is not None]
            last_scores = [s for s in last_scores if s is not None]
            if first_scores and last_scores:
                first_avg = sum(first_scores) / len(first_scores)
                last_avg = sum(last_scores) / len(last_scores)
                improvement_rate = round(
                    ((last_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0.0,
                    0,
                )

        return EnterpriseStatsResponse(
            totalUsers=total_users,
            activeSessions=active_sessions,
            totalSessions=total_sessions,
            averageScore=average_score,
            improvementRate=improvement_rate,
            organization=org_name,
        )

    def get_activity(
        self,
        org_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> ActivityResponse:
        """Get recent activity for organization."""
        query = (
            self.db.query(InterviewSession, User)
            .join(User, InterviewSession.user_id == User.id)
            .filter(InterviewSession.organization_id == org_id)
            .order_by(desc(InterviewSession.created_at))
        )
        total = query.count()
        rows = query.offset(offset).limit(limit).all()

        items = []
        for session, user in rows:
            score = _extract_score(session.overall_score) or 0.0
            date_str = (session.created_at.date().isoformat() if session.created_at else "")
            status = "completed" if session.status == "completed" else "in-progress"
            items.append(
                ActivityItem(
                    id=str(session.id),
                    user=user.name or user.email,
                    role=session.role,
                    score=score,
                    date=date_str,
                    status=status,
                )
            )

        return ActivityResponse(items=items, total=total)

    def get_performers(self, org_id: str, limit: int = 10) -> PerformersResponse:
        """Get top performers by average score."""
        sessions = (
            self.db.query(InterviewSession)
            .filter(
                InterviewSession.organization_id == org_id,
                InterviewSession.status == "completed",
            )
            .all()
        )
        user_scores: Dict[str, List[float]] = defaultdict(list)
        user_roles: Dict[str, str] = {}
        for s in sessions:
            score = _extract_score(s.overall_score)
            if score is not None:
                user_scores[str(s.user_id)].append(score)
                user_roles[str(s.user_id)] = s.role

        performers = []
        for user_id, scores in user_scores.items():
            user = self.db.query(User).filter(User.id == user_id).first()
            if user:
                avg = sum(scores) / len(scores)
                performers.append(
                    PerformerItem(
                        name=user.name or user.email,
                        role=user_roles.get(user_id, ""),
                        avgScore=round(avg, 1),
                        sessions=len(scores),
                    )
                )

        performers.sort(key=lambda x: x.avgScore, reverse=True)
        return PerformersResponse(items=performers[:limit])

    def get_sessions(
        self,
        org_id: str,
        status: Optional[str] = None,
        score_min: Optional[float] = None,
        score_max: Optional[float] = None,
        department: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> SessionsListResponse:
        """Get sessions list with filters."""
        query = (
            self.db.query(InterviewSession, User, Department)
            .join(User, InterviewSession.user_id == User.id)
            .outerjoin(Department, InterviewSession.department_id == Department.id)
            .filter(InterviewSession.organization_id == org_id)
        )
        if status and status != "all":
            if status == "completed":
                query = query.filter(InterviewSession.status == "completed")
            elif status == "in-progress":
                query = query.filter(InterviewSession.status == "active")
        if department:
            query = query.filter(Department.name == department)

        rows = query.order_by(desc(InterviewSession.created_at)).all()

        items = []
        for session, user, dept in rows:
            score = _extract_score(session.overall_score) or 0.0
            if score_min is not None and score < score_min:
                continue
            if score_max is not None and score > score_max:
                continue
            items.append((session, user, dept))

        total = len(items)
        items = items[offset : offset + limit]

        result_items = []
        for session, user, dept in items:
            score = _extract_score(session.overall_score) or 0.0
            date_str = (session.created_at.date().isoformat() if session.created_at else "")
            result_items.append(
                SessionListItem(
                    id=str(session.id),
                    user=user.name or user.email,
                    email=user.email,
                    role=session.role,
                    department=dept.name if dept else None,
                    score=score,
                    duration=_session_duration(session),
                    date=date_str,
                    status=session.status,
                    questions=session.total_questions or 0,
                    feedback=session.feedback,
                )
            )

        return SessionsListResponse(items=result_items, total=total)

    def get_session_detail(self, org_id: str, session_id: str) -> Optional[SessionDetailResponse]:
        """Get single session detail."""
        row = (
            self.db.query(InterviewSession, User, Department)
            .join(User, InterviewSession.user_id == User.id)
            .outerjoin(Department, InterviewSession.department_id == Department.id)
            .filter(
                InterviewSession.id == session_id,
                InterviewSession.organization_id == org_id,
            )
            .first()
        )
        if not row:
            return None
        session, user, dept = row
        score = _extract_score(session.overall_score) or 0.0
        date_str = (session.created_at.date().isoformat() if session.created_at else "")
        return SessionDetailResponse(
            id=str(session.id),
            user=user.name or user.email,
            email=user.email,
            role=session.role,
            department=dept.name if dept else None,
            score=score,
            duration=_session_duration(session),
            date=date_str,
            status=session.status,
            questions=session.total_questions or 0,
            feedback=session.feedback,
            company_id=None,
            department_id=str(session.department_id) if session.department_id else None,
        )

    def get_analytics(
        self,
        org_id: str,
        time_range: str,
    ) -> AnalyticsResponse:
        """Get analytics for time range (7d, 30d, 90d, 1y)."""
        days_map = {"7d": 7, "30d": 30, "90d": 90, "1y": 365}
        days = days_map.get(time_range, 30)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        sessions = (
            self.db.query(InterviewSession)
            .filter(
                InterviewSession.organization_id == org_id,
                InterviewSession.created_at >= start_date,
                InterviewSession.created_at <= end_date,
            )
            .all()
        )

        total_sessions = len(sessions)
        completed = len([s for s in sessions if s.status == "completed"])
        completion_rate = round((completed / total_sessions * 100), 0) if total_sessions else 0.0

        scores = [_extract_score(s.overall_score) for s in sessions if _extract_score(s.overall_score) is not None]
        average_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        improvement_rate = 0.0
        if len(sessions) >= 2:
            sorted_sessions = sorted(sessions, key=lambda x: x.created_at or datetime.min.replace(tzinfo=timezone.utc))
            mid = len(sorted_sessions) // 2
            first_scores = [_extract_score(s.overall_score) for s in sorted_sessions[:mid] if _extract_score(s.overall_score) is not None]
            last_scores = [_extract_score(s.overall_score) for s in sorted_sessions[mid:] if _extract_score(s.overall_score) is not None]
            if first_scores and last_scores:
                first_avg = sum(first_scores) / len(first_scores)
                last_avg = sum(last_scores) / len(last_scores)
                improvement_rate = round(((last_avg - first_avg) / first_avg * 100) if first_avg > 0 else 0.0, 0)

        skill_scores: Dict[str, List[float]] = defaultdict(list)
        for s in sessions:
            if s.overall_score and isinstance(s.overall_score, dict):
                for skill, val in s.overall_score.items():
                    if skill not in ("overall", "average", "score", "total") and isinstance(val, (int, float)):
                        skill_scores[skill].append(float(val))

        top_skills = [
            TopSkillItem(
                skill=skill,
                score=round(sum(vals) / len(vals), 0),
                trend="up" if len(vals) >= 2 and vals[-1] > vals[0] else ("down" if len(vals) >= 2 and vals[-1] < vals[0] else "stable"),
            )
            for skill, vals in sorted(skill_scores.items(), key=lambda x: -sum(x[1]) / len(x[1]))[:5]
        ]

        dept_sessions: Dict[str, List[InterviewSession]] = defaultdict(list)
        for s in sessions:
            dept_id = str(s.department_id) if s.department_id else "Unknown"
            dept_sessions[dept_id].append(s)

        department_stats = []
        for dept_id, sess_list in dept_sessions.items():
            if dept_id != "Unknown":
                dept = self.db.query(Department).filter(Department.id == dept_id).first()
                dept_name = dept.name if dept else dept_id
            else:
                dept_name = "Unknown"
            dept_scores = [_extract_score(s.overall_score) for s in sess_list if _extract_score(s.overall_score) is not None]
            avg = sum(dept_scores) / len(dept_scores) if dept_scores else 0.0
            department_stats.append(
                DepartmentStatItem(
                    department=dept_name,
                    sessions=len(sess_list),
                    avgScore=round(avg, 1),
                    improvement=0.0,
                )
            )

        monthly: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"sessions": 0, "scores": []})
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        for s in sessions:
            if s.created_at:
                key = f"{s.created_at.year}-{s.created_at.month:02d}"
                monthly[key]["sessions"] += 1
                sc = _extract_score(s.overall_score)
                if sc is not None:
                    monthly[key]["scores"].append(sc)

        monthly_trend = []
        for i in range(days, 0, -30):
            d = end_date - timedelta(days=i)
            key = f"{d.year}-{d.month:02d}"
            if key in monthly:
                m = monthly[key]
                avg = sum(m["scores"]) / len(m["scores"]) if m["scores"] else 0.0
                monthly_trend.append(
                    MonthlyTrendItem(
                        month=month_names[d.month - 1],
                        sessions=m["sessions"],
                        avgScore=round(avg, 1),
                    )
                )

        return AnalyticsResponse(
            totalSessions=total_sessions,
            averageScore=average_score,
            improvementRate=improvement_rate,
            completionRate=completion_rate,
            topSkills=top_skills,
            departmentStats=department_stats,
            monthlyTrend=monthly_trend,
        )

    def get_settings(self, org_id: str) -> OrganizationSettingsResponse:
        """Get organization settings."""
        org = self.db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            raise ValueError("Organization not found")

        settings = (
            self.db.query(OrganizationSettings)
            .filter(OrganizationSettings.organization_id == org_id)
            .first()
        )

        if settings:
            features = {**DEFAULT_FEATURES, **(settings.features or {})}
            notifications = {**DEFAULT_NOTIFICATIONS, **(settings.notifications or {})}
            security = {**DEFAULT_SECURITY, **(settings.security or {})}
            return OrganizationSettingsResponse(
                organization=OrganizationInfo(
                    name=org.name,
                    domain=org.domain or "",
                    timezone=settings.timezone or "UTC",
                    language=settings.language or "en",
                ),
                features=FeaturesConfig(**features),
                notifications=NotificationsConfig(**notifications),
                security=SecurityConfig(**security),
            )
        return OrganizationSettingsResponse(
            organization=OrganizationInfo(
                name=org.name,
                domain=org.domain or "",
                timezone="UTC",
                language="en",
            ),
            features=FeaturesConfig(**DEFAULT_FEATURES),
            notifications=NotificationsConfig(**DEFAULT_NOTIFICATIONS),
            security=SecurityConfig(**DEFAULT_SECURITY),
        )

    def update_settings(self, org_id: str, patch: Dict[str, Any]) -> OrganizationSettingsResponse:
        """Update organization settings (partial PATCH)."""
        org = self.db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            raise ValueError("Organization not found")

        settings = (
            self.db.query(OrganizationSettings)
            .filter(OrganizationSettings.organization_id == org_id)
            .first()
        )
        if not settings:
            settings = OrganizationSettings(
                organization_id=org_id,
                timezone="UTC",
                language="en",
                features=DEFAULT_FEATURES.copy(),
                notifications=DEFAULT_NOTIFICATIONS.copy(),
                security=DEFAULT_SECURITY.copy(),
            )
            self.db.add(settings)
            self.db.commit()
            self.db.refresh(settings)

        if "organization" in patch and patch["organization"]:
            o = patch["organization"]
            if "name" in o:
                org.name = o["name"]
            if "domain" in o:
                org.domain = o["domain"]
            if "timezone" in o:
                settings.timezone = o["timezone"]
            if "language" in o:
                settings.language = o["language"]
        if "features" in patch and patch["features"]:
            settings.features = {**(settings.features or {}), **patch["features"]}
        if "notifications" in patch and patch["notifications"]:
            settings.notifications = {**(settings.notifications or {}), **patch["notifications"]}
        if "security" in patch and patch["security"]:
            settings.security = {**(settings.security or {}), **patch["security"]}

        self.db.commit()
        self.db.refresh(settings)
        self.db.refresh(org)
        return self.get_settings(org_id)

    def get_departments(self, org_id: str) -> DepartmentsResponse:
        """Get departments for organization."""
        depts = (
            self.db.query(Department)
            .filter(Department.organization_id == org_id)
            .all()
        )
        return DepartmentsResponse(
            items=[
                DepartmentItem(
                    id=str(d.id),
                    name=d.name,
                    company_id=str(d.company_id) if d.company_id else None,
                )
                for d in depts
            ]
        )
