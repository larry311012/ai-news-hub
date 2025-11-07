"""
Authentication utilities for user authentication and session management
"""
import bcrypt
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status, Header, Request
from datetime import datetime, timedelta
from typing import Optional, Annotated, Tuple
import secrets
import logging
import hashlib

from database import User, UserSession, get_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """
    Hash a plain text password using bcrypt.

    Args:
        password: Plain text password to hash

    Returns:
        Hashed password string
    """
    # Truncate password to 72 bytes if needed (bcrypt limit)
    password_bytes = password.encode("utf-8")[:72]
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hashed password.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    # Truncate password to 72 bytes if needed (bcrypt limit)
    password_bytes = plain_password.encode("utf-8")[:72]
    return bcrypt.checkpw(password_bytes, hashed_password.encode("utf-8"))


def generate_session_token() -> str:
    """
    Generate a secure random session token.

    Returns:
        64-character hexadecimal token string
    """
    return secrets.token_hex(32)


def generate_session_fingerprint(
    request: Request = None, user_agent: str = None, ip_address: str = None
) -> str:
    """
    Generate session fingerprint from request data for session hijacking prevention

    Args:
        request: FastAPI Request object (optional)
        user_agent: User agent string (optional)
        ip_address: IP address (optional)

    Returns:
        SHA-256 hash of fingerprint data
    """
    if request:
        user_agent = request.headers.get("user-agent", "")
        ip_address = request.client.host if request.client else ""
    else:
        user_agent = user_agent or ""
        ip_address = ip_address or ""

    # Create fingerprint
    fingerprint_data = f"{user_agent}{ip_address}"
    return hashlib.sha256(fingerprint_data.encode()).hexdigest()


def validate_session_fingerprint(request: Request, stored_fingerprint: str) -> bool:
    """
    Validate session hasn't been hijacked by comparing fingerprints

    Args:
        request: Current request
        stored_fingerprint: Fingerprint stored with session

    Returns:
        True if fingerprints match, False otherwise
    """
    current_fingerprint = generate_session_fingerprint(request)
    return secrets.compare_digest(current_fingerprint, stored_fingerprint)


def create_session(
    user_id: int,
    db: Session,
    expires_days: int = 30,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
    session_fingerprint: Optional[str] = None,
    remember_me: bool = False,
) -> Tuple[str, datetime]:
    """
    Create a new session for a user and return the session token and expiration time.

    Args:
        user_id: ID of the user to create session for
        db: Database session
        expires_days: Number of days until session expires (default 30, overridden by remember_me)
        user_agent: Optional user agent string from request
        ip_address: Optional IP address from request
        session_fingerprint: Optional session fingerprint for security
        remember_me: If True, extends session to 30 days; if False, uses 1 day (default False)

    Returns:
        Tuple of (session_token, expires_at)
    """
    # Generate unique token
    token = generate_session_token()

    # Calculate expiration time based on remember_me flag
    # remember_me=True: 30 days (long session)
    # remember_me=False: 1 day (short session for security)
    if remember_me:
        expires_at = datetime.utcnow() + timedelta(days=30)
        logger.info(f"Creating extended session (30 days) for user_id={user_id}")
    else:
        expires_at = datetime.utcnow() + timedelta(days=1)
        logger.info(f"Creating standard session (1 day) for user_id={user_id}")

    # Generate fingerprint if not provided
    if session_fingerprint is None and user_agent and ip_address:
        session_fingerprint = generate_session_fingerprint(
            user_agent=user_agent, ip_address=ip_address
        )

    # Create session record
    session = UserSession(
        user_id=user_id,
        token=token,
        expires_at=expires_at,
        user_agent=user_agent[:500] if user_agent else None,  # Truncate to fit column
        ip_address=ip_address,
        session_fingerprint=session_fingerprint,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    logger.info(f"Created session for user_id={user_id}, expires_at={expires_at}")

    return token, expires_at


def get_current_user(
    token: str, db: Session, request: Request = None, validate_fingerprint: bool = True
) -> Optional[User]:
    """
    Validate a session token and return the associated user.

    Args:
        token: Session token to validate
        db: Database session
        request: Optional request object for fingerprint validation
        validate_fingerprint: Whether to validate session fingerprint

    Returns:
        User object if token is valid, None otherwise
    """
    # Find session by token
    session = db.query(UserSession).filter(UserSession.token == token).first()

    if not session:
        logger.warning(f"Session not found for token")
        return None

    # Check if session has expired
    if session.expires_at < datetime.utcnow():
        logger.warning(f"Session expired for user_id={session.user_id}")
        # Clean up expired session
        db.delete(session)
        db.commit()
        return None

    # Validate session fingerprint if enabled
    if validate_fingerprint and request and session.session_fingerprint:
        if not validate_session_fingerprint(request, session.session_fingerprint):
            logger.warning(f"Session fingerprint mismatch for user_id={session.user_id}")
            # Potential session hijacking - invalidate session
            db.delete(session)
            db.commit()
            return None

    # Get user
    user = db.query(User).filter(User.id == session.user_id).first()

    if not user:
        logger.error(f"User not found for session user_id={session.user_id}")
        return None

    # Check if user is active
    if not user.is_active:
        logger.warning(f"Inactive user attempted to use session: user_id={user.id}")
        return None

    return user


def get_current_user_dependency(
    authorization: Annotated[Optional[str], Header()] = None, db: Session = Depends(get_db)
) -> User:
    """
    FastAPI dependency for getting the current authenticated user.
    Extracts token from Authorization header (Bearer token format).

    Args:
        authorization: Authorization header value (Bearer {token})
        db: Database session

    Returns:
        User object if authenticated

    Raises:
        HTTPException: If authentication fails
    """
    # Check if Authorization header exists
    if not authorization:
        logger.warning("No authorization header provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token from Bearer format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning(f"Invalid authorization header format")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]

    # Validate token and get user (without fingerprint validation in dependency)
    user = get_current_user(token, db, validate_fingerprint=False)

    if not user:
        logger.warning(f"Invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_current_user_optional(
    authorization: Annotated[Optional[str], Header()] = None, db: Session = Depends(get_db)
) -> Optional[User]:
    """
    FastAPI dependency for getting the current user (optional).
    Returns None if not authenticated, instead of raising exception.

    Args:
        authorization: Authorization header value (Bearer {token})
        db: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    # Check if Authorization header exists
    if not authorization:
        return None

    # Extract token from Bearer format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None

    token = parts[1]

    # Validate token and get user
    user = get_current_user(token, db, validate_fingerprint=False)

    return user


def delete_session(token: str, db: Session) -> bool:
    """
    Delete a session by token (used for logout).

    Args:
        token: Session token to delete
        db: Database session

    Returns:
        True if session was deleted, False if not found
    """
    session = db.query(UserSession).filter(UserSession.token == token).first()

    if not session:
        return False

    user_id = session.user_id
    db.delete(session)
    db.commit()

    logger.info(f"Deleted session for user_id={user_id}")

    return True


def cleanup_expired_sessions(db: Session) -> int:
    """
    Clean up expired sessions from the database.
    Should be called periodically (e.g., daily cron job).

    Args:
        db: Database session

    Returns:
        Number of sessions deleted
    """
    expired_sessions = (
        db.query(UserSession).filter(UserSession.expires_at < datetime.utcnow()).all()
    )

    count = len(expired_sessions)

    for session in expired_sessions:
        db.delete(session)

    db.commit()

    logger.info(f"Cleaned up {count} expired sessions")

    return count
