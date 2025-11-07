"""
Phase 4: Security dashboard and session management endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from user_agents import parse
import logging

from database import get_db, User, UserSession, UserSecuritySettings, LoginActivity, SecurityAudit
from utils.auth_selector import get_current_user as get_current_user_dependency
from utils.security_monitor import SecurityMonitor
from utils.audit_logger import AuditLogger

router = APIRouter()
logger = logging.getLogger(__name__)


# Pydantic models
class SessionInfo(BaseModel):
    """Session information with metadata"""

    id: int
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    ip_address: Optional[str]
    device_type: str
    device_name: str
    browser: str
    location: str
    is_current: bool

    class Config:
        from_attributes = True


class LoginActivityResponse(BaseModel):
    """Login activity entry"""

    id: int
    action: str
    success: bool
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SecurityScoreResponse(BaseModel):
    """Security score calculation"""

    score: int
    max_score: int
    level: str  # weak, fair, good, strong
    factors: dict
    recommendations: List[str]


class SecuritySettingsResponse(BaseModel):
    """Security settings"""

    notify_new_login: bool
    notify_password_change: bool
    notify_api_key_change: bool
    session_timeout_days: int

    class Config:
        from_attributes = True


class UpdateSecuritySettingsRequest(BaseModel):
    """Request to update security settings"""

    notify_new_login: Optional[bool] = None
    notify_password_change: Optional[bool] = None
    notify_api_key_change: Optional[bool] = None
    session_timeout_days: Optional[int] = None


class RevokeSessionRequest(BaseModel):
    """Request to revoke a specific session"""

    session_id: int


def parse_user_agent(user_agent_string: Optional[str]) -> dict:
    """Parse user agent string to extract device info"""
    if not user_agent_string:
        return {
            "device_type": "Unknown",
            "device_name": "Unknown Device",
            "browser": "Unknown Browser",
        }

    try:
        ua = parse(user_agent_string)

        # Determine device type
        if ua.is_mobile:
            device_type = "Mobile"
        elif ua.is_tablet:
            device_type = "Tablet"
        elif ua.is_pc:
            device_type = "Desktop"
        else:
            device_type = "Unknown"

        # Get device name
        device_name = ua.device.family
        if device_name == "Other":
            device_name = f"{ua.os.family}"

        # Get browser
        browser = f"{ua.browser.family}"
        if ua.browser.version_string:
            browser += f" {ua.browser.version_string}"

        return {"device_type": device_type, "device_name": device_name, "browser": browser}
    except Exception as e:
        logger.warning(f"Error parsing user agent: {str(e)}")
        return {
            "device_type": "Unknown",
            "device_name": "Unknown Device",
            "browser": "Unknown Browser",
        }


@router.get("/sessions", response_model=List[SessionInfo])
async def list_sessions(
    request: Request,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    List all active sessions for the current user.

    Returns detailed information about each session including device info,
    location, and activity timestamps.
    """
    try:
        # Get current token to identify current session
        auth_header = request.headers.get("Authorization", "")
        current_token = auth_header.split()[1] if len(auth_header.split()) == 2 else None

        # Get all active sessions
        sessions = (
            db.query(UserSession)
            .filter(UserSession.user_id == user.id, UserSession.expires_at > datetime.utcnow())
            .order_by(UserSession.last_activity.desc())
            .all()
        )

        session_list = []
        for session in sessions:
            # Parse user agent
            device_info = parse_user_agent(session.user_agent)

            # Create session info
            session_info = SessionInfo(
                id=session.id,
                created_at=session.created_at,
                last_activity=session.last_activity,
                expires_at=session.expires_at,
                ip_address=session.ip_address,
                device_type=device_info["device_type"],
                device_name=device_info["device_name"],
                browser=device_info["browser"],
                location=session.ip_address or "Unknown",  # Could be enhanced with GeoIP
                is_current=(session.token == current_token),
            )
            session_list.append(session_info)

        return session_list

    except Exception as e:
        logger.error(f"Error listing sessions for user_id={user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving sessions",
        )


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: int,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Revoke a specific session.

    The session will be deleted and the associated token will become invalid.
    """
    try:
        # Find session
        session = (
            db.query(UserSession)
            .filter(UserSession.id == session_id, UserSession.user_id == user.id)
            .first()
        )

        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

        # Delete session
        db.delete(session)
        db.commit()

        # Log activity
        AuditLogger.log_security_event(
            "session_revoked",
            db,
            user_id=user.id,
            details={"session_id": session_id},
            risk_level="low",
        )

        logger.info(f"Session {session_id} revoked by user_id={user.id}")

        return {"success": True, "message": "Session revoked successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking session for user_id={user.id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while revoking session",
        )


@router.post("/sessions/revoke-all")
async def revoke_all_sessions(
    request: Request,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Revoke all other sessions except the current one.

    This is useful for security purposes if you suspect unauthorized access.
    """
    try:
        # Get current token
        auth_header = request.headers.get("Authorization", "")
        current_token = auth_header.split()[1] if len(auth_header.split()) == 2 else None

        # Delete all sessions except current
        sessions_to_delete = (
            db.query(UserSession)
            .filter(
                UserSession.user_id == user.id,
                UserSession.token != current_token if current_token else True,
            )
            .all()
        )

        count = len(sessions_to_delete)
        for session in sessions_to_delete:
            db.delete(session)

        db.commit()

        # Log activity
        AuditLogger.log_security_event(
            "all_sessions_revoked",
            db,
            user_id=user.id,
            details={"sessions_revoked": count},
            risk_level="medium",
        )

        logger.info(f"All sessions revoked by user_id={user.id}, count={count}")

        return {
            "success": True,
            "message": f"Successfully revoked {count} other session(s)",
            "revoked_count": count,
        }

    except Exception as e:
        logger.error(f"Error revoking all sessions for user_id={user.id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while revoking sessions",
        )


