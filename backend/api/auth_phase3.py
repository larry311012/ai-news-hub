"""
Phase 3 Authentication endpoints: Email Verification & Guest Mode
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import secrets
import logging
import uuid

from database import get_db, User, UserSession
from utils.auth import create_session, get_current_user_dependency, hash_password
from utils.email import send_verification_email, send_welcome_email
from api.auth import LoginResponse, UserResponse, StandardResponse

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting storage (in production, use Redis)
verification_attempts = {}


class SendVerificationRequest(BaseModel):
    """Request model for sending verification email"""

    email: Optional[EmailStr] = None  # If provided, update email first


class ResendVerificationRequest(BaseModel):
    """Request model for resending verification email"""

    email: EmailStr


class ConvertGuestRequest(BaseModel):
    """Request model for converting guest to full user"""

    email: EmailStr
    password: str
    full_name: str

    def validate_password(self) -> str:
        """Validate password meets minimum requirements"""
        if len(self.password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return self.password

    def validate_full_name(self) -> str:
        """Validate full name is not empty"""
        if not self.full_name or not self.full_name.strip():
            raise ValueError("Full name cannot be empty")
        return self.full_name.strip()


class GuestLimitations(BaseModel):
    """Response model for guest limitations"""

    is_guest: bool
    limitations: List[str]
    restricted_endpoints: List[str]


def generate_verification_token() -> str:
    """Generate secure verification token"""
    return secrets.token_urlsafe(32)


def check_rate_limit(identifier: str, max_attempts: int = 3, window_minutes: int = 60) -> bool:
    """
    Check if user has exceeded rate limit for verification emails.

    Args:
        identifier: User email or ID
        max_attempts: Maximum attempts allowed
        window_minutes: Time window in minutes

    Returns:
        True if within rate limit, False if exceeded
    """
    current_time = datetime.utcnow()

    # Clean up old entries
    expired_keys = [
        key
        for key, data in verification_attempts.items()
        if (current_time - data["window_start"]).total_seconds() > (window_minutes * 60)
    ]
    for key in expired_keys:
        del verification_attempts[key]

    # Check current attempts
    if identifier in verification_attempts:
        data = verification_attempts[identifier]
        if data["count"] >= max_attempts:
            logger.warning(f"Rate limit exceeded for {identifier}")
            return False

        # Increment count
        data["count"] += 1
        data["last_attempt"] = current_time
    else:
        # First attempt
        verification_attempts[identifier] = {
            "count": 1,
            "window_start": current_time,
            "last_attempt": current_time,
        }

    return True


@router.post("/send-verification", response_model=StandardResponse)
async def send_verification(
    request: SendVerificationRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Send email verification link to user.

    If user is already verified, returns success without sending.
    Supports optional email update before sending verification.

    Args:
        request: Optional new email address
        user: Current authenticated user
        db: Database session

    Returns:
        Success response
    """
    try:
        # Check if already verified
        if user.is_verified:
            return StandardResponse(success=True, message="Email is already verified")

        # Check rate limit
        if not check_rate_limit(f"verify_{user.id}", max_attempts=3, window_minutes=60):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many verification emails sent. Please try again in an hour.",
            )

        # Update email if provided
        if request.email and request.email.lower() != user.email:
            # Check if new email is already taken
            existing_user = (
                db.query(User)
                .filter(User.email == request.email.lower(), User.id != user.id)
                .first()
            )

            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This email is already in use by another account",
                )

            user.email = request.email.lower()
            user.is_verified = False  # Reset verification status

        # Generate verification token
        token = generate_verification_token()
        user.verification_token = token
        user.verification_token_expires = datetime.utcnow() + timedelta(hours=24)
        user.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(user)

        # Send verification email
        send_verification_email(user, token)

        logger.info(f"Verification email sent to user_id={user.id}")

        return StandardResponse(
            success=True, message="Verification email sent. Please check your inbox."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error sending verification email: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while sending verification email",
        )


@router.get("/verify-email/{token}", response_model=StandardResponse)
async def verify_email(token: str, db: Session = Depends(get_db)):
    """
    Verify email address using token from email.

    Args:
        token: Verification token from email link
        db: Database session

    Returns:
        Success response with redirect info
    """
    try:
        # Find user by verification token
        user = db.query(User).filter(User.verification_token == token).first()

        if not user:
            logger.warning(f"Invalid verification token")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification token",
            )

        # Check if token has expired
        if user.verification_token_expires < datetime.utcnow():
            logger.warning(f"Expired verification token for user_id={user.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification token has expired. Please request a new one.",
            )

        # Verify user
        user.is_verified = True
        user.verification_token = None
        user.verification_token_expires = None
        user.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(user)

        # Send welcome email
        send_welcome_email(user)

        logger.info(f"Email verified for user_id={user.id}")

        return StandardResponse(
            success=True, message="Email verified successfully! You can now access all features."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying email: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while verifying email",
        )


