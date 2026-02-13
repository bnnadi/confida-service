"""
Data rights router for GDPR/CCPA compliance.

Provides user data export (Right to Access) and account deletion (Right to Erasure).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.services.database_service import get_db
from app.services.data_rights_service import DataRightsService
from app.services.auth_service import AuthService
from app.middleware.auth_middleware import get_current_user_required
from app.models.schemas import DeleteAccountRequest, DataExportResponse
router = APIRouter(prefix="/api/v1/data-rights", tags=["data-rights"])


@router.get("/export", response_model=DataExportResponse)
async def export_user_data(
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """
    Export all user data (GDPR Right to Access).

    Returns a complete export of user profile, sessions, answers, performance,
    analytics events, goals, and consent preferences.
    Excludes sensitive fields such as password hash.
    """
    service = DataRightsService(db)
    data = service.export_user_data(current_user["id"])
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    return DataExportResponse(**data)


@router.post("/delete-account", status_code=status.HTTP_200_OK)
async def delete_account(
    request: DeleteAccountRequest,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """
    Delete user account and all associated data (GDPR Right to Erasure).

    Requires confirmation and current password for security.
    This action is irreversible.
    """
    auth_service = AuthService(db)
    user = auth_service.get_user_by_id(current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not auth_service.verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password",
        )

    service = DataRightsService(db)
    success = service.delete_user_account(current_user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "Account deleted successfully"}