@router.get("/activity", response_model=List[LoginActivityResponse])
async def get_login_activity(
    limit: int = 50,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Get recent login activity for the current user.

    Returns up to 'limit' most recent activities including logins, logouts,
    password changes, and other security-relevant actions.
    """
    try:
        activities = (
            db.query(LoginActivity)
            .filter(LoginActivity.user_id == user.id)
            .order_by(LoginActivity.created_at.desc())
            .limit(limit)
            .all()
        )

        return [
            LoginActivityResponse(
                id=activity.id,
                action=activity.action,
                success=activity.success,
                ip_address=activity.ip_address,
                user_agent=activity.user_agent,
                created_at=activity.created_at,
            )
            for activity in activities
        ]

    except Exception as e:
        logger.error(f"Error getting activity for user_id={user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving activity",
        )


@router.get("/score", response_model=SecurityScoreResponse)
async def get_security_score(
    user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
):
    """
    Calculate and return the user's security score.

    The score is based on various factors including email verification,
    password strength, 2FA status, OAuth linking, and recent password changes.
    """
    try:
        score = 0
        max_score = 100
        factors = {}
        recommendations = []

        # Email verified (+30 points)
        if user.is_verified:
            factors["email_verified"] = 30
            score += 30
        else:
            factors["email_verified"] = 0
            recommendations.append("Verify your email address")

        # Password strength (+20 points) - Check if password was recently changed
        if user.password_changed_at:
            days_since_change = (datetime.utcnow() - user.password_changed_at).days
            if days_since_change <= 90:
                factors["recent_password_change"] = 20
                score += 20
            else:
                factors["recent_password_change"] = 10
                score += 10
                recommendations.append(
                    "Consider changing your password (last changed over 90 days ago)"
                )
        elif user.password_hash:
            # Has password but no change date (legacy)
            factors["recent_password_change"] = 10
            score += 10
            recommendations.append("Consider changing your password regularly")
        else:
            factors["recent_password_change"] = 0
            recommendations.append("Set up a strong password")

        # OAuth linked (+10 points)
        if user.oauth_provider:
            factors["oauth_linked"] = 10
            score += 10
        else:
            factors["oauth_linked"] = 0
            recommendations.append("Link your account with OAuth for additional security")

        # Active sessions management (+15 points)
        active_sessions = (
            db.query(UserSession)
            .filter(UserSession.user_id == user.id, UserSession.expires_at > datetime.utcnow())
            .count()
        )

        if active_sessions <= 3:
            factors["session_management"] = 15
            score += 15
        elif active_sessions <= 5:
            factors["session_management"] = 10
            score += 10
            recommendations.append(
                "You have multiple active sessions, consider revoking unused ones"
            )
        else:
            factors["session_management"] = 5
            score += 5
            recommendations.append("You have many active sessions, review and revoke unused ones")

        # No recent security incidents (+15 points)
        recent_incidents = (
            db.query(SecurityAudit)
            .filter(
                SecurityAudit.user_id == user.id,
                SecurityAudit.risk_level == "high",
                SecurityAudit.created_at >= datetime.utcnow() - timedelta(days=30),
            )
            .count()
        )

        if recent_incidents == 0:
            factors["no_incidents"] = 15
            score += 15
        else:
            factors["no_incidents"] = 0
            recommendations.append(
                f"Review {recent_incidents} high-risk security incident(s) from the last 30 days"
            )

        # API keys encrypted (+10 points)
        # Always give points since all API keys are encrypted in this system
        factors["api_keys_encrypted"] = 10
        score += 10

        # Determine level
        if score >= 80:
            level = "strong"
        elif score >= 60:
            level = "good"
        elif score >= 40:
            level = "fair"
        else:
            level = "weak"

        return SecurityScoreResponse(
            score=score,
            max_score=max_score,
            level=level,
            factors=factors,
            recommendations=recommendations,
        )

    except Exception as e:
        logger.error(f"Error calculating security score for user_id={user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while calculating security score",
        )


@router.get("/settings", response_model=SecuritySettingsResponse)
async def get_security_settings(
    user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
):
    """
    Get current security settings for the user.

    Returns notification preferences and session timeout settings.
    """
    try:
        # Get or create security settings
        settings = (
            db.query(UserSecuritySettings).filter(UserSecuritySettings.user_id == user.id).first()
        )

        if not settings:
            # Create default settings
            settings = UserSecuritySettings(user_id=user.id)
            db.add(settings)
            db.commit()
            db.refresh(settings)

        return SecuritySettingsResponse(
            notify_new_login=settings.notify_new_login,
            notify_password_change=settings.notify_password_change,
            notify_api_key_change=settings.notify_api_key_change,
            session_timeout_days=settings.session_timeout_days,
        )

    except Exception as e:
        logger.error(f"Error getting security settings for user_id={user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving security settings",
        )


@router.patch("/settings", response_model=SecuritySettingsResponse)
async def update_security_settings(
    request: UpdateSecuritySettingsRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Update security settings for the user.

    Allows changing notification preferences and session timeout.
    """
    try:
        # Get or create security settings
        settings = (
            db.query(UserSecuritySettings).filter(UserSecuritySettings.user_id == user.id).first()
        )

        if not settings:
            settings = UserSecuritySettings(user_id=user.id)
            db.add(settings)

        # Update settings
        if request.notify_new_login is not None:
            settings.notify_new_login = request.notify_new_login

        if request.notify_password_change is not None:
            settings.notify_password_change = request.notify_password_change

        if request.notify_api_key_change is not None:
            settings.notify_api_key_change = request.notify_api_key_change

        if request.session_timeout_days is not None:
            # Validate session timeout (7-90 days)
            if not 7 <= request.session_timeout_days <= 90:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Session timeout must be between 7 and 90 days",
                )
            settings.session_timeout_days = request.session_timeout_days

        settings.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(settings)

        # Log activity
        AuditLogger.log_security_event(
            "security_settings_changed",
            db,
            user_id=user.id,
            details={"changes": request.dict(exclude_none=True)},
            risk_level="low",
        )

        logger.info(f"Security settings updated for user_id={user.id}")

        return SecuritySettingsResponse(
            notify_new_login=settings.notify_new_login,
            notify_password_change=settings.notify_password_change,
            notify_api_key_change=settings.notify_api_key_change,
            session_timeout_days=settings.session_timeout_days,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating security settings for user_id={user.id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating security settings",
        )


@router.get("/threats")
async def check_threats(
    request: Request,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Check for security threats for the current user.

    Analyzes recent activity patterns and returns potential security concerns.
    """
    try:
        # Get client IP
        ip_address = request.client.host if request.client else "unknown"

        # Check for threats
        threat_analysis = SecurityMonitor.check_for_threats(
            user_id=user.id, ip_address=ip_address, db=db
        )

        return {"success": True, **threat_analysis}

    except Exception as e:
        logger.error(f"Error checking threats for user_id={user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while checking for threats",
        )


@router.get("/metrics")
async def get_security_metrics(
    user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
):
    """
    Get comprehensive security metrics for the user.

    Includes statistics on sessions, logins, and security events.
    """
    try:
        metrics = SecurityMonitor.get_security_metrics(user.id, db)

        return {"success": True, "metrics": metrics}

    except Exception as e:
        logger.error(f"Error getting metrics for user_id={user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving security metrics",
        )
