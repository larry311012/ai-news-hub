"""
Twitter OAuth 1.0a Utilities - Centralized Authentication

This module implements Twitter OAuth 1.0a (3-legged OAuth) for centralized
authentication. Unlike OAuth 2.0, this allows ONE centralized Twitter app
to authenticate ALL users without requiring each user to create their own app.

OAuth 1.0a Flow:
1. Request Token: Get temporary credentials from Twitter
2. User Authorization: Redirect user to Twitter for consent
3. Access Token: Exchange temporary credentials for permanent user tokens

Key Benefits:
- No need for users to create Twitter apps
- Centralized credentials (API Key + Secret)
- Per-user access tokens (stored encrypted)
- Tokens never expire (unless revoked by user)
- Works with Twitter API v1.1 and v2

Documentation: https://developer.twitter.com/en/docs/authentication/oauth-1-0a
"""

import os
import hmac
import hashlib
import base64
import urllib.parse
import time
import secrets
import logging
import httpx
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Twitter OAuth 1.0a Configuration
# ============================================================================

# Centralized app credentials (shared by all users)
# Note: These are loaded at module level for backward compatibility,
# but get_twitter_credentials() should be used for actual OAuth operations
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")  # Consumer Key
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET")  # Consumer Secret
TWITTER_CALLBACK_URL = os.getenv(
    "TWITTER_CALLBACK_URL", "http://localhost:8000/api/social-media/twitter/callback"
)


def is_placeholder_credential(value: Optional[str]) -> bool:
    """
    Check if a credential value is a placeholder (not real).

    Args:
        value: Credential value to check

    Returns:
        True if value is a placeholder, False if it's likely real
    """
    if not value:
        return True

    # Common placeholder patterns
    placeholders = [
        "your-",
        "your_",
        "placeholder",
        "example",
        "test-",
        "demo-",
        "xxx",
        "yyy",
        "zzz",
        "replace-me",
        "change-me",
        "add-your",
        "insert-",
    ]

    value_lower = value.lower()
    return any(placeholder in value_lower for placeholder in placeholders)


def get_twitter_credentials() -> dict:
    """
    Get Twitter OAuth credentials from database or environment.

    Checks database first, then falls back to environment variables.
    Validates that credentials are not placeholder values.

    Returns:
        dict with api_key, api_secret, callback_url, source, and is_valid
    """
    # Try database first
    try:
        from database import SessionLocal
        from utils.oauth_credential_manager import OAuthCredentialManager

        db = SessionLocal()
        try:
            manager = OAuthCredentialManager(db)
            creds = manager.get_credentials("twitter")

            if creds and creds.get("api_key") and creds.get("api_secret"):
                # Validate credentials are not placeholders
                api_key = creds["api_key"]
                api_secret = creds["api_secret"]

                if is_placeholder_credential(api_key) or is_placeholder_credential(api_secret):
                    logger.warning(
                        "Database credentials for Twitter appear to be placeholders. "
                        "Please configure real Twitter API credentials."
                    )
                    return {
                        "api_key": api_key,
                        "api_secret": api_secret,
                        "callback_url": creds.get("callback_url", TWITTER_CALLBACK_URL),
                        "source": "database",
                        "is_valid": False,
                        "error": "Credentials appear to be placeholder values",
                    }

                logger.info("Using database credentials for Twitter OAuth (validated)")
                return {
                    "api_key": api_key,
                    "api_secret": api_secret,
                    "callback_url": creds.get("callback_url", TWITTER_CALLBACK_URL),
                    "source": "database",
                    "is_valid": True,
                }
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"Could not get database credentials: {e}")

    # Fall back to environment variables
    api_key = TWITTER_API_KEY
    api_secret = TWITTER_API_SECRET

    # Validate environment credentials
    if is_placeholder_credential(api_key) or is_placeholder_credential(api_secret):
        logger.warning(
            "Environment credentials for Twitter appear to be placeholders. "
            "To enable Twitter OAuth:\n"
            "  1. Go to https://developer.twitter.com/en/portal/dashboard\n"
            "  2. Create an app and get API Key + Secret\n"
            "  3. Update .env file OR add to database via /api/admin/oauth-credentials\n"
            "  4. Restart the server"
        )
        return {
            "api_key": api_key,
            "api_secret": api_secret,
            "callback_url": TWITTER_CALLBACK_URL,
            "source": "environment",
            "is_valid": False,
            "error": "Credentials are placeholder values - please configure real Twitter API credentials",
        }

    logger.info("Using environment credentials for Twitter OAuth (validated)")
    return {
        "api_key": api_key,
        "api_secret": api_secret,
        "callback_url": TWITTER_CALLBACK_URL,
        "source": "environment",
        "is_valid": True,
    }