@router.post("/resend-verification", response_model=StandardResponse)
async def resend_verification(request: ResendVerificationRequest, db: Session = Depends(get_db)):
    """
    Resend verification email to unverified user.

    This endpoint doesn't require authentication to help users
    who lost their verification email.

    Args:
        request: Email address to send verification to
        db: Database session

    Returns:
        Success response (always returns success to avoid email enumeration)
    """
    try:
        # Find user by email
        user = db.query(User).filter(User.email == request.email.lower()).first()

        # Always return success to avoid email enumeration
        if not user:
            logger.warning(f"Resend verification requested for non-existent email")
            return StandardResponse(
                success=True,
                message="If this email is registered, a verification link has been sent.",
            )

        # Check if already verified
        if user.is_verified:
            return StandardResponse(
                success=True,
                message="If this email is registered, a verification link has been sent.",
            )

        # Check rate limit
        if not check_rate_limit(
            f"resend_{request.email.lower()}", max_attempts=3, window_minutes=60
        ):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many verification emails sent. Please try again in an hour.",
            )

        # Generate new token
        token = generate_verification_token()
        user.verification_token = token
        user.verification_token_expires = datetime.utcnow() + timedelta(hours=24)
        user.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(user)

        # Send verification email
        send_verification_email(user, token)

        logger.info(f"Verification email resent to user_id={user.id}")

        return StandardResponse(
            success=True, message="If this email is registered, a verification link has been sent."
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resending verification email: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while sending verification email",
        )


@router.post("/guest", response_model=LoginResponse)
async def create_guest_account(request: Request, db: Session = Depends(get_db)):
    """
    Create a guest account for anonymous users.

    Guest accounts have limited features and can be converted
    to full accounts later.

    Args:
        request: FastAPI request object
        db: Database session

    Returns:
        LoginResponse with guest user token
    """
    try:
        # Generate unique guest email
        guest_uuid = str(uuid.uuid4())
        guest_email = f"guest_{guest_uuid}@temp.local"
        guest_name = f"Guest_{guest_uuid[:8]}"

        # Create guest user
        user = User(
            email=guest_email,
            password_hash=None,  # No password for guests
            full_name=guest_name,
            is_active=True,
            is_verified=False,
            is_guest=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        # Get user agent and IP for session tracking
        user_agent = request.headers.get("user-agent")
        ip_address = request.client.host if request.client else None

        # Create session (7 days for guests)
        token, expires_at = create_session(
            user_id=user.id, db=db, expires_days=7, user_agent=user_agent, ip_address=ip_address
        )

        logger.info(f"Guest account created: user_id={user.id}, email={guest_email}")

        return LoginResponse(
            success=True,
            token=token,
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                bio=user.bio,
                created_at=user.created_at,
                is_verified=user.is_verified,
            ),
            expires_at=expires_at,
        )

    except Exception as e:
        logger.error(f"Error creating guest account: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating guest account",
        )


@router.post("/guest/convert", response_model=LoginResponse)
async def convert_guest_to_user(
    request: ConvertGuestRequest,
    user: User = Depends(get_current_user_dependency),
    http_request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Convert guest account to full user account.

    Args:
        request: Email, password, and full name for new account
        user: Current guest user
        http_request: FastAPI request object
        db: Database session

    Returns:
        LoginResponse with updated user data
    """
    try:
        # Validate user is a guest
        if not user.is_guest:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This account is not a guest account",
            )

        # Validate password and full name
        try:
            request.validate_password()
            request.validate_full_name()
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        # Check if email is already taken
        existing_user = (
            db.query(User).filter(User.email == request.email.lower(), User.id != user.id).first()
        )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="This email is already registered"
            )

        # Convert guest to full user
        user.email = request.email.lower()
        user.password_hash = hash_password(request.password)
        user.full_name = request.full_name
        user.is_guest = False
        user.is_verified = False  # Will need to verify email
        user.updated_at = datetime.utcnow()

        # Generate verification token
        token = generate_verification_token()
        user.verification_token = token
        user.verification_token_expires = datetime.utcnow() + timedelta(hours=24)

        db.commit()
        db.refresh(user)

        # Send verification email
        send_verification_email(user, token)

        # Get user agent and IP
        user_agent = http_request.headers.get("user-agent") if http_request else None
        ip_address = http_request.client.host if http_request and http_request.client else None

        # Create new session (30 days for full users)
        new_token, expires_at = create_session(
            user_id=user.id, db=db, expires_days=30, user_agent=user_agent, ip_address=ip_address
        )

        logger.info(f"Guest converted to full user: user_id={user.id}, email={user.email}")

        return LoginResponse(
            success=True,
            token=new_token,
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                bio=user.bio,
                created_at=user.created_at,
                is_verified=user.is_verified,
            ),
            expires_at=expires_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error converting guest account: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while converting guest account",
        )


@router.get("/guest/limitations", response_model=GuestLimitations)
async def get_guest_limitations(user: User = Depends(get_current_user_dependency)):
    """
    Get list of features and endpoints restricted for guest users.

    Args:
        user: Current authenticated user

    Returns:
        Guest limitations information
    """
    limitations = [
        "Cannot save API keys permanently",
        "Limited session duration (7 days instead of 30)",
        "Cannot connect social media accounts",
        "Limited post generation quota",
        "No email notifications",
    ]

    restricted_endpoints = [
        "POST /api/auth/api-keys",
        "GET /api/auth/api-keys",
        "DELETE /api/auth/api-keys/{provider}",
        "POST /api/posts/publish",
        "POST /api/settings/social-accounts",
    ]

    return GuestLimitations(
        is_guest=user.is_guest,
        limitations=limitations if user.is_guest else [],
        restricted_endpoints=restricted_endpoints if user.is_guest else [],
    )


def require_full_user(user: User = Depends(get_current_user_dependency)) -> User:
    """
    Dependency to ensure user is not a guest.

    Args:
        user: Current authenticated user

    Returns:
        User object if not guest

    Raises:
        HTTPException: If user is a guest
    """
    if user.is_guest:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This feature requires a full account. Please create an account to continue.",
        )
    return user
