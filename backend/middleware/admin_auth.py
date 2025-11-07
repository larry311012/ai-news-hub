"""
Admin Authorization Middleware

This module provides middleware and dependencies for admin-only endpoints.
Only users with is_admin=true can access admin-protected routes.

Usage:
    from middleware.admin_auth import require_admin

    @router.get("/admin/some-endpoint")
    async def admin_endpoint(admin_user: User = Depends(require_admin)):
        # Only admins can reach this code
        return {"message": "Admin access granted"}
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db, User
from utils.auth import get_current_user_dependency


async def require_admin(
    current_user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
) -> User:
    """
    Dependency to require admin privileges.

    This checks if the current user has admin privileges. If not,
    it raises a 403 Forbidden exception.

    Args:
        current_user: Current authenticated user
        db: Database session

    Returns:
        User object if user is admin

    Raises:
        HTTPException: 403 if user is not admin
    """
    # Check if user has is_admin field (we need to add this to User model)
    # For now, we'll use a simple check - you can expand this based on your needs

    # Option 1: Check if user has an is_admin column
    if hasattr(current_user, "is_admin") and current_user.is_admin:
        return current_user

    # Option 2: Check if user email is in admin list (temporary solution)
    # You can configure this via environment variable
    import os

    admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
    admin_emails = [email.strip() for email in admin_emails if email.strip()]

    if current_user.email in admin_emails:
        return current_user

    # Option 3: Check if user has specific role in metadata
    # This could be stored in a separate roles table or in user metadata

    # If none of the above, user is not admin
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin privileges required. You do not have permission to access this resource.",
    )


async def is_user_admin(user: User) -> bool:
    """
    Check if a user has admin privileges.

    Args:
        user: User object to check

    Returns:
        True if user is admin, False otherwise
    """
    # Check is_admin field
    if hasattr(user, "is_admin") and user.is_admin:
        return True

    # Check admin emails list
    import os

    admin_emails = os.getenv("ADMIN_EMAILS", "").split(",")
    admin_emails = [email.strip() for email in admin_emails if email.strip()]

    if user.email in admin_emails:
        return True

    return False


def get_admin_user_id(current_user: User = Depends(require_admin)) -> int:
    """
    Dependency to get admin user ID.

    Useful for audit trail when creating/updating records.

    Args:
        current_user: Current admin user

    Returns:
        User ID of admin user
    """
    return current_user.id