# Twitter OAuth endpoints
TWITTER_REQUEST_TOKEN_URL = "https://api.twitter.com/oauth/request_token"
TWITTER_AUTHORIZE_URL = "https://api.twitter.com/oauth/authorize"
TWITTER_ACCESS_TOKEN_URL = "https://api.twitter.com/oauth/access_token"

# Twitter API endpoints
TWITTER_VERIFY_CREDENTIALS_URL = "https://api.twitter.com/1.1/account/verify_credentials.json"
TWITTER_USER_INFO_URL = "https://api.twitter.com/2/users/me"


# ============================================================================
# OAuth 1.0a Signature Generation
# ============================================================================


def generate_oauth_nonce() -> str:
    """
    Generate a random nonce for OAuth requests.

    Returns:
        32-character random hex string
    """
    return secrets.token_hex(16)


def generate_oauth_timestamp() -> str:
    """
    Generate current Unix timestamp for OAuth requests.

    Returns:
        Current timestamp as string
    """
    return str(int(time.time()))


def percent_encode(value: str) -> str:
    """
    Percent-encode a string according to OAuth spec.

    OAuth requires specific encoding rules:
    - Letters, digits, '-', '.', '_', '~' are not encoded
    - All other characters are percent-encoded
    - Spaces are encoded as %20 (not +)

    Args:
        value: String to encode

    Returns:
        Percent-encoded string
    """
    return urllib.parse.quote(str(value), safe="~")


def generate_signature_base_string(method: str, url: str, params: Dict[str, str]) -> str:
    """
    Generate OAuth signature base string.

    The signature base string is composed of:
    - HTTP method (uppercase)
    - Base URL (without query parameters)
    - Normalized request parameters (sorted)

    Format: METHOD&URL&PARAMETERS

    Args:
        method: HTTP method (GET, POST, etc.)
        url: Base URL without query parameters
        params: All parameters (OAuth + request params)

    Returns:
        Signature base string
    """
    # Normalize method
    method = method.upper()

    # Sort parameters by key
    sorted_params = sorted(params.items())

    # Build parameter string
    param_string = "&".join([f"{percent_encode(k)}={percent_encode(v)}" for k, v in sorted_params])

    # Build signature base string
    base_string = f"{method}&{percent_encode(url)}&{percent_encode(param_string)}"

    logger.debug(f"Signature base string: {base_string[:100]}...")
    return base_string


def generate_signing_key(consumer_secret: str, token_secret: str = "") -> str:
    """
    Generate OAuth signing key.

    Format: CONSUMER_SECRET&TOKEN_SECRET
    For request token: TOKEN_SECRET is empty string

    Args:
        consumer_secret: App consumer secret
        token_secret: User token secret (empty for request token)

    Returns:
        Signing key
    """
    return f"{percent_encode(consumer_secret)}&{percent_encode(token_secret)}"


def generate_oauth_signature(
    method: str, url: str, params: Dict[str, str], consumer_secret: str, token_secret: str = ""
) -> str:
    """
    Generate OAuth 1.0a signature using HMAC-SHA1.

    Steps:
    1. Create signature base string
    2. Create signing key
    3. Generate HMAC-SHA1 signature
    4. Base64 encode signature

    Args:
        method: HTTP method (GET, POST)
        url: Base URL
        params: All parameters (OAuth + request)
        consumer_secret: App consumer secret
        token_secret: User token secret (empty for request token)

    Returns:
        Base64-encoded signature
    """
    # Generate signature base string
    base_string = generate_signature_base_string(method, url, params)

    # Generate signing key
    signing_key = generate_signing_key(consumer_secret, token_secret)

    # Generate HMAC-SHA1 signature
    signature_bytes = hmac.new(
        signing_key.encode("utf-8"), base_string.encode("utf-8"), hashlib.sha1
    ).digest()

    # Base64 encode
    signature = base64.b64encode(signature_bytes).decode("utf-8")

    logger.debug(f"Generated signature: {signature[:20]}...")
    return signature


