"""
Enterprise API endpoints (INT-49).

All endpoints require Bearer token and organization context from JWT.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.services.database_service import get_db
from app.services.enterprise_service import EnterpriseService
from app.middleware.auth_middleware import get_enterprise_user, get_current_user_required
from app.models.enterprise_schemas import (
    EnterpriseStatsResponse,
    ActivityResponse,
    PerformersResponse,
    SessionsListResponse,
    SessionDetailResponse,
    AnalyticsResponse,
    OrganizationSettingsResponse,
    OrganizationSettingsPatch,
    DepartmentsResponse,
    UsersListResponse,
    InviteUserRequest,
    InviteUserResponse,
    CreateOrganizationRequest,
    CreateOrganizationResponse,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/enterprise", tags=["enterprise"])


def get_enterprise_service(db: Session = Depends(get_db)) -> EnterpriseService:
    """Dependency for EnterpriseService."""
    return EnterpriseService(db)


@router.get("/users", response_model=UsersListResponse)
async def get_users(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    role: str = Query(None, description="Filter by role"),
    department_id: str = Query(None, description="Filter by department ID"),
    current_user: dict = Depends(get_enterprise_user),
    service: EnterpriseService = Depends(get_enterprise_service),
):
    """List users in the organization. Filter by role and department."""
    try:
        return service.get_users(
            current_user["organization_id"],
            limit=limit,
            offset=offset,
            role=role,
            department_id=department_id,
        )
    except Exception as e:
        logger.error(f"Error getting enterprise users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get users",
        ) from e


@router.post("/users/invite", response_model=InviteUserResponse, status_code=status.HTTP_201_CREATED)
async def invite_user(
    request: InviteUserRequest,
    current_user: dict = Depends(get_enterprise_user),
    service: EnterpriseService = Depends(get_enterprise_service),
):
    """Invite a user to the organization. Returns invite link to share manually."""
    try:
        return service.create_invite(
            org_id=current_user["organization_id"],
            inviter_id=current_user["id"],
            email=request.email,
            role=request.role,
            department_id=request.department_id,
        )
    except ValueError as e:
        msg = str(e)
        if "already in organization" in msg or "already exists" in msg:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from e
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg) from e
    except Exception as e:
        logger.error(f"Error creating invite: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create invite",
        ) from e


@router.get("/stats", response_model=EnterpriseStatsResponse)
async def get_stats(
    current_user: dict = Depends(get_enterprise_user),
    service: EnterpriseService = Depends(get_enterprise_service),
):
    """Get dashboard stats for the organization."""
    try:
        return service.get_stats(current_user["organization_id"])
    except Exception as e:
        logger.error(f"Error getting enterprise stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get stats",
        ) from e


@router.get("/activity", response_model=ActivityResponse)
async def get_activity(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_enterprise_user),
    service: EnterpriseService = Depends(get_enterprise_service),
):
    """Get recent activity for the organization."""
    try:
        return service.get_activity(
            current_user["organization_id"],
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"Error getting enterprise activity: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get activity",
        ) from e


@router.get("/performers", response_model=PerformersResponse)
async def get_performers(
    limit: int = Query(10, ge=1, le=100),
    current_user: dict = Depends(get_enterprise_user),
    service: EnterpriseService = Depends(get_enterprise_service),
):
    """Get top performers for the organization."""
    try:
        return service.get_performers(
            current_user["organization_id"],
            limit=limit,
        )
    except Exception as e:
        logger.error(f"Error getting enterprise performers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get performers",
        ) from e


@router.get("/sessions", response_model=SessionsListResponse)
async def get_sessions(
    status_filter: str = Query("all", alias="status"),
    scoreMin: float = Query(None, alias="scoreMin"),
    scoreMax: float = Query(None, alias="scoreMax"),
    department: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_enterprise_user),
    service: EnterpriseService = Depends(get_enterprise_service),
):
    """Get sessions list with filters."""
    try:
        return service.get_sessions(
            current_user["organization_id"],
            status=status_filter if status_filter != "all" else None,
            score_min=scoreMin,
            score_max=scoreMax,
            department=department,
            limit=limit,
            offset=offset,
        )
    except Exception as e:
        logger.error(f"Error getting enterprise sessions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get sessions",
        ) from e


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(
    session_id: str,
    current_user: dict = Depends(get_enterprise_user),
    service: EnterpriseService = Depends(get_enterprise_service),
):
    """Get single session detail."""
    detail = service.get_session_detail(current_user["organization_id"], session_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    return detail


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(
    timeRange: str = Query(..., description="7d, 30d, 90d, or 1y"),
    current_user: dict = Depends(get_enterprise_user),
    service: EnterpriseService = Depends(get_enterprise_service),
):
    """Get analytics for the organization."""
    if timeRange not in ("7d", "30d", "90d", "1y"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="timeRange must be 7d, 30d, 90d, or 1y",
        )
    try:
        return service.get_analytics(
            current_user["organization_id"],
            time_range=timeRange,
        )
    except Exception as e:
        logger.error(f"Error getting enterprise analytics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analytics",
        ) from e


@router.get("/settings", response_model=OrganizationSettingsResponse)
async def get_settings(
    current_user: dict = Depends(get_enterprise_user),
    service: EnterpriseService = Depends(get_enterprise_service),
):
    """Get organization settings."""
    try:
        return service.get_settings(current_user["organization_id"])
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error getting enterprise settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get settings",
        ) from e


@router.patch("/settings", response_model=OrganizationSettingsResponse)
async def update_settings(
    patch: OrganizationSettingsPatch,
    current_user: dict = Depends(get_enterprise_user),
    service: EnterpriseService = Depends(get_enterprise_service),
):
    """Update organization settings (partial PATCH)."""
    patch_dict = patch.model_dump(exclude_none=True)
    if not patch_dict:
        return service.get_settings(current_user["organization_id"])
    try:
        return service.update_settings(
            current_user["organization_id"],
            patch_dict,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Error updating enterprise settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update settings",
        ) from e


@router.post("/organizations", response_model=CreateOrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization_self_serve(
    request: CreateOrganizationRequest,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """
    Create a new organization (self-serve).
    Authenticated user without an org can create one; they become the first member.
    Returns 400 if user already has an organization.
    """
    from app.database.models import Organization, OrganizationSettings, Department, User
    from uuid import UUID

    user = db.query(User).filter(User.id == UUID(current_user["id"])).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has an organization",
        )
    org = Organization(name=request.name, domain=request.domain)
    db.add(org)
    db.flush()
    settings_obj = OrganizationSettings(
        organization_id=org.id,
        timezone="UTC",
        language="en",
        features={"sso": False, "analytics": True, "customBranding": False, "advancedReporting": True, "userManagement": True},
        notifications={"email": True, "weekly": True, "monthly": True, "alerts": True},
        security={"passwordPolicy": "strong", "sessionTimeout": 30, "twoFactor": False, "ipRestrictions": False},
    )
    db.add(settings_obj)
    default_dept = Department(organization_id=org.id, name="Default")
    db.add(default_dept)
    user.organization_id = org.id
    db.commit()
    db.refresh(org)
    logger.info(f"User {current_user['id']} created organization: {org.name}")
    return CreateOrganizationResponse(
        id=str(org.id),
        name=org.name,
        domain=org.domain,
    )


@router.get("/departments", response_model=DepartmentsResponse)
async def get_departments(
    current_user: dict = Depends(get_enterprise_user),
    service: EnterpriseService = Depends(get_enterprise_service),
):
    """Get departments for the organization."""
    try:
        return service.get_departments(current_user["organization_id"])
    except Exception as e:
        logger.error(f"Error getting enterprise departments: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get departments",
        ) from e
