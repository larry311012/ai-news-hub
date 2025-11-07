"""
OAuth Configuration Helper

This module provides helper functions to get OAuth credentials with
fallback from database to environment variables. This allows for
seamless integration of database-backed credentials while maintaining
backward compatibility with .env files.

Usage:
    from utils.oauth_config import get_twitter_config, get_linkedin_config

    # In your OAuth flow
    twitter_config = get_twitter_config(db)
    if twitter_config:
        api_key = twitter_config['api_key']
        api_secret = twitter_config['api_secret']
"""

import os
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_twitter_config(db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
    """
    Get Twitter OAuth 1.0a configuration.

    Priority:
    1. Database credentials (if db session provided and configured)
    2. Environment variables

    Args:
        db: Optional database session for retrieving database credentials

    Returns:
        Dictionary with:
        {
            "api_key": "...",
            "api_secret": "...",
            "callback_url": "...",
            "oauth_version": "1.0a",
            "source": "database" or "env"
        }

        None if not configured
    """
    # Try database first if session provided
    if db:
        try:
            from utils.oauth_credential_manager import OAuthCredentialManager

            manager = OAuthCredentialManager(db)
            creds = manager.get_credentials("twitter")
            if creds:
                logger.debug("Using Twitter credentials from database")
                return creds
        except Exception as e:
            logger.warning(f"Error retrieving Twitter credentials from database: {str(e)}")

    # Fallback to environment variables
    api_key = os.getenv("TWITTER_API_KEY")
    api_secret = os.getenv("TWITTER_API_SECRET")
    callback_url = os.getenv(
        "TWITTER_CALLBACK_URL", "http://localhost:8000/api/social-media/twitter-oauth1/callback"
    )

    if api_key and api_secret:
        logger.debug("Using Twitter credentials from environment")
        return {
            "api_key": api_key,
            "api_secret": api_secret,
            "callback_url": callback_url,
            "oauth_version": "1.0a",
            "source": "env",
        }

    logger.warning("Twitter OAuth credentials not configured")
    return None


def get_linkedin_config(db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
    """
    Get LinkedIn OAuth 2.0 configuration.

    Priority:
    1. Database credentials (if db session provided and configured)
    2. Environment variables

    Args:
        db: Optional database session for retrieving database credentials

    Returns:
        Dictionary with:
        {
            "client_id": "...",
            "client_secret": "...",
            "redirect_uri": "...",
            "scopes": ["openid", "profile", ...],
            "oauth_version": "2.0",
            "source": "database" or "env"
        }

        None if not configured
    """
    # Try database first if session provided
    if db:
        try:
            from utils.oauth_credential_manager import OAuthCredentialManager

            manager = OAuthCredentialManager(db)
            creds = manager.get_credentials("linkedin")
            if creds:
                logger.debug("Using LinkedIn credentials from database")
                return creds
        except Exception as e:
            logger.warning(f"Error retrieving LinkedIn credentials from database: {str(e)}")

    # Fallback to environment variables
    client_id = os.getenv("LINKEDIN_CLIENT_ID")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
    redirect_uri = os.getenv(
        "LINKEDIN_REDIRECT_URI", "http://localhost:8000/api/social-media/linkedin/callback"
    )

    if client_id and client_secret:
        logger.debug("Using LinkedIn credentials from environment")
        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "scopes": ["openid", "profile", "email", "w_member_social"],
            "oauth_version": "2.0",
            "source": "env",
        }

    logger.warning("LinkedIn OAuth credentials not configured")
    return None


def get_threads_config(db: Optional[Session] = None) -> Optional[Dict[str, Any]]:
    """
    Get Threads OAuth 2.0 configuration.

    Priority:
    1. Database credentials (if db session provided and configured)
    2. Environment variables

    Args:
        db: Optional database session for retrieving database credentials

    Returns:
        Dictionary with:
        {
            "client_id": "...",  # App ID
            "client_secret": "...",  # App Secret
            "redirect_uri": "...",
            "scopes": ["threads_basic", "threads_content_publish"],
            "oauth_version": "2.0",
            "source": "database" or "env"
        }

        None if not configured
    """
    # Try database first if session provided
    if db:
        try:
            from utils.oauth_credential_manager import OAuthCredentialManager

            manager = OAuthCredentialManager(db)
            creds = manager.get_credentials("threads")
            if creds:
                logger.debug("Using Threads credentials from database")
                return creds
        except Exception as e:
            logger.warning(f"Error retrieving Threads credentials from database: {str(e)}")

    # Fallback to environment variables
    client_id = os.getenv("THREADS_APP_ID")  # Note: Threads uses APP_ID
    client_secret = os.getenv("THREADS_APP_SECRET")
    redirect_uri = os.getenv(
        "THREADS_REDIRECT_URI", "http://localhost:8000/api/social-media/threads/callback"
    )

    if client_id and client_secret:
        logger.debug("Using Threads credentials from environment")
        return {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "scopes": ["threads_basic", "threads_content_publish"],
            "oauth_version": "2.0",
            "source": "env",
        }

    logger.warning("Threads OAuth credentials not configured")
    return None


def is_platform_configured(platform: str, db: Optional[Session] = None) -> bool:
    """
    Check if a platform is configured.

    Args:
        platform: Platform name (twitter, linkedin, threads)
        db: Optional database session

    Returns:
        True if platform is configured, False otherwise
    """
    config_getters = {
        "twitter": get_twitter_config,
        "linkedin": get_linkedin_config,
        "threads": get_threads_config,
    }

    getter = config_getters.get(platform.lower())
    if not getter:
        return False

    config = getter(db)
    return config is not None


def get_all_platforms_config(db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Get configuration status for all platforms.

    Args:
        db: Optional database session

    Returns:
        Dictionary mapping platform names to their config status
    """
    return {
        "twitter": {"configured": is_platform_configured("twitter", db), "oauth_version": "1.0a"},
        "linkedin": {"configured": is_platform_configured("linkedin", db), "oauth_version": "2.0"},
        "threads": {"configured": is_platform_configured("threads", db), "oauth_version": "2.0"},
    }