def generate_oauth_header(
    method: str,
    url: str,
    consumer_key: str,
    consumer_secret: str,
    token: Optional[str] = None,
    token_secret: str = "",
    params: Optional[Dict[str, str]] = None,
    callback_url: Optional[str] = None,
    verifier: Optional[str] = None,
) -> str:
    """
    Generate complete OAuth Authorization header.

    This creates the OAuth header with all required parameters:
    - oauth_consumer_key
    - oauth_signature_method
    - oauth_timestamp
    - oauth_nonce
    - oauth_version
    - oauth_signature (computed)
    - oauth_token (if provided)
    - oauth_callback (if provided)
    - oauth_verifier (if provided)

    Args:
        method: HTTP method
        url: Request URL
        consumer_key: App consumer key
        consumer_secret: App consumer secret
        token: OAuth token (for access token request)
        token_secret: OAuth token secret (for signature)
        params: Additional request parameters
        callback_url: OAuth callback URL (for request token)
        verifier: OAuth verifier (for access token)

    Returns:
        OAuth Authorization header value
    """
    # OAuth parameters
    oauth_params = {
        "oauth_consumer_key": consumer_key,
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": generate_oauth_timestamp(),
        "oauth_nonce": generate_oauth_nonce(),
        "oauth_version": "1.0",
    }

    # Add optional parameters
    if token:
        oauth_params["oauth_token"] = token
    if callback_url:
        oauth_params["oauth_callback"] = callback_url
    if verifier:
        oauth_params["oauth_verifier"] = verifier

    # Merge with request parameters for signature
    all_params = {**oauth_params}
    if params:
        all_params.update(params)

    # Generate signature
    signature = generate_oauth_signature(method, url, all_params, consumer_secret, token_secret)
    oauth_params["oauth_signature"] = signature

    # Build Authorization header
    header_parts = [
        f'{percent_encode(k)}="{percent_encode(v)}"' for k, v in sorted(oauth_params.items())
    ]
    header = f"OAuth {', '.join(header_parts)}"

    logger.debug(f"Generated OAuth header: {header[:100]}...")
    return header


# ============================================================================
# OAuth 1.0a Flow Implementation
# ============================================================================


async def get_request_token() -> Optional[Dict[str, str]]:
    """
    Step 1: Obtain a request token from Twitter.

    This is the first step in the OAuth 1.0a flow. We request temporary
    credentials from Twitter that will be used to redirect the user for
    authorization.

    Returns:
        Dictionary with:
        - oauth_token: Temporary token
        - oauth_token_secret: Temporary token secret
        - oauth_callback_confirmed: "true" if callback is confirmed

        None if request fails

    Raises:
        ValueError: If Twitter OAuth not configured
    """
    # Get credentials from database or environment
    creds = get_twitter_credentials()

    # Check if credentials are valid
    if not creds.get("is_valid", False):
        error_msg = creds.get("error", "Twitter OAuth credentials not configured or invalid")
        logger.error(f"Cannot get request token: {error_msg}")
        raise ValueError(error_msg)

    if not creds["api_key"] or not creds["api_secret"]:
        raise ValueError("Twitter OAuth 1.0a not configured - missing API key or secret")

    try:
        # Generate OAuth header
        auth_header = generate_oauth_header(
            method="POST",
            url=TWITTER_REQUEST_TOKEN_URL,
            consumer_key=creds["api_key"],
            consumer_secret=creds["api_secret"],
            callback_url=creds["callback_url"],
        )

        logger.info(f"Requesting Twitter OAuth token using {creds['source']} credentials")

        # Make request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TWITTER_REQUEST_TOKEN_URL,
                headers={
                    "Authorization": auth_header,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )

            if response.status_code != 200:
                logger.error(
                    f"Failed to get request token from Twitter: {response.status_code} - {response.text}\n"
                    f"Credential source: {creds['source']}\n"
                    f"This usually means:\n"
                    f"  1. Invalid API credentials\n"
                    f"  2. App not configured for OAuth 1.0a in Twitter Developer Portal\n"
                    f"  3. Callback URL mismatch in Twitter app settings"
                )
                return None

            # Parse response (URL-encoded)
            response_data = urllib.parse.parse_qs(response.text)

            # Extract values
            result = {
                "oauth_token": response_data.get("oauth_token", [None])[0],
                "oauth_token_secret": response_data.get("oauth_token_secret", [None])[0],
                "oauth_callback_confirmed": response_data.get("oauth_callback_confirmed", [None])[
                    0
                ],
            }

            if not result["oauth_token"] or not result["oauth_token_secret"]:
                logger.error("Invalid response from Twitter: missing token")
                return None

            logger.info(
                f"Successfully obtained request token: {result['oauth_token'][:10]}... (source: {creds['source']})"
            )
            return result

    except Exception as e:
        logger.error(f"Error getting request token: {str(e)}")
        return None


