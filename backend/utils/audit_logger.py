"""
Phase 4: Security audit logging utilities
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
import logging

from database import SecurityAudit, LoginActivity

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Centralized security audit logging system.
    Tracks all security-related events with risk assessment.
    """

    # Event types
    EVENT_TYPES = {
        # Authentication events
        "login_success": "low",
        "login_failed": "medium",
        "login_failed_multiple": "high",
        "logout": "low",
        # Password events
        "password_change": "low",
        "password_reset_request": "low",
        "password_reset_success": "medium",
        "password_reset_failed": "medium",
        # Account events
        "account_created": "low",
        "account_deleted": "medium",
        "email_changed": "medium",
        "email_verified": "low",
        # OAuth events
        "oauth_link": "low",
        "oauth_unlink": "medium",
        # API key events
        "api_key_created": "low",
        "api_key_updated": "low",
        "api_key_deleted": "low",
        # Session events
        "session_created": "low",
        "session_revoked": "low",
        "all_sessions_revoked": "medium",
        # Security events
        "suspicious_login": "high",
        "concurrent_locations": "high",
        "account_enumeration": "high",
        "rate_limit_exceeded": "medium",
        # Settings events
        "security_settings_changed": "low",
    }

    @staticmethod
    def log_security_event(
        event_type: str,
        db: Session,
        user_id: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        risk_level: Optional[str] = None,
    ) -> SecurityAudit:
        """
        Log a security event to the audit table.

        Args:
            event_type: Type of security event
            db: Database session
            user_id: User ID if applicable
            ip_address: IP address of request
            user_agent: User agent string
            details: Additional event details as JSON
            risk_level: Override risk level (low, medium, high)

        Returns:
            Created SecurityAudit record
        """
        # Determine risk level
        if risk_level is None:
            risk_level = AuditLogger.EVENT_TYPES.get(event_type, "low")

        # Create audit record
        audit = SecurityAudit(
            user_id=user_id,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
            details=details,
            risk_level=risk_level,
        )

        db.add(audit)
        db.commit()
        db.refresh(audit)

        logger.info(
            f"Security audit: {event_type} (risk: {risk_level}), "
            f"user_id={user_id}, ip={ip_address}"
        )

        return audit

    @staticmethod
    def log_login_activity(
        user_id: int,
        action: str,
        db: Session,
        success: bool = True,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> LoginActivity:
        """
        Log user login activity.

        Args:
            user_id: User ID
            action: Action type (login, logout, etc.)
            db: Database session
            success: Whether action was successful
            ip_address: IP address
            user_agent: User agent string
            details: Additional details

        Returns:
            Created LoginActivity record
        """
        activity = LoginActivity(
            user_id=user_id,
            action=action,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
            details=details,
        )

        db.add(activity)
        db.commit()
        db.refresh(activity)

        # Keep only last 100 activities per user
        AuditLogger._cleanup_old_login_activities(user_id, db)

        return activity

    @staticmethod
    def _cleanup_old_login_activities(user_id: int, db: Session, keep_count: int = 100):
        """
        Keep only the most recent login activities for a user.

        Args:
            user_id: User ID
            db: Database session
            keep_count: Number of recent activities to keep
        """
        # Get count of activities
        total = db.query(LoginActivity).filter(LoginActivity.user_id == user_id).count()

        if total > keep_count:
            # Get activities to delete (oldest ones)
            to_delete = (
                db.query(LoginActivity)
                .filter(LoginActivity.user_id == user_id)
                .order_by(LoginActivity.created_at.desc())
                .offset(keep_count)
                .all()
            )

            for activity in to_delete:
                db.delete(activity)

            db.commit()
            logger.debug(f"Cleaned up {len(to_delete)} old login activities for user {user_id}")

    @staticmethod
    def detect_suspicious_login(
        user_id: int, ip_address: str, db: Session, time_window_minutes: int = 10
    ) -> bool:
        """
        Detect suspicious login patterns.

        Args:
            user_id: User ID
            ip_address: Current IP address
            db: Database session
            time_window_minutes: Time window to check for patterns

        Returns:
            True if suspicious activity detected
        """
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=time_window_minutes)

        # Check for multiple failed logins
        failed_logins = (
            db.query(LoginActivity)
            .filter(
                LoginActivity.user_id == user_id,
                LoginActivity.action == "login",
                LoginActivity.success == False,
                LoginActivity.created_at >= window_start,
            )
            .count()
        )

        if failed_logins >= 5:
            AuditLogger.log_security_event(
                "login_failed_multiple",
                db,
                user_id=user_id,
                ip_address=ip_address,
                details={
                    "failed_attempts": failed_logins,
                    "time_window_minutes": time_window_minutes,
                },
                risk_level="high",
            )
            return True

        # Check for concurrent logins from different locations
        recent_activities = (
            db.query(LoginActivity)
            .filter(
                LoginActivity.user_id == user_id,
                LoginActivity.action == "login",
                LoginActivity.success == True,
                LoginActivity.created_at >= window_start,
            )
            .all()
        )

        if len(recent_activities) >= 2:
            # Check if different IP addresses
            ip_addresses = {a.ip_address for a in recent_activities if a.ip_address}
            if len(ip_addresses) > 1 and ip_address not in ip_addresses:
                AuditLogger.log_security_event(
                    "concurrent_locations",
                    db,
                    user_id=user_id,
                    ip_address=ip_address,
                    details={"ip_addresses": list(ip_addresses)},
                    risk_level="high",
                )
                return True

        return False

    @staticmethod
    def detect_account_enumeration(
        ip_address: str, db: Session, time_window_minutes: int = 10, threshold: int = 10
    ) -> bool:
        """
        Detect account enumeration attempts.

        Args:
            ip_address: IP address to check
            db: Database session
            time_window_minutes: Time window
            threshold: Number of failed attempts to trigger

        Returns:
            True if enumeration detected
        """
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=time_window_minutes)

        # Count failed login attempts from this IP
        failed_attempts = (
            db.query(SecurityAudit)
            .filter(
                SecurityAudit.event_type == "login_failed",
                SecurityAudit.ip_address == ip_address,
                SecurityAudit.created_at >= window_start,
            )
            .count()
        )

        if failed_attempts >= threshold:
            AuditLogger.log_security_event(
                "account_enumeration",
                db,
                ip_address=ip_address,
                details={
                    "failed_attempts": failed_attempts,
                    "time_window_minutes": time_window_minutes,
                },
                risk_level="high",
            )
            return True

        return False

    @staticmethod
    def get_recent_audit_logs(
        db: Session,
        user_id: Optional[int] = None,
        risk_level: Optional[str] = None,
        limit: int = 100,
    ) -> list:
        """
        Get recent audit logs with optional filtering.

        Args:
            db: Database session
            user_id: Filter by user ID
            risk_level: Filter by risk level
            limit: Maximum number of records

        Returns:
            List of SecurityAudit records
        """
        query = db.query(SecurityAudit)

        if user_id is not None:
            query = query.filter(SecurityAudit.user_id == user_id)

        if risk_level is not None:
            query = query.filter(SecurityAudit.risk_level == risk_level)

        return query.order_by(SecurityAudit.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_user_login_history(user_id: int, db: Session, limit: int = 50) -> list:
        """
        Get user's login activity history.

        Args:
            user_id: User ID
            db: Database session
            limit: Maximum number of records

        Returns:
            List of LoginActivity records
        """
        return (
            db.query(LoginActivity)
            .filter(LoginActivity.user_id == user_id)
            .order_by(LoginActivity.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def cleanup_old_audits(db: Session, days: int = 90) -> int:
        """
        Clean up old audit records (except high risk ones).

        Args:
            db: Database session
            days: Keep records from last N days

        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Delete low and medium risk audits older than cutoff
        old_audits = (
            db.query(SecurityAudit)
            .filter(
                SecurityAudit.created_at < cutoff_date,
                SecurityAudit.risk_level.in_(["low", "medium"]),
            )
            .all()
        )

        count = len(old_audits)
        for audit in old_audits:
            db.delete(audit)

        db.commit()
        logger.info(f"Cleaned up {count} old audit records")
        return count
