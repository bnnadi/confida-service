"""
Audit service for data access logging (INT-31, INT-32).

Provides audit trail logging and query functions for admin audit dashboard
and compliance reporting.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.database.models import DataAccessLog, ConsentHistory
from app.utils.uuid_utils import to_uuid
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Thresholds for suspicious activity detection (INT-32)
SUSPICIOUS_EXPORTS_PER_DAY = 5
SUSPICIOUS_ACCESS_PER_HOUR = 50
SUSPICIOUS_UNIQUE_IPS_PER_USER = 10


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


def get_data_access_logs(
    db: Session,
    user_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    action: Optional[str] = None,
    since: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """Query data access logs for admin audit dashboard (INT-32)."""
    q = db.query(DataAccessLog)
    if user_id:
        uid = to_uuid(user_id)
        q = q.filter(DataAccessLog.user_id == uid)
    if resource_type:
        q = q.filter(DataAccessLog.resource_type == resource_type)
    if action:
        q = q.filter(DataAccessLog.action == action)
    if since:
        q = q.filter(DataAccessLog.created_at >= since)
    rows = q.order_by(DataAccessLog.created_at.desc()).limit(limit).offset(offset).all()
    return [
        {
            "id": str(r.id),
            "user_id": str(r.user_id) if r.user_id else None,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "action": r.action,
            "ip_address": r.ip_address,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def get_audit_summary(
    db: Session,
    since: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Get audit log summary for admin dashboard (INT-32)."""
    if not since:
        since = datetime.utcnow() - timedelta(days=7)
    q = db.query(
        DataAccessLog.resource_type,
        DataAccessLog.action,
        func.count(DataAccessLog.id).label("count"),
    ).filter(DataAccessLog.created_at >= since).group_by(
        DataAccessLog.resource_type,
        DataAccessLog.action,
    )
    rows = q.all()
    total = sum(r.count for r in rows)
    by_resource = {}
    by_action = {}
    for r in rows:
        by_resource[r.resource_type] = by_resource.get(r.resource_type, 0) + r.count
        by_action[r.action] = by_action.get(r.action, 0) + r.count
    return {
        "total_events": total,
        "since": since.isoformat(),
        "by_resource_type": by_resource,
        "by_action": by_action,
    }


def get_consent_history_admin(
    db: Session,
    user_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    since: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Query consent history for admin audit (INT-32)."""
    q = db.query(ConsentHistory)
    if user_id:
        uid = to_uuid(user_id)
        q = q.filter(ConsentHistory.user_id == uid)
    if since:
        q = q.filter(ConsentHistory.created_at >= since)
    rows = q.order_by(ConsentHistory.created_at.desc()).limit(limit).offset(offset).all()
    return [
        {
            "id": str(r.id),
            "user_id": str(r.user_id),
            "consent_type": r.consent_type,
            "action": r.action,
            "ip_address": r.ip_address,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def detect_suspicious_activity(
    db: Session,
    since: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Detect suspicious activity patterns in audit logs (INT-32)."""
    if not since:
        since = datetime.utcnow() - timedelta(days=1)
    findings = []

    # High export volume per user
    export_counts = (
        db.query(DataAccessLog.user_id, func.count(DataAccessLog.id).label("cnt"))
        .filter(
            DataAccessLog.created_at >= since,
            DataAccessLog.action == "export",
            DataAccessLog.resource_type == "export",
        )
        .group_by(DataAccessLog.user_id)
        .having(func.count(DataAccessLog.id) >= SUSPICIOUS_EXPORTS_PER_DAY)
        .all()
    )
    for row in export_counts:
        if row.user_id:
            findings.append({
                "type": "high_export_volume",
                "user_id": str(row.user_id),
                "count": row.cnt,
                "threshold": SUSPICIOUS_EXPORTS_PER_DAY,
                "message": f"User {row.user_id} performed {row.cnt} data exports in the period",
            })

    # High access volume per user (many reads/writes in short time)
    access_counts = (
        db.query(DataAccessLog.user_id, func.count(DataAccessLog.id).label("cnt"))
        .filter(DataAccessLog.created_at >= since, DataAccessLog.user_id.isnot(None))
        .group_by(DataAccessLog.user_id)
        .having(func.count(DataAccessLog.id) >= SUSPICIOUS_ACCESS_PER_HOUR)
        .all()
    )
    for row in access_counts:
        if row.user_id:
            findings.append({
                "type": "high_access_volume",
                "user_id": str(row.user_id),
                "count": row.cnt,
                "threshold": SUSPICIOUS_ACCESS_PER_HOUR,
                "message": f"User {row.user_id} had {row.cnt} data access events in the period",
            })

    # Multiple IPs per user (possible account sharing or compromise)
    ip_counts = (
        db.query(
            DataAccessLog.user_id,
            func.count(distinct(DataAccessLog.ip_address)).label("ip_count"),
        )
        .filter(
            DataAccessLog.created_at >= since,
            DataAccessLog.user_id.isnot(None),
            DataAccessLog.ip_address.isnot(None),
        )
        .group_by(DataAccessLog.user_id)
        .having(func.count(distinct(DataAccessLog.ip_address)) >= SUSPICIOUS_UNIQUE_IPS_PER_USER)
        .all()
    )
    for row in ip_counts:
        if row.user_id:
            findings.append({
                "type": "multiple_ips",
                "user_id": str(row.user_id),
                "unique_ips": row.ip_count,
                "threshold": SUSPICIOUS_UNIQUE_IPS_PER_USER,
                "message": f"User {row.user_id} accessed from {row.ip_count} different IPs",
            })

    return findings


def get_compliance_report(
    db: Session,
    since: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Generate compliance report aggregating audit and consent data (INT-32)."""
    if not since:
        since = datetime.utcnow() - timedelta(days=30)
    total_access = db.query(func.count(DataAccessLog.id)).filter(
        DataAccessLog.created_at >= since
    ).scalar() or 0
    total_consent_changes = db.query(func.count(ConsentHistory.id)).filter(
        ConsentHistory.created_at >= since
    ).scalar() or 0
    export_count = db.query(func.count(DataAccessLog.id)).filter(
        DataAccessLog.created_at >= since,
        DataAccessLog.action == "export",
    ).scalar() or 0
    delete_count = db.query(func.count(DataAccessLog.id)).filter(
        DataAccessLog.created_at >= since,
        DataAccessLog.action == "delete",
    ).scalar() or 0
    suspicious = detect_suspicious_activity(db, since)
    return {
        "period": {"since": since.isoformat()},
        "data_access": {
            "total_events": total_access,
            "exports": export_count,
            "deletes": delete_count,
        },
        "consent": {
            "total_changes": total_consent_changes,
        },
        "suspicious_activity_count": len(suspicious),
        "suspicious_findings": suspicious[:20],
    }
