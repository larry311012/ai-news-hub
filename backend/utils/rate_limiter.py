"""
Phase 4: Rate limiting utilities for API endpoints
"""
from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
import logging

from database import RateLimitLog

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded"""

    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Try again in {retry_after} seconds.")


class RateLimiter:
    """
    Rate limiter for API endpoints with database-backed storage.
    Uses sliding window approach for accurate rate limiting.
    """

    # Default rate limits: (max_attempts, window_minutes, block_duration_minutes)
    RATE_LIMITS = {
        "login": (5, 15, 15),  # 5 attempts per 15 minutes, block for 15 minutes
        "register": (5, 60, 60),  # 5 registrations per hour per IP
        "password_reset": (3, 60, 60),  # 3 reset requests per hour
        "email_verification": (3, 60, 60),  # 3 verification emails per hour
        "api_general": (100, 60, 5),  # 100 requests per hour, block for 5 minutes
    }

    @staticmethod
    def check_rate_limit(
        identifier: str,
        endpoint: str,
        db: Session,
        max_attempts: Optional[int] = None,
        window_minutes: Optional[int] = None,
        block_duration_minutes: Optional[int] = None,
    ) -> Tuple[bool, Optional[int]]:
        """
        Check if identifier has exceeded rate limit for endpoint.

        Args:
            identifier: IP address or user ID
            endpoint: Endpoint name (login, register, etc.)
            db: Database session
            max_attempts: Override max attempts
            window_minutes: Override time window
            block_duration_minutes: Override block duration

        Returns:
            Tuple of (is_allowed, retry_after_seconds)

        Raises:
            RateLimitExceeded: If rate limit is exceeded
        """
        # Get rate limit configuration
        if endpoint in RateLimiter.RATE_LIMITS:
            default_max, default_window, default_block = RateLimiter.RATE_LIMITS[endpoint]
            max_attempts = max_attempts or default_max
            window_minutes = window_minutes or default_window
            block_duration_minutes = block_duration_minutes or default_block
        else:
            # Use general API rate limit as default
            max_attempts = max_attempts or 100
            window_minutes = window_minutes or 60
            block_duration_minutes = block_duration_minutes or 5

        now = datetime.utcnow()
        window_start = now - timedelta(minutes=window_minutes)

        # Check for existing rate limit record
        rate_limit = (
            db.query(RateLimitLog)
            .filter(RateLimitLog.identifier == identifier, RateLimitLog.endpoint == endpoint)
            .first()
        )

        # Check if currently blocked
        if rate_limit and rate_limit.blocked_until:
            if rate_limit.blocked_until > now:
                retry_after = int((rate_limit.blocked_until - now).total_seconds())
                logger.warning(
                    f"Rate limit blocked: {identifier} on {endpoint}, "
                    f"retry after {retry_after}s"
                )
                raise RateLimitExceeded(retry_after)
            else:
                # Block expired, reset
                rate_limit.blocked_until = None
                rate_limit.attempt_count = 0
                rate_limit.window_start = now
                db.commit()

        # Check attempts in current window
        if rate_limit:
            # Check if we need to start a new window
            if rate_limit.window_start < window_start:
                # Start new window
                rate_limit.window_start = now
                rate_limit.attempt_count = 1
                db.commit()
                return True, None
            else:
                # Same window, increment count
                rate_limit.attempt_count += 1

                if rate_limit.attempt_count > max_attempts:
                    # Exceeded limit, block user
                    rate_limit.blocked_until = now + timedelta(minutes=block_duration_minutes)
                    db.commit()

                    retry_after = int(timedelta(minutes=block_duration_minutes).total_seconds())
                    logger.warning(
                        f"Rate limit exceeded: {identifier} on {endpoint}, "
                        f"blocked for {block_duration_minutes} minutes"
                    )
                    raise RateLimitExceeded(retry_after)

                db.commit()
                return True, None
        else:
            # First attempt, create record
            new_rate_limit = RateLimitLog(
                identifier=identifier, endpoint=endpoint, attempt_count=1, window_start=now
            )
            db.add(new_rate_limit)
            db.commit()
            return True, None

    @staticmethod
    def reset_rate_limit(identifier: str, endpoint: str, db: Session) -> None:
        """
        Reset rate limit for an identifier and endpoint.

        Args:
            identifier: IP address or user ID
            endpoint: Endpoint name
            db: Database session
        """
        rate_limit = (
            db.query(RateLimitLog)
            .filter(RateLimitLog.identifier == identifier, RateLimitLog.endpoint == endpoint)
            .first()
        )

        if rate_limit:
            db.delete(rate_limit)
            db.commit()
            logger.info(f"Reset rate limit: {identifier} on {endpoint}")

    @staticmethod
    def cleanup_old_records(db: Session, days: int = 7) -> int:
        """
        Clean up old rate limit records.

        Args:
            db: Database session
            days: Delete records older than this many days

        Returns:
            Number of records deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        old_records = (
            db.query(RateLimitLog)
            .filter(RateLimitLog.updated_at < cutoff_date, RateLimitLog.blocked_until.is_(None))
            .all()
        )

        count = len(old_records)
        for record in old_records:
            db.delete(record)

        db.commit()
        logger.info(f"Cleaned up {count} old rate limit records")
        return count

    @staticmethod
    def get_remaining_attempts(identifier: str, endpoint: str, db: Session) -> Optional[int]:
        """
        Get remaining attempts for an identifier and endpoint.

        Args:
            identifier: IP address or user ID
            endpoint: Endpoint name
            db: Database session

        Returns:
            Number of remaining attempts or None if no limit record exists
        """
        if endpoint not in RateLimiter.RATE_LIMITS:
            return None

        max_attempts, window_minutes, _ = RateLimiter.RATE_LIMITS[endpoint]
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=window_minutes)

        rate_limit = (
            db.query(RateLimitLog)
            .filter(RateLimitLog.identifier == identifier, RateLimitLog.endpoint == endpoint)
            .first()
        )

        if not rate_limit:
            return max_attempts

        # Check if window expired
        if rate_limit.window_start < window_start:
            return max_attempts

        # Check if blocked
        if rate_limit.blocked_until and rate_limit.blocked_until > now:
            return 0

        remaining = max_attempts - rate_limit.attempt_count
        return max(0, remaining)
