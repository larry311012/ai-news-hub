"""
Anonymous authentication module - always returns user_id=1
For single-user deployments without login
"""
import os
from sqlalchemy.orm import Session
from fastapi import Depends
from database import User, get_db
import logging

logger = logging.getLogger(__name__)

# Read ANONYMOUS_MODE from environment
ANONYMOUS_MODE_ENABLED = os.getenv("ANONYMOUS_MODE", "false").lower() == "true"


def get_anonymous_user(db: Session = Depends(get_db)) -> User:
    """
    Always return the anonymous user (id=1).
    Creates the anonymous user if it doesn't exist.

    This bypasses all authentication and always returns user_id=1.
    Use only in single-user deployments.

    Args:
        db: Database session

    Returns:
        User object with id=1 (anonymous user)
    """
    # Find or create anonymous user
    user = db.query(User).filter(User.id == 1).first()

    if not user:
        logger.warning("Anonymous user not found, creating now...")
        # Create anonymous user
        user = User(
            id=1,
            email="anonymous@localhost",
            full_name="Anonymous User",
            password_hash=None,  # No password required
            is_active=True,
            is_verified=True,
            is_admin=True,  # Grant admin privileges for full access
            user_tier="free",  # Default tier
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Created anonymous user (id=1) for ANONYMOUS_MODE")

    return user


# Export the dependency function
get_current_user_anonymous = get_anonymous_user
