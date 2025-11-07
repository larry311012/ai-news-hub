"""Advanced security audit logging"""
from sqlalchemy.orm import Session
from database import SecurityAudit
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)


class AuditLogger:
    """Enhanced audit logging with risk assessment"""

    RISK_SCORES = {
        "login": 1,
        "failed_login": 3,
        "password_change": 5,
        "email_change": 7,
        "oauth_link": 4,
        "oauth_unlink": 4,
        "api_key_create": 5,
        "api_key_delete": 5,
        "account_delete": 10,
        "suspicious_activity": 8,
        "password_reset_request": 4,
        "password_reset_complete": 6,
        "verification_sent": 2,
        "verification_complete": 3,
        "session_created": 1,
        "session_deleted": 1,
    }

    @staticmethod
    def log_event(
        db: Session,
        user_id: int,
        event_type: str,
        ip_address: str,
        user_agent: str = None,
        details: dict = None,
        auto_assess_risk: bool = True,
    ):
        """Log security event with automatic risk assessment"""

        # Calculate risk level
        if auto_assess_risk:
            risk_level = AuditLogger._assess_risk(db, user_id, event_type, ip_address)
        else:
            risk_level = "low"

        # Create audit log
        audit = SecurityAudit(
            user_id=user_id,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
            details=details or {},
            risk_level=risk_level,
        )

        db.add(audit)
        db.commit()

        # Check if action needed
        if risk_level == "high":
            AuditLogger._trigger_security_alert(user_id, event_type, details)

    @staticmethod
    def _assess_risk(db: Session, user_id: int, event_type: str, ip_address: str) -> str:
        """Assess risk level of an event"""
        base_score = AuditLogger.RISK_SCORES.get(event_type, 1)

        # Check for suspicious patterns
        # 1. New IP address?
        recent_ips = (
            db.query(SecurityAudit)
            .filter(SecurityAudit.user_id == user_id)
            .order_by(SecurityAudit.created_at.desc())
            .limit(10)
            .all()
        )

        known_ips = {audit.ip_address for audit in recent_ips}
        if ip_address not in known_ips:
            base_score += 2

        # 2. Rapid successive events?
        recent_events = (
            db.query(SecurityAudit)
            .filter(
                SecurityAudit.user_id == user_id,
                SecurityAudit.created_at >= datetime.utcnow() - timedelta(minutes=5),
            )
            .count()
        )

        if recent_events > 10:
            base_score += 3

        # 3. Multiple failed attempts?
        if event_type == "failed_login":
            recent_failures = (
                db.query(SecurityAudit)
                .filter(
                    SecurityAudit.user_id == user_id,
                    SecurityAudit.event_type == "failed_login",
                    SecurityAudit.created_at >= datetime.utcnow() - timedelta(minutes=15),
                )
                .count()
            )

            if recent_failures >= 3:
                base_score += 4

        # Determine risk level
        if base_score >= 8:
            return "high"
        elif base_score >= 5:
            return "medium"
        else:
            return "low"

    @staticmethod
    def _trigger_security_alert(user_id: int, event_type: str, details: dict):
        """Trigger security alert (email, webhook, etc.)"""
        # TODO: Send email notification
        # TODO: Webhook to security monitoring
        logger.warning(
            f"HIGH RISK SECURITY EVENT: user_id={user_id}, "
            f"event={event_type}, details={details}"
        )

    @staticmethod
    def get_user_security_summary(db: Session, user_id: int, days: int = 30) -> dict:
        """Get security summary for a user"""
        cutoff = datetime.utcnow() - timedelta(days=days)

        audits = (
            db.query(SecurityAudit)
            .filter(SecurityAudit.user_id == user_id, SecurityAudit.created_at >= cutoff)
            .all()
        )

        # Calculate statistics
        total_events = len(audits)
        high_risk_events = sum(1 for a in audits if a.risk_level == "high")
        medium_risk_events = sum(1 for a in audits if a.risk_level == "medium")
        low_risk_events = sum(1 for a in audits if a.risk_level == "low")

        # Count by event type
        event_counts = {}
        for audit in audits:
            event_counts[audit.event_type] = event_counts.get(audit.event_type, 0) + 1

        # Get unique IPs
        unique_ips = len(set(a.ip_address for a in audits if a.ip_address))

        return {
            "total_events": total_events,
            "high_risk_events": high_risk_events,
            "medium_risk_events": medium_risk_events,
            "low_risk_events": low_risk_events,
            "event_counts": event_counts,
            "unique_ips": unique_ips,
            "period_days": days,
        }

    @staticmethod
    def detect_suspicious_pattern(db: Session, user_id: int) -> tuple[bool, str]:
        """
        Detect suspicious patterns in user activity

        Returns:
            (is_suspicious, reason)
        """
        # Check for rapid password changes
        recent_password_changes = (
            db.query(SecurityAudit)
            .filter(
                SecurityAudit.user_id == user_id,
                SecurityAudit.event_type == "password_change",
                SecurityAudit.created_at >= datetime.utcnow() - timedelta(hours=24),
            )
            .count()
        )

        if recent_password_changes >= 3:
            return True, "Multiple password changes in 24 hours"

        # Check for multiple failed logins
        recent_failures = (
            db.query(SecurityAudit)
            .filter(
                SecurityAudit.user_id == user_id,
                SecurityAudit.event_type == "failed_login",
                SecurityAudit.created_at >= datetime.utcnow() - timedelta(hours=1),
            )
            .count()
        )

        if recent_failures >= 5:
            return True, "Multiple failed login attempts"

        # Check for logins from many different IPs
        recent_logins = (
            db.query(SecurityAudit)
            .filter(
                SecurityAudit.user_id == user_id,
                SecurityAudit.event_type == "login",
                SecurityAudit.created_at >= datetime.utcnow() - timedelta(hours=24),
            )
            .all()
        )

        unique_ips = len(set(a.ip_address for a in recent_logins if a.ip_address))
        if unique_ips >= 5:
            return True, "Logins from multiple IP addresses"

        return False, ""
