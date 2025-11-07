"""
Mobile API v1 Endpoints (Task 1.6)

iOS-optimized API endpoints with:
- Token refresh
- Device registration
- iOS OAuth redirect support
- Response optimization
- Mobile-specific validation
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, timedelta
import secrets
import logging
from user_agents import parse

from database import get_db, User, UserSession
from utils.auth_selector import get_current_user as get_current_user_dependency, create_session
from utils.error_responses import (
    ErrorCode,
    create_error_response,
    create_error_exception
)
from middleware.rate_limiting import limiter

logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Mobile Request/Response Models
# ============================================================================


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh"""
    refresh_token: str = Field(..., min_length=32, max_length=128)
    device_id: Optional[str] = Field(None, max_length=128)


class RefreshTokenResponse(BaseModel):
    """Response model for token refresh"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int  # seconds
    expires_at: str  # ISO 8601 timestamp


class DeviceRegistrationRequest(BaseModel):
    """Request model for device registration"""
    device_id: str = Field(..., min_length=10, max_length=128)
    device_type: str = Field(..., pattern="^(ios|android)$")
    device_name: Optional[str] = Field(None, max_length=255)
    os_version: Optional[str] = Field(None, max_length=50)
    app_version: str = Field(..., max_length=50)
    push_token: Optional[str] = Field(None, max_length=500)

    @field_validator("device_id")
    @classmethod
    def validate_device_id(cls, v: str) -> str:
        """Validate device ID format"""
        if not v or not v.strip():
            raise ValueError("Device ID cannot be empty")
        return v.strip()


class DeviceRegistrationResponse(BaseModel):
    """Response model for device registration"""
    device_id: str
    registered_at: str
    message: str = "Device registered successfully"


class MobileSessionInfo(BaseModel):
    """Mobile-optimized session info"""
    session_id: str
    expires_at: str
    device_info: dict
    last_activity: str


# ============================================================================
# Mobile Device Model (Database)
# ============================================================================


# Note: This would be added to database.py in production
# For now, we'll use the sessions table with extended metadata


# ============================================================================
# Token Refresh Endpoint (Task 1.6 - Critical)
# ============================================================================


@router.post("/v1/auth/refresh", response_model=RefreshTokenResponse)
@limiter.limit("10/minute")  # Rate limit: 10 requests per minute per user
async def refresh_access_token(
    request: Request,
    refresh_request: RefreshTokenRequest,
    db: Session = Depends(get_db),
    user_agent: Optional[str] = Header(None),
    app_version: Optional[str] = Header(None, alias="X-App-Version")
):
    """
    Refresh access token using refresh token.

    **iOS Integration:**
    ```swift
    let request = RefreshTokenRequest(
        refresh_token: storedRefreshToken,
        device_id: UIDevice.current.identifierForVendor?.uuidString
    )

    let response = await api.post("/api/v1/auth/refresh", body: request)
    // Store new access_token
    KeychainManager.shared.saveAccessToken(response.access_token)
    ```

    **Rate Limit:** 10 requests per minute per device

    **Security:**
    - Validates refresh token hasn't expired
    - Checks device ID if provided
    - Creates new session with shorter expiration
    - Logs refresh for security audit

    Args:
        request: FastAPI request object
        refresh_request: Refresh token data
        db: Database session
        user_agent: User agent string
        app_version: App version from header

    Returns:
        New access token with expiration info

    Raises:
        401: If refresh token is invalid or expired
        429: If rate limit exceeded
    """
    try:
        # Validate refresh token
        session = db.query(UserSession).filter(
            UserSession.token == refresh_request.refresh_token,
            UserSession.expires_at > datetime.utcnow()
        ).first()

        if not session:
            logger.warning(
                f"Invalid or expired refresh token from IP: {request.client.host}"
            )
            raise create_error_exception(
                code=ErrorCode.AUTH_TOKEN_EXPIRED,
                message="Refresh token is invalid or expired",
                status_code=status.HTTP_401_UNAUTHORIZED,
                details={"reason": "token_not_found_or_expired"}
            )

        # Get user
        user = db.query(User).filter(User.id == session.user_id).first()
        if not user or not user.is_active:
            logger.warning(f"Refresh token used for inactive user: {session.user_id}")
            raise create_error_exception(
                code=ErrorCode.AUTH_USER_INACTIVE,
                message="User account is inactive",
                status_code=status.HTTP_403_FORBIDDEN
            )

        # Validate device ID if provided (optional security check)
        if refresh_request.device_id:
            stored_device_id = session.session_fingerprint
            if stored_device_id and stored_device_id != refresh_request.device_id:
                logger.warning(
                    f"Device ID mismatch for user {user.id}: "
                    f"expected {stored_device_id}, got {refresh_request.device_id}"
                )
                # Note: We log but don't block - device IDs can change

        # Create new access token (shorter expiration for mobile)
        # Mobile apps use refresh tokens, so access tokens can be short-lived
        new_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=2)  # 2 hour access token

        # Update existing session with new token
        session.token = new_token
        session.expires_at = expires_at
        session.last_activity = datetime.utcnow()
        session.user_agent = user_agent or session.user_agent
        db.commit()

        logger.info(
            f"Access token refreshed for user {user.id} from device {refresh_request.device_id}"
        )

        # Calculate expires_in (seconds from now)
        expires_in = int((expires_at - datetime.utcnow()).total_seconds())

        return RefreshTokenResponse(
            access_token=new_token,
            token_type="Bearer",
            expires_in=expires_in,
            expires_at=expires_at.isoformat() + "Z"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing token: {str(e)}")
        raise create_error_exception(
            code=ErrorCode.AUTH_REFRESH_FAILED,
            message="Failed to refresh access token",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# Device Registration Endpoint (Task 1.6)
# ============================================================================


@router.post("/v1/devices", response_model=DeviceRegistrationResponse)
@limiter.limit("5/hour")  # Rate limit: 5 registrations per hour
async def register_device(
    request: Request,
    device_req: DeviceRegistrationRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Register mobile device for push notifications and tracking.

    **iOS Integration:**
    ```swift
    let deviceInfo = DeviceRegistrationRequest(
        device_id: UIDevice.current.identifierForVendor?.uuidString ?? "",
        device_type: "ios",
        device_name: UIDevice.current.name,
        os_version: UIDevice.current.systemVersion,
        app_version: Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "1.0",
        push_token: deviceToken // From APNs
    )

    let response = await api.post("/api/v1/devices", body: deviceInfo)
    ```

    **Purpose:**
    - Register device for future push notifications
    - Track active devices per user
    - Enable device-specific rate limiting
    - Collect analytics on device types/versions

    Args:
        request: FastAPI request object
        device_req: Device registration data
        user: Current authenticated user
        db: Database session

    Returns:
        Device registration confirmation

    Raises:
        400: If device data is invalid
        429: If rate limit exceeded
    """
    try:
        # Find or create session for this device
        session = db.query(UserSession).filter(
            UserSession.user_id == user.id,
            UserSession.session_fingerprint == device_req.device_id
        ).first()

        if session:
            # Update existing device registration
            session.last_activity = datetime.utcnow()
            session.user_agent = f"{device_req.device_type}/{device_req.os_version} ({device_req.app_version})"
            logger.info(f"Updated device registration for user {user.id}: {device_req.device_id}")
        else:
            # Create new device session (for tracking)
            # Note: In production, you'd have a separate devices table
            new_session = UserSession(
                user_id=user.id,
                token=secrets.token_urlsafe(32),
                expires_at=datetime.utcnow() + timedelta(days=90),  # Long-lived for device
                session_fingerprint=device_req.device_id,
                user_agent=f"{device_req.device_type}/{device_req.os_version} ({device_req.app_version})",
                ip_address=request.client.host if request.client else None,
                last_activity=datetime.utcnow()
            )
            db.add(new_session)
            logger.info(f"New device registered for user {user.id}: {device_req.device_id}")

        db.commit()

        # TODO: Store push_token for future push notification support
        # This would go into a separate push_tokens table

        return DeviceRegistrationResponse(
            device_id=device_req.device_id,
            registered_at=datetime.utcnow().isoformat() + "Z",
            message=f"{device_req.device_type.upper()} device registered successfully"
        )

    except Exception as e:
        logger.error(f"Error registering device for user {user.id}: {str(e)}")
        db.rollback()
        raise create_error_exception(
            code=ErrorCode.VALIDATION_INVALID_INPUT,
            message="Failed to register device",
            status_code=status.HTTP_400_BAD_REQUEST,
            details={"error": str(e)}
        )


