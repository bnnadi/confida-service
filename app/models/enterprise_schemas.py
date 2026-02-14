"""
Pydantic schemas for Enterprise API (INT-49).
"""
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class EnterpriseStatsResponse(BaseModel):
    """Dashboard stats response."""

    totalUsers: int = Field(..., description="Total users in organization")
    activeSessions: int = Field(..., description="Currently active sessions")
    totalSessions: int = Field(..., description="Total sessions")
    averageScore: float = Field(..., description="Average score across sessions")
    improvementRate: float = Field(..., description="Improvement rate percentage")
    organization: str = Field(..., description="Organization name")


class ActivityItem(BaseModel):
    """Single activity item."""

    id: str = Field(..., description="Session or activity ID")
    user: str = Field(..., description="User display name")
    role: str = Field(..., description="Job role")
    score: float = Field(..., description="Score")
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    status: str = Field(..., description="completed, in-progress, etc.")


class ActivityResponse(BaseModel):
    """Recent activity response."""

    items: List[ActivityItem] = Field(default_factory=list)
    total: int = Field(..., description="Total count")


class PerformerItem(BaseModel):
    """Top performer item."""

    name: str = Field(..., description="User name")
    role: str = Field(..., description="Job role")
    avgScore: float = Field(..., description="Average score")
    sessions: int = Field(..., description="Number of sessions")


class PerformersResponse(BaseModel):
    """Top performers response."""

    items: List[PerformerItem] = Field(default_factory=list)


class SessionListItem(BaseModel):
    """Session list item."""

    id: str = Field(..., description="Session ID")
    user: str = Field(..., description="User name")
    email: str = Field(..., description="User email")
    role: str = Field(..., description="Job role")
    department: Optional[str] = Field(None, description="Department name")
    score: float = Field(..., description="Score")
    duration: Optional[int] = Field(None, description="Duration in minutes")
    date: str = Field(..., description="Date (YYYY-MM-DD)")
    status: str = Field(..., description="Session status")
    questions: int = Field(..., description="Number of questions")
    feedback: Optional[str] = Field(None, description="Session feedback")


class SessionsListResponse(BaseModel):
    """Sessions list response."""

    items: List[SessionListItem] = Field(default_factory=list)
    total: int = Field(..., description="Total count")


class SessionDetailResponse(SessionListItem):
    """Session detail (extends list item with optional IDs)."""

    company_id: Optional[str] = Field(None, description="Company ID for future use")
    department_id: Optional[str] = Field(None, description="Department ID")


class TopSkillItem(BaseModel):
    """Top skill item for analytics."""

    skill: str = Field(..., description="Skill name")
    score: float = Field(..., description="Score")
    trend: Literal["up", "down", "stable"] = Field(..., description="Trend direction")


class DepartmentStatItem(BaseModel):
    """Department stat for analytics."""

    department: str = Field(..., description="Department name")
    sessions: int = Field(..., description="Session count")
    avgScore: float = Field(..., description="Average score")
    improvement: float = Field(..., description="Improvement percentage")


class MonthlyTrendItem(BaseModel):
    """Monthly trend item."""

    month: str = Field(..., description="Month label (e.g. Jan)")
    sessions: int = Field(..., description="Session count")
    avgScore: float = Field(..., description="Average score")


class AnalyticsResponse(BaseModel):
    """Analytics response."""

    totalSessions: int = Field(..., description="Total sessions in range")
    averageScore: float = Field(..., description="Average score")
    improvementRate: float = Field(..., description="Improvement rate percentage")
    completionRate: float = Field(..., description="Completion rate percentage")
    topSkills: List[TopSkillItem] = Field(default_factory=list)
    departmentStats: List[DepartmentStatItem] = Field(default_factory=list)
    monthlyTrend: List[MonthlyTrendItem] = Field(default_factory=list)


class OrganizationInfo(BaseModel):
    """Organization info in settings."""

    name: str = Field(..., description="Organization name")
    domain: str = Field(..., description="Domain")
    timezone: str = Field(..., description="Timezone")
    language: str = Field(..., description="Language code")


class FeaturesConfig(BaseModel):
    """Features configuration."""

    sso: bool = Field(default=False)
    analytics: bool = Field(default=True)
    customBranding: bool = Field(default=False)
    advancedReporting: bool = Field(default=True)
    userManagement: bool = Field(default=True)


class NotificationsConfig(BaseModel):
    """Notifications configuration."""

    email: bool = Field(default=True)
    weekly: bool = Field(default=True)
    monthly: bool = Field(default=True)
    alerts: bool = Field(default=True)


class SecurityConfig(BaseModel):
    """Security configuration."""

    passwordPolicy: str = Field(default="strong")
    sessionTimeout: int = Field(default=30, description="Minutes")
    twoFactor: bool = Field(default=False)
    ipRestrictions: bool = Field(default=False)


class OrganizationSettingsResponse(BaseModel):
    """Organization settings response."""

    organization: OrganizationInfo = Field(...)
    features: FeaturesConfig = Field(default_factory=FeaturesConfig)
    notifications: NotificationsConfig = Field(default_factory=NotificationsConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)


class OrganizationSettingsPatch(BaseModel):
    """Partial settings for PATCH."""

    organization: Optional[Dict[str, Any]] = None
    features: Optional[Dict[str, Any]] = None
    notifications: Optional[Dict[str, Any]] = None
    security: Optional[Dict[str, Any]] = None


class DepartmentItem(BaseModel):
    """Department item."""

    id: str = Field(..., description="Department ID")
    name: str = Field(..., description="Department name")
    company_id: Optional[str] = Field(None, description="Company ID for future use")


class DepartmentsResponse(BaseModel):
    """Departments list response."""

    items: List[DepartmentItem] = Field(default_factory=list)
