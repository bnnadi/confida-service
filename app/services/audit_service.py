"""
Audit service for data access logging (INT-31).
"""
from typing import Optional

from sqlalchemy.orm import Session

from app.database.models import DataAccessLog
from app.utils.uuid_utils import to_uuid
from app.utils.logger import get_logger

logger = get_logger(__name__)


def log_data_access(
    db: Session,
    user_id: str,
    resource_type: str,
    action: str,
    resource_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> None:
    """Log a data access event for audit trail."""
    try:
        uid = to_uuid(user_id) if user_id else None
        log_entry = DataAccessLog(
            user_id=uid,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            ip_address=ip_address,
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to log data access: {e}")
        db.rollback()