def get_authorization_url(oauth_token: str) -> str:
    """
    Step 2: Generate authorization URL for user to authorize the app.

    After obtaining a request token, we redirect the user to Twitter
    to authorize our application. The user will see a consent screen.

    Args:
        oauth_token: Request token from step 1

    Returns:
        Authorization URL to redirect user to

    Raises:
        ValueError: If oauth_token is missing
    """
    if not oauth_token:
        raise ValueError("oauth_token is required")

    # Build authorization URL
    auth_url = f"{TWITTER_AUTHORIZE_URL}?oauth_token={percent_encode(oauth_token)}"

    logger.info(f"Generated authorization URL for token: {oauth_token[:10]}...")
    return auth_url


async def get_access_token(
    oauth_token: str, oauth_token_secret: str, oauth_verifier: str
) -> Optional[Dict[str, str]]:
    """
    Step 3: Exchange request token for access token.

    After the user authorizes, Twitter redirects back to our callback
    with an oauth_verifier. We use this to exchange the temporary
    request token for permanent access credentials.

    Args:
        oauth_token: Request token from callback
        oauth_token_secret: Request token secret from step 1
        oauth_verifier: Verifier from callback

    Returns:
        Dictionary with:
        - oauth_token: User's access token (permanent)
        - oauth_token_secret: User's access token secret
        - user_id: Twitter user ID
        - screen_name: Twitter username

        None if request fails

    Raises:
        ValueError: If parameters are missing
    """
    if not oauth_token or not oauth_token_secret or not oauth_verifier:
        raise ValueError("oauth_token, oauth_token_secret, and oauth_verifier are required")

    # Get credentials from database or environment
    creds = get_twitter_credentials()

    # Check if credentials are valid
    if not creds.get("is_valid", False):
        error_msg = creds.get("error", "Twitter OAuth credentials not configured or invalid")
        logger.error(f"Cannot get access token: {error_msg}")
        raise ValueError(error_msg)

    if not creds["api_key"] or not creds["api_secret"]:
        raise ValueError("Twitter OAuth 1.0a not configured")

    try:
        # Generate OAuth header with verifier
        auth_header = generate_oauth_header(
            method="POST",
            url=TWITTER_ACCESS_TOKEN_URL,
            consumer_key=creds["api_key"],
            consumer_secret=creds["api_secret"],
            token=oauth_token,
            token_secret=oauth_token_secret,
            verifier=oauth_verifier,
        )

        logger.info(
            f"Exchanging request token for access token using {creds['source']} credentials"
        )

        # Make request
        async with httpx.AsyncClient() as client:
            response = await client.post(
                TWITTER_ACCESS_TOKEN_URL,
                headers={
                    "Authorization": auth_header,
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )

            if response.status_code != 200:
                logger.error(
                    f"Failed to get access token: {response.status_code} - {response.text}\n"
                    f"Credential source: {creds['source']}"
                )
                return None

            # Parse response (URL-encoded)
            response_data = urllib.parse.parse_qs(response.text)

            # Extract values
            result = {
                "oauth_token": response_data.get("oauth_token", [None])[0],
                "oauth_token_secret": response_data.get("oauth_token_secret", [None])[0],
                "user_id": response_data.get("user_id", [None])[0],
                "screen_name": response_data.get("screen_name", [None])[0],
            }

            if not result["oauth_token"] or not result["oauth_token_secret"]:
                logger.error("Invalid response from Twitter: missing token")
                return None

            logger.info(
                f"Successfully obtained access token for user: @{result['screen_name']} (source: {creds['source']})"
            )
            return result

    except Exception as e:
        logger.error(f"Error getting access token: {str(e)}")
        return None


# ============================================================================
# User Information Retrieval
# ============================================================================


async def get_user_info(access_token: str, access_token_secret: str) -> Optional[Dict[str, Any]]:
    """
    Get Twitter user information using OAuth 1.0a credentials.

    Uses Twitter API v1.1 account/verify_credentials endpoint to get
    detailed user information.

    Args:
        access_token: User's OAuth access token
        access_token_secret: User's OAuth access token secret

    Returns:
        Dictionary with user info:
        - id_str: Twitter user ID
        - screen_name: Twitter username
        - name: Display name
        - profile_image_url_https: Profile image URL
        - followers_count: Number of followers
        - friends_count: Number of following
        - ... (more fields)

        None if request fails
    """
    if not access_token or not access_token_secret:
        raise ValueError("access_token and access_token_secret are required")

    # Get credentials from database or environment
    creds = get_twitter_credentials()

    # Check if credentials are valid
    if not creds.get("is_valid", False):
        error_msg = creds.get("error", "Twitter OAuth credentials not configured or invalid")
        logger.error(f"Cannot get user info: {error_msg}")
        raise ValueError(error_msg)

    if not creds["api_key"] or not creds["api_secret"]:
        raise ValueError("Twitter OAuth 1.0a not configured")

    try:
        # Parameters for user info request
        params = {
            "skip_status": "true",  # Don't include latest tweet
            "include_email": "false",  # We don't need email
        }

        # Generate OAuth header
        auth_header = generate_oauth_header(
            method="GET",
            url=TWITTER_VERIFY_CREDENTIALS_URL,
            consumer_key=creds["api_key"],
            consumer_secret=creds["api_secret"],
            token=access_token,
            token_secret=access_token_secret,
            params=params,
        )

        # Make request
        async with httpx.AsyncClient() as client:
            response = await client.get(
                TWITTER_VERIFY_CREDENTIALS_URL,
                headers={"Authorization": auth_header},
                params=params,
            )

            if response.status_code != 200:
                logger.error(f"Failed to get user info: {response.status_code} - {response.text}")
                return None

            user_info = response.json()

            # Normalize to match our expected format
            normalized = {
                "id": user_info.get("id_str"),
                "username": user_info.get("screen_name"),
                "name": user_info.get("name"),
                "profile_image_url": user_info.get("profile_image_url_https"),
                "followers_count": user_info.get("followers_count"),
                "following_count": user_info.get("friends_count"),
                "tweet_count": user_info.get("statuses_count"),
                "verified": user_info.get("verified"),
                "description": user_info.get("description"),
                "location": user_info.get("location"),
                "created_at": user_info.get("created_at"),
                # Store full response in metadata
                "raw_data": user_info,
            }

            logger.info(f"Retrieved user info for: @{normalized['username']}")
            return normalized

    except Exception as e:
        logger.error(f"Error getting user info: {str(e)}")
        return None


# ============================================================================
# Token Validation
# ============================================================================


async def validate_credentials(access_token: str, access_token_secret: str) -> bool:
    """
    Validate Twitter OAuth 1.0a credentials by making a test API call.

    This calls the verify_credentials endpoint to check if the tokens
    are still valid.

    Args:
        access_token: User's OAuth access token
        access_token_secret: User's OAuth access token secret

    Returns:
        True if credentials are valid, False otherwise
    """
    try:
        user_info = await get_user_info(access_token, access_token_secret)
        return user_info is not None
    except Exception as e:
        logger.error(f"Error validating credentials: {str(e)}")
        return False


# ============================================================================
# API Call Helper (for Publishing)
# ============================================================================


def generate_api_auth_header(
    method: str,
    url: str,
    access_token: str,
    access_token_secret: str,
    params: Optional[Dict[str, str]] = None,
    consumer_key: Optional[str] = None,
    consumer_secret: Optional[str] = None,
) -> str:
    """
    Generate OAuth header for Twitter API calls (e.g., posting tweets).

    Use this when making authenticated API calls to Twitter endpoints
    like posting tweets, uploading media, etc.

    Args:
        method: HTTP method (GET, POST)
        url: API endpoint URL
        access_token: User's OAuth access token
        access_token_secret: User's OAuth access token secret
        params: Request parameters
        consumer_key: Twitter app consumer key (optional, will fetch from credentials if not provided)
        consumer_secret: Twitter app consumer secret (optional, will fetch from credentials if not provided)

    Returns:
        OAuth Authorization header value

    Example:
        ```python
        # Post a tweet
        auth_header = generate_api_auth_header(
            method="POST",
            url="https://api.twitter.com/1.1/statuses/update.json",
            access_token=user_token,
            access_token_secret=user_secret,
            params={"status": "Hello Twitter!"}
        )

        response = await client.post(
            "https://api.twitter.com/1.1/statuses/update.json",
            headers={"Authorization": auth_header},
            data={"status": "Hello Twitter!"}
        )
        ```
    """
    # If consumer keys not provided, get from credentials
    if not consumer_key or not consumer_secret:
        creds = get_twitter_credentials()

        # Allow valid credentials or skip validation if keys explicitly provided
        if not creds.get("is_valid", False):
            logger.warning(f"Twitter credentials validation failed, but will attempt with provided tokens")

        consumer_key = consumer_key or creds.get("api_key")
        consumer_secret = consumer_secret or creds.get("api_secret")

        if not consumer_key or not consumer_secret:
            raise ValueError("Twitter consumer keys not configured")

    return generate_oauth_header(
        method=method,
        url=url,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        token=access_token,
        token_secret=access_token_secret,
        params=params,
    )


# ============================================================================
# Utility Functions
# ============================================================================


def is_oauth1_configured() -> bool:
    """
    Check if Twitter OAuth 1.0a is configured with VALID credentials.

    Checks database credentials first, then falls back to environment variables.
    Validates that credentials are not placeholder values.

    Returns:
        True if VALID API key and secret are set, False otherwise
    """
    creds = get_twitter_credentials()
    return creds.get("is_valid", False)


def get_oauth_config_status() -> Dict[str, Any]:
    """
    Get OAuth 1.0a configuration status with detailed validation.

    Checks database credentials first, then falls back to environment variables.
    Includes validation of credential values.

    Returns:
        Dictionary with configuration details including validation status
    """
    creds = get_twitter_credentials()

    return {
        "configured": creds.get("is_valid", False),
        "api_key_set": bool(creds.get("api_key")),
        "api_secret_set": bool(creds.get("api_secret")),
        "callback_url": creds.get("callback_url", TWITTER_CALLBACK_URL),
        "oauth_version": "1.0a",
        "source": creds.get("source", "unknown"),
        "is_valid": creds.get("is_valid", False),
        "error": creds.get("error") if not creds.get("is_valid") else None,
        "help": None
        if creds.get("is_valid")
        else (
            "To configure Twitter OAuth:\n"
            "1. Visit https://developer.twitter.com/en/portal/dashboard\n"
            "2. Create an app and enable OAuth 1.0a\n"
            "3. Copy API Key and API Secret\n"
            "4. Add to database: POST /api/admin/oauth-credentials/twitter\n"
            "   OR update .env file with TWITTER_API_KEY and TWITTER_API_SECRET\n"
            "5. Restart the server"
        ),
    }


# ============================================================================
# Logging and Debugging
# ============================================================================


def log_oauth_request(
    step: str, method: str, url: str, params: Optional[Dict[str, str]] = None, success: bool = True
):
    """
    Log OAuth request for debugging.

    Args:
        step: OAuth step (request_token, authorize, access_token)
        method: HTTP method
        url: Request URL
        params: Request parameters
        success: Whether request was successful
    """
    log_data = {
        "step": step,
        "method": method,
        "url": url,
        "success": success,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if params:
        # Sanitize sensitive data
        safe_params = {
            k: v[:10] + "..." if k in ["oauth_token", "oauth_signature"] else v
            for k, v in params.items()
        }
        log_data["params"] = safe_params

    if success:
        logger.info(f"OAuth request successful: {log_data}")
    else:
        logger.error(f"OAuth request failed: {log_data}")
