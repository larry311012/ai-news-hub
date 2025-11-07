"""Account security features - lockouts, suspicious activity"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database import User, SecurityAudit


class AccountLockout:
    """Manage account lockouts for security"""

    LOCKOUT_THRESHOLD = 5  # Failed attempts before lockout
    LOCKOUT_DURATION = 1800  # 30 minutes in seconds

    @staticmethod
    def record_failed_login(email: str, ip_address: str, db: Session):
        """Record failed login attempt"""
        # Create audit entry
        audit = SecurityAudit(
            user_id=None,  # Don't know user_id yet
            event_type="failed_login",
            ip_address=ip_address,
            details={"email": email},
            risk_level="medium",
        )
        db.add(audit)
        db.commit()

        # Check if account should be locked
        return AccountLockout.should_lock_account(email, db)

    @staticmethod
    def should_lock_account(email: str, db: Session) -> bool:
        """Check if account should be locked based on failed attempts"""
        # Count recent failed attempts
        cutoff = datetime.utcnow() - timedelta(seconds=AccountLockout.LOCKOUT_DURATION)

        failed_attempts = (
            db.query(SecurityAudit)
            .filter(
                SecurityAudit.event_type == "failed_login",
                SecurityAudit.details["email"].astext == email,
                SecurityAudit.created_at >= cutoff,
            )
            .count()
        )

        return failed_attempts >= AccountLockout.LOCKOUT_THRESHOLD

    @staticmethod
    def is_account_locked(email: str, db: Session) -> bool:
        """Check if account is currently locked"""
        cutoff = datetime.utcnow() - timedelta(seconds=AccountLockout.LOCKOUT_DURATION)

        # Get most recent failed login
        recent_failure = (
            db.query(SecurityAudit)
            .filter(
                SecurityAudit.event_type == "failed_login",
                SecurityAudit.details["email"].astext == email,
                SecurityAudit.created_at >= cutoff,
            )
            .order_by(SecurityAudit.created_at.desc())
            .first()
        )

        if not recent_failure:
            return False

        # Check if threshold exceeded in window
        return AccountLockout.should_lock_account(email, db)

    @staticmethod
    def clear_lockout(email: str, db: Session):
        """Clear lockout after successful login"""
        # Just recording successful login will naturally expire old failures
        pass

    @staticmethod
    def get_remaining_lockout_time(email: str, db: Session) -> int:
        """Get remaining lockout time in seconds"""
        cutoff = datetime.utcnow() - timedelta(seconds=AccountLockout.LOCKOUT_DURATION)

        # Get oldest failed login in window
        oldest_failure = (
            db.query(SecurityAudit)
            .filter(
                SecurityAudit.event_type == "failed_login",
                SecurityAudit.details["email"].astext == email,
                SecurityAudit.created_at >= cutoff,
            )
            .order_by(SecurityAudit.created_at.asc())
            .first()
        )

        if not oldest_failure:
            return 0

        # Calculate when lockout expires
        lockout_expires = oldest_failure.created_at + timedelta(
            seconds=AccountLockout.LOCKOUT_DURATION
        )
        remaining = (lockout_expires - datetime.utcnow()).total_seconds()

        return max(0, int(remaining))
