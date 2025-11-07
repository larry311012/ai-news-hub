"""
Mock OAuth endpoints for testing without real credentials
"""
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
import logging

from database import get_db
from utils.oauth import create_or_update_oauth_user
from utils.auth import create_session
from api.auth import LoginResponse, UserResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# Mock user database
MOCK_USERS = {
    "google": {
        "id": "mock-google-user-123",
        "email": "testuser@gmail.com",
        "name": "Test User (Google)",
        "picture": "https://ui-avatars.com/api/?name=Test+User&background=4285F4&color=fff",
    },
    "github": {
        "id": "mock-github-user-456",
        "email": "testuser@github.com",
        "name": "Test User (GitHub)",
        "avatar_url": "https://ui-avatars.com/api/?name=Test+User&background=24292e&color=fff",
    },
}


@router.get("/google/test")
async def mock_google_oauth(return_url: str = Query(None), db: Session = Depends(get_db)):
    """
    Mock Google OAuth endpoint for testing.
    Simulates the entire OAuth flow without requiring real credentials.
    """
    logger.info("Mock Google OAuth initiated")

    # Simulate OAuth user creation
    mock_user = MOCK_USERS["google"]

    user = create_or_update_oauth_user(
        db=db,
        provider="google",
        oauth_id=mock_user["id"],
        email=mock_user["email"],
        name=mock_user["name"],
        picture=mock_user["picture"],
    )

    # Create session (returns tuple now)
    token, expires_at = create_session(
        user_id=user.id,
        db=db,
        expires_days=30,
        user_agent="Mock Test Client",
        ip_address="127.0.0.1",
    )

    logger.info(f"Mock OAuth login successful: user_id={user.id}, provider=google")

    # Redirect to return URL if provided
    if return_url:
        redirect_url = (
            f"{return_url}?token={token}&expires_at={expires_at.isoformat()}&provider=google"
        )
        return RedirectResponse(url=redirect_url)

    # Otherwise return JSON
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


@router.get("/github/test")
async def mock_github_oauth(return_url: str = Query(None), db: Session = Depends(get_db)):
    """
    Mock GitHub OAuth endpoint for testing.
    Simulates the entire OAuth flow without requiring real credentials.
    """
    logger.info("Mock GitHub OAuth initiated")

    # Simulate OAuth user creation
    mock_user = MOCK_USERS["github"]

    user = create_or_update_oauth_user(
        db=db,
        provider="github",
        oauth_id=mock_user["id"],
        email=mock_user["email"],
        name=mock_user["name"],
        picture=mock_user["avatar_url"],
    )

    # Create session (returns tuple now)
    token, expires_at = create_session(
        user_id=user.id,
        db=db,
        expires_days=30,
        user_agent="Mock Test Client",
        ip_address="127.0.0.1",
    )

    logger.info(f"Mock OAuth login successful: user_id={user.id}, provider=github")

    # Redirect to return URL if provided
    if return_url:
        redirect_url = (
            f"{return_url}?token={token}&expires_at={expires_at.isoformat()}&provider=github"
        )
        return RedirectResponse(url=redirect_url)

    # Otherwise return JSON
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


@router.get("/test-users")
async def get_mock_users():
    """
    Get list of available mock test users.
    """
    return {
        "success": True,
        "message": "Mock OAuth test endpoints available",
        "endpoints": {
            "google": "/api/auth/oauth/mock/google/test",
            "github": "/api/auth/oauth/mock/github/test",
        },
        "test_users": MOCK_USERS,
    }