# ============================================================================
# Mobile Session Info Endpoint
# ============================================================================


@router.get("/v1/sessions/current", response_model=MobileSessionInfo)
@limiter.limit("30/minute")
async def get_current_session_info(
    request: Request,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Get current session information for mobile app.

    Returns session details including expiration and device info.
    Useful for displaying session status in app settings.

    Args:
        request: FastAPI request object
        user: Current authenticated user
        db: Database session

    Returns:
        Current session information
    """
    try:
        # Extract token from header
        authorization = request.headers.get("authorization", "")
        token = authorization.replace("Bearer ", "") if authorization else None

        if not token:
            raise create_error_exception(
                code=ErrorCode.AUTH_TOKEN_MISSING,
                message="Authorization token missing",
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        # Get session
        session = db.query(UserSession).filter(
            UserSession.user_id == user.id,
            UserSession.token == token
        ).first()

        if not session:
            raise create_error_exception(
                code=ErrorCode.AUTH_TOKEN_INVALID,
                message="Session not found",
                status_code=status.HTTP_401_UNAUTHORIZED
            )

        # Parse user agent
        ua = parse(session.user_agent or "")

        return MobileSessionInfo(
            session_id=str(session.id),
            expires_at=session.expires_at.isoformat() + "Z",
            device_info={
                "device_id": session.session_fingerprint or "unknown",
                "os": f"{ua.os.family} {ua.os.version_string}",
                "browser": f"{ua.browser.family} {ua.browser.version_string}",
                "is_mobile": ua.is_mobile,
                "ip_address": session.ip_address or "unknown"
            },
            last_activity=session.last_activity.isoformat() + "Z" if session.last_activity else datetime.utcnow().isoformat() + "Z"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting session info for user {user.id}: {str(e)}")
        raise create_error_exception(
            code=ErrorCode.SERVER_INTERNAL_ERROR,
            message="Failed to retrieve session info",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ============================================================================
# Mobile-Optimized User Info Endpoint
# ============================================================================


@router.get("/v1/user/me")
@limiter.limit("60/minute")
async def get_mobile_user_info(
    request: Request,
    user: User = Depends(get_current_user_dependency)
):
    """
    Get current user information (mobile-optimized).

    Returns only essential user data to minimize payload size.
    Optimized for mobile network conditions.

    Args:
        request: FastAPI request object
        user: Current authenticated user

    Returns:
        Compact user information
    """
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "is_verified": user.is_verified,
        "user_tier": user.user_tier,
        "created_at": user.created_at.isoformat() + "Z" if user.created_at else None
    }
