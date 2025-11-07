"""
Quota Checking Middleware

Enforces daily post generation quotas based on user tier:
- Guest users: 1 post (no publishing)
- Free users: Unlimited posts (open source - no restrictions!)
- Paid users: Unlimited posts (legacy tier)

NOTE: This is now an open-source self-hosted tool.
      All users get unlimited access to all features.
"""
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, Dict
import logging

from database import User, AdminSettings

logger = logging.getLogger(__name__)


class QuotaManager:
    """Manages user quota checking and reset logic"""

    # Default quota limits by tier (open-source - very generous!)
    DEFAULT_QUOTAS = {
        "guest": 1,  # Guest preview only
        "free": 999999,  # Unlimited for free tier (open source!)
        "paid": 999999,  # Unlimited for legacy paid tier
    }

    def __init__(self, db: Session):
        self.db = db

    def get_quota_limit(self, user_tier: str) -> int:
        """
        Get quota limit for user tier

        Args:
            user_tier: User tier (guest, free, paid)

        Returns:
            Quota limit for the tier
        """
        # Try to get from admin settings first
        setting_key = f"{user_tier}_quota_limit"
        setting = self.db.query(AdminSettings).filter(AdminSettings.key == setting_key).first()

        if setting:
            try:
                return int(setting.value)
            except ValueError:
                logger.warning(
                    f"Invalid quota value in admin settings for {setting_key}, using default"
                )

        # Fall back to default
        return self.DEFAULT_QUOTAS.get(user_tier, 999999)

    def check_quota(self, user: User) -> tuple[bool, Dict]:
        """
        Check if user has quota remaining

        Args:
            user: User model instance

        Returns:
            Tuple of (has_quota, quota_info_dict)
        """
        # Reset quota if needed
        self._reset_quota_if_needed(user)

        quota_limit = self.get_quota_limit(user.user_tier)
        remaining = max(0, quota_limit - user.daily_quota_used)

        quota_info = {
            "tier": user.user_tier,
            "limit": quota_limit,
            "used": user.daily_quota_used,
            "remaining": remaining,
            "reset_at": user.quota_reset_date.isoformat() if user.quota_reset_date else None,
        }

        has_quota = user.daily_quota_used < quota_limit

        return has_quota, quota_info

    def increment_quota(self, user: User) -> None:
        """
        Increment user's daily quota usage

        Args:
            user: User model instance
        """
        # Reset if needed before incrementing
        self._reset_quota_if_needed(user)

        user.daily_quota_used += 1
        self.db.commit()
        self.db.refresh(user)

        logger.info(
            f"Incremented quota for user {user.id} ({user.user_tier}): {user.daily_quota_used}/{self.get_quota_limit(user.user_tier)}"
        )

    def _reset_quota_if_needed(self, user: User) -> bool:
        """
        Reset user quota if reset date has passed

        Args:
            user: User model instance

        Returns:
            True if quota was reset, False otherwise
        """
        now = datetime.utcnow()

        # Initialize reset date if not set
        if not user.quota_reset_date:
            user.quota_reset_date = self._get_next_reset_date(now)
            self.db.commit()
            return False

        # Check if reset is needed
        if now >= user.quota_reset_date:
            user.daily_quota_used = 0
            user.quota_reset_date = self._get_next_reset_date(now)
            self.db.commit()
            self.db.refresh(user)

            logger.info(f"Reset quota for user {user.id} ({user.user_tier})")
            return True

        return False

    def _get_next_reset_date(self, from_date: datetime) -> datetime:
        """
        Calculate next quota reset date (midnight UTC next day)

        Args:
            from_date: Date to calculate from

        Returns:
            Next reset datetime
        """
        # Next midnight UTC
        next_day = from_date + timedelta(days=1)
        return next_day.replace(hour=0, minute=0, second=0, microsecond=0)

    def can_publish(self, user: User) -> bool:
        """
        Check if user can publish posts (not just generate)

        Guest users cannot publish, only preview.

        Args:
            user: User model instance

        Returns:
            True if user can publish, False otherwise
        """
        return user.user_tier != "guest"


def check_quota_dependency(user: User, db: Session) -> Dict:
    """
    Dependency function to check user quota

    Args:
        user: Current user from auth dependency
        db: Database session

    Returns:
        Quota info dict

    Raises:
        HTTPException: If quota exceeded
    """
    quota_manager = QuotaManager(db)
    has_quota, quota_info = quota_manager.check_quota(user)

    if not has_quota:
        logger.warning(f"Quota exceeded for user {user.id} ({user.user_tier})")

        # For open-source version, this should rarely happen (only for guests)
        raise HTTPException(
            status_code=429,
            detail={
                "error": "quota_exceeded",
                "message": f"Daily quota exceeded. You have used {quota_info['used']}/{quota_info['limit']} posts today.",
                "quota": quota_info,
                "upgrade_message": "Create a free account for unlimited posts!"
                if user.user_tier == "guest"
                else None,
            },
        )

    return quota_info


def check_publish_permission(user: User) -> bool:
    """
    Check if user can publish (not just generate preview)

    Args:
        user: Current user

    Returns:
        True if can publish, False if only preview allowed

    Raises:
        HTTPException: If guest user attempts to publish
    """
    if user.user_tier == "guest":
        raise HTTPException(
            status_code=403,
            detail={
                "error": "publish_not_allowed",
                "message": "Guest users can only preview posts. Please create a free account to publish.",
                "action": "Sign up for a free account to publish posts - it's completely free!",
            },
        )

    return True


# ============================================================================
# HELPER FUNCTIONS FOR API ENDPOINTS
# ============================================================================


def get_quota_info(user: User, db: Session) -> Dict:
    """
    Get quota information for user without checking/raising errors

    Args:
        user: User model instance
        db: Database session

    Returns:
        Quota info dict
    """
    quota_manager = QuotaManager(db)
    _, quota_info = quota_manager.check_quota(user)
    return quota_info


def increment_user_quota(user: User, db: Session) -> None:
    """
    Increment user's post generation quota

    Args:
        user: User model instance
        db: Database session
    """
    quota_manager = QuotaManager(db)
    quota_manager.increment_quota(user)
