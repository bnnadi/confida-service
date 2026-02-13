"""
Consent service for GDPR/CCPA compliance.

Manages user consent preferences and consent change history.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.models import UserConsent, ConsentHistory
from app.utils.uuid_utils import to_uuid
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Allowed consent types
ALLOWED_CONSENT_TYPES = {"essential", "analytics", "marketing"}

# Default consent values for new users
DEFAULT_CONSENTS = {
    "essential": True,
    "analytics": True,
    "marketing": False,
}


class ConsentService:
    """Service for managing user consent preferences."""

    def __init__(self, db: Session):
        self.db = db

    def get_consents(self, user_id) -> List[dict]:
        """
        Get current consent preferences for a user.
        Returns defaults for consent types not yet set.
        """
        uid = to_uuid(user_id)
        rows = self.db.query(UserConsent).filter(UserConsent.user_id == uid).all()

        # Build dict of stored consents
        stored = {r.consent_type: r for r in rows}

        # Return all consent types with stored or default values
        result = []
        for consent_type in ALLOWED_CONSENT_TYPES:
            if consent_type in stored:
                r = stored[consent_type]
                result.append({
                    "consent_type": r.consent_type,
                    "granted": r.granted,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                })
            else:
                result.append({
                    "consent_type": consent_type,
                    "granted": DEFAULT_CONSENTS.get(consent_type, False),
                    "updated_at": None,
                })
        return result

    def update_consent(
        self,
        user_id,
        consent_type: str,
        granted: bool,
        ip_address: Optional[str] = None,
    ) -> UserConsent:
        """Update a single consent preference and append to history."""
        if consent_type not in ALLOWED_CONSENT_TYPES:
            raise ValueError(f"Invalid consent_type: {consent_type}")

        uid = to_uuid(user_id)
        existing = (
            self.db.query(UserConsent)
            .filter(UserConsent.user_id == uid, UserConsent.consent_type == consent_type)
            .first()
        )

        if existing:
            existing.granted = granted
            self.db.commit()
            self.db.refresh(existing)
            consent = existing
        else:
            consent = UserConsent(
                user_id=uid,
                consent_type=consent_type,
                granted=granted,
            )
            self.db.add(consent)
            self.db.commit()
            self.db.refresh(consent)

        # Append to history
        action = "granted" if granted else "withdrawn"
        history_entry = ConsentHistory(
            user_id=uid,
            consent_type=consent_type,
            action=action,
            ip_address=ip_address,
        )
        self.db.add(history_entry)
        self.db.commit()

        logger.info(f"Consent updated: user={uid}, type={consent_type}, granted={granted}")
        return consent

    def update_consents(
        self,
        user_id,
        preferences: dict,
        ip_address: Optional[str] = None,
    ) -> List[dict]:
        """Bulk update consent preferences."""
        uid = to_uuid(user_id)
        for consent_type, granted in preferences.items():
            if consent_type in ALLOWED_CONSENT_TYPES:
                self.update_consent(uid, consent_type, granted, ip_address)

        return self.get_consents(uid)

    def get_consent_history(self, user_id, limit: int = 50) -> List[dict]:
        """Get consent change history for a user, most recent first."""
        uid = to_uuid(user_id)
        rows = (
            self.db.query(ConsentHistory)
            .filter(ConsentHistory.user_id == uid)
            .order_by(ConsentHistory.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "consent_type": r.consent_type,
                "action": r.action,
                "created_at": r.created_at.isoformat() if r.created_at else "",
            }
            for r in rows
        ]
