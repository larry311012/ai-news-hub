"""
Phase 4: Password reset and advanced authentication endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from datetime import datetime, timedelta
import secrets
import logging

from database import get_db, User, UserSession
from utils.auth import hash_password, verify_password
from utils.password_validator import validate_password_strength
from utils.rate_limiter import RateLimiter, RateLimitExceeded
from utils.audit_logger import AuditLogger

router = APIRouter()
logger = logging.getLogger(__name__)


# Pydantic models
class ForgotPasswordRequest(BaseModel):
    """Request to initiate password reset"""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request to reset password with token"""

    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password meets requirements"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class ValidateTokenResponse(BaseModel):
    """Response for token validation"""

    valid: bool
    email: Optional[str] = None
    message: Optional[str] = None


class StandardResponse(BaseModel):
    """Standard success response"""

    success: bool
    message: str


def generate_reset_token() -> str:
    """Generate secure random reset token (32 bytes = 64 hex chars)"""
    return secrets.token_hex(32)


def send_password_reset_email(email: str, reset_token: str, db: Session):
    """
    Send password reset email to user.

    In production, this would use SendGrid or similar service.
    For now, we'll log the reset link.
    """
    # Construct reset link (in production, use actual frontend URL)
    reset_link = f"http://localhost:8080/reset-password?token={reset_token}"

    # In production, send actual email
    # For now, just log it
    logger.info(f"Password reset requested for {email}")
    logger.info(f"Reset link (for testing): {reset_link}")

    # TODO: Implement actual email sending
    # Example with SendGrid:
    # from sendgrid import SendGridAPIClient
    # from sendgrid.helpers.mail import Mail
    #
    # message = Mail(
    #     from_email='noreply@yourapp.com',
    #     to_emails=email,
    #     subject='Reset Your Password',
    #     html_content=render_template('password_reset.html', reset_link=reset_link)
    # )
    #
    # sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
    # response = sg.send(message)


@router.post("/forgot-password", response_model=StandardResponse)
async def forgot_password(
    request: ForgotPasswordRequest, http_request: Request, db: Session = Depends(get_db)
):
    """
    Request a password reset email.

    Generates a reset token and sends an email with a reset link.
    Uses generic responses to avoid revealing if email exists.
    Rate limited to 3 requests per hour per email.
    """
    try:
        # Get client IP for rate limiting
        ip_address = http_request.client.host if http_request.client else "unknown"

        # Rate limit check
        try:
            RateLimiter.check_rate_limit(
                identifier=request.email.lower(), endpoint="password_reset", db=db
            )
        except RateLimitExceeded as e:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many password reset requests. Please try again in {e.retry_after} seconds.",
            )

        # Find user by email
        user = db.query(User).filter(User.email == request.email.lower()).first()

        # Always return success to avoid email enumeration
        # But only send email if user exists
        if user and not user.is_guest:
            # Only allow password reset for users with passwords (not OAuth-only)
            if user.password_hash:
                # Generate reset token
                reset_token = generate_reset_token()

                # Set token and expiration (1 hour)
                user.reset_token = reset_token
                user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)

                db.commit()

                # Send reset email
                send_password_reset_email(user.email, reset_token, db)

                # Log security event
                AuditLogger.log_security_event(
                    "password_reset_request",
                    db,
                    user_id=user.id,
                    ip_address=ip_address,
                    details={"email": user.email},
                )

                logger.info(f"Password reset requested for user_id={user.id}")
            else:
                logger.info(f"Password reset requested for OAuth-only user: {request.email}")
        else:
            # Log potential enumeration attempt
            AuditLogger.log_security_event(
                "password_reset_request",
                db,
                ip_address=ip_address,
                details={"email": request.email, "user_exists": False},
            )
            logger.warning(f"Password reset requested for non-existent email: {request.email}")

        # Generic success message
        return StandardResponse(
            success=True,
            message="If your email is registered, you will receive a password reset link shortly.",
        )

    except RateLimitExceeded:
        raise
    except Exception as e:
        logger.error(f"Error in forgot password: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing your request",
        )


@router.get("/validate-reset-token/{token}", response_model=ValidateTokenResponse)
async def validate_reset_token(token: str, db: Session = Depends(get_db)):
    """
    Validate a password reset token.

    Checks if the token exists and hasn't expired.
    Returns user email if valid.
    """
    try:
        # Find user with this reset token
        user = db.query(User).filter(User.reset_token == token).first()

        if not user:
            return ValidateTokenResponse(valid=False, message="Invalid reset token")

        # Check if token has expired
        if not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
            return ValidateTokenResponse(
                valid=False, message="Reset token has expired. Please request a new one."
            )

        return ValidateTokenResponse(valid=True, email=user.email, message="Token is valid")

    except Exception as e:
        logger.error(f"Error validating reset token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while validating token",
        )


@router.post("/reset-password", response_model=StandardResponse)
async def reset_password(
    request: ResetPasswordRequest, http_request: Request, db: Session = Depends(get_db)
):
    """
    Reset password using a valid reset token.

    Validates the token, updates the password, invalidates all sessions,
    and clears the reset token.
    """
    try:
        # Get client IP
        ip_address = http_request.client.host if http_request.client else "unknown"
        user_agent = http_request.headers.get("User-Agent")

        # Find user with this reset token
        user = db.query(User).filter(User.reset_token == request.token).first()

        if not user:
            # Log failed attempt
            AuditLogger.log_security_event(
                "password_reset_failed",
                db,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"reason": "invalid_token"},
                risk_level="medium",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token"
            )

        # Check if token has expired
        if not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
            # Log failed attempt
            AuditLogger.log_security_event(
                "password_reset_failed",
                db,
                user_id=user.id,
                ip_address=ip_address,
                user_agent=user_agent,
                details={"reason": "expired_token"},
                risk_level="medium",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired. Please request a new one.",
            )

        # Validate new password strength
        try:
            validate_password_strength(
                request.new_password, user_email=user.email, user_name=user.full_name
            )
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        # Hash new password
        new_password_hash = hash_password(request.new_password)

        # Update password
        user.password_hash = new_password_hash
        user.password_changed_at = datetime.utcnow()

        # Clear reset token
        user.reset_token = None
        user.reset_token_expires = None

        # Invalidate all sessions for security
        sessions = db.query(UserSession).filter(UserSession.user_id == user.id).all()

        session_count = len(sessions)
        for session in sessions:
            db.delete(session)

        db.commit()

        # Log successful reset
        AuditLogger.log_security_event(
            "password_reset_success",
            db,
            user_id=user.id,
            ip_address=ip_address,
            user_agent=user_agent,
            details={"sessions_invalidated": session_count},
        )

        AuditLogger.log_login_activity(
            user_id=user.id,
            action="password_change",
            db=db,
            success=True,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        logger.info(f"Password reset successful for user_id={user.id}")

        return StandardResponse(
            success=True,
            message=f"Password reset successful. All {session_count} session(s) have been logged out for security.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while resetting password",
        )


@router.post("/change-password-strength", response_model=dict)
async def check_password_strength(
    password: str, email: Optional[str] = None, full_name: Optional[str] = None
):
    """
    Check password strength without saving.

    Useful for client-side validation feedback.
    """
    try:
        from utils.password_validator import check_password_strength as check_strength

        result = check_strength(password, email, full_name)

        return {"success": True, **result}

    except Exception as e:
        logger.error(f"Error checking password strength: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while checking password strength",
        )
