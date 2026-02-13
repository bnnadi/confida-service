"""
Consent router for GDPR/CCPA compliance.

Manages user consent preferences and consent history.
"""
from fastapi import APIRouter, Depends, status, Query, Request
from sqlalchemy.orm import Session
from app.services.database_service import get_db
from app.services.consent_service import ConsentService
from app.middleware.auth_middleware import get_current_user_required
from app.models.schemas import (
    ConsentPreferencesRequest,
    ConsentPreferencesResponse,
    ConsentItemResponse,
    ConsentHistoryResponse,
    ConsentHistoryItem,
)
router = APIRouter(prefix="/api/v1/consent", tags=["consent"])


@router.get("/", response_model=ConsentPreferencesResponse)
async def get_consent(
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db),
):
    """
    Get current consent preferences.

    Returns consent preferences for essential, analytics, and marketing.
    Uses defaults for types not yet explicitly set.
    """
    service = ConsentService(db)
    consents = service.get_consents(current_user["id"])
    return ConsentPreferencesResponse(
        consents=[
            ConsentItemResponse(
                consent_type=c["consent_type"],
                granted=c["granted"],
                updated_at=c.get("updated_at"),
            )
            for c in consents
        ]
    )


@router.put("/", response_model=ConsentPreferencesResponse)
async def update_consent(
    request: ConsentPreferencesRequest,
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db),
    req: Request = None,
):
    """
    Update consent preferences.

    Accepts a list of consent_type and granted pairs.
    Valid consent types: essential, analytics, marketing.
    """
    service = ConsentService(db)
    ip_address = req.client.host if req else None
    preferences = {c.consent_type: c.granted for c in request.consents}
    consents = service.update_consents(
        current_user["id"],
        preferences,
        ip_address=ip_address,
    )
    return ConsentPreferencesResponse(
        consents=[
            ConsentItemResponse(
                consent_type=c["consent_type"],
                granted=c["granted"],
                updated_at=c.get("updated_at"),
            )
            for c in consents
        ]
    )


@router.get("/history", response_model=ConsentHistoryResponse)
async def get_consent_history(
    current_user: dict = Depends(get_current_user_required),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=100, description="Max history entries"),
):
    """
    Get consent change history.

    Returns audit trail of consent grants and withdrawals, most recent first.
    """
    service = ConsentService(db)
    history = service.get_consent_history(current_user["id"], limit=limit)
    return ConsentHistoryResponse(
        history=[
            ConsentHistoryItem(
                consent_type=h["consent_type"],
                action=h["action"],
                created_at=h["created_at"],
            )
            for h in history
        ]
    )
