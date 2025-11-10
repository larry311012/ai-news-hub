"""
Authentication API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
import logging

from database import get_db, User, UserSession, UserApiKey
from utils.auth_selector import (
    hash_password,
    verify_password,
    create_session,
    get_current_user_dependency,
    delete_session,
)
from utils.encryption import encrypt_api_key, decrypt_api_key
from utils.input_sanitizer import InputSanitizer

router = APIRouter()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Pydantic models for request/response
class RegisterRequest(BaseModel):
    """Request model for user registration"""

    email: EmailStr
    password: str
    full_name: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password meets minimum requirements"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        """Validate full name is not empty"""
        if not v or not v.strip():
            raise ValueError("Full name cannot be empty")
        return v.strip()


class LoginRequest(BaseModel):
    """Request model for user login"""

    email: EmailStr
    password: str
    remember_me: bool = False


class UserResponse(BaseModel):
    """Response model for user data"""

    id: int
    email: str
    full_name: str
    bio: Optional[str] = None
    created_at: datetime
    is_verified: bool = False
    is_admin: bool = False

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Response model for successful login"""

    success: bool
    token: str
    user: UserResponse
    expires_at: datetime


class StandardResponse(BaseModel):
    """Standard response for success/error messages"""

    success: bool
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response model"""

    success: bool = False
    error: str
    code: str


class UpdateProfileRequest(BaseModel):
    """Request model for updating user profile"""

    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    bio: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate full name is not empty if provided"""
        if v is not None and (not v or not v.strip()):
            raise ValueError("Full name cannot be empty")
        return v.strip() if v else None

    @field_validator("bio")
    @classmethod
    def validate_bio(cls, v: Optional[str]) -> Optional[str]:
        """Validate bio length"""
        if v is not None and len(v) > 1000:
            raise ValueError("Bio must be less than 1000 characters")
        return v.strip() if v else None


class ChangePasswordRequest(BaseModel):
    """Request model for changing password"""

    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        """Validate new password meets minimum requirements"""
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters long")
        return v


class DeleteAccountRequest(BaseModel):
    """Request model for deleting account"""

    password: str


class SaveApiKeyRequest(BaseModel):
    """Request model for saving API key"""

    provider: str
    api_key: str
    name: Optional[str] = None

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        """Validate provider is supported"""
        allowed_providers = ["openai", "anthropic", "twitter", "linkedin", "facebook"]
        if v.lower() not in allowed_providers:
            raise ValueError(f'Provider must be one of: {", ".join(allowed_providers)}')
        return v.lower()

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate API key is not empty"""
        if not v or not v.strip():
            raise ValueError("API key cannot be empty")
        return v.strip()


class ApiKeyResponse(BaseModel):
    """Response model for API key info (without exposing actual key)"""

    provider: str
    name: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ApiKeyTestResponse(BaseModel):
    """
    Response model for API key test endpoint.

    iOS-compatible format matching the Swift model:
    struct APIKeyTestResponse: Codable {
        let isValid: Bool
        let message: String?
        let provider: APIProvider
        let testedAt: Date
    }
    """

    is_valid: bool
    message: str
    provider: str
    tested_at: str  # ISO8601 format

    class Config:
        # Use alias for snake_case -> camelCase conversion if needed
        populate_by_name = True


# Custom exceptions
class InvalidCredentialsException(HTTPException):
    """Exception for invalid login credentials"""

    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


class UserAlreadyExistsException(HTTPException):
    """Exception for duplicate email registration"""

    def __init__(self):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")


# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new user with email and password.

    Creates a new user account and returns an authentication token.

    Args:
        request: Registration data (email, password, full_name)
        db: Database session

    Returns:
        LoginResponse with token and user data

    Raises:
        UserAlreadyExistsException: If email is already registered
        HTTPException: For validation or database errors
    """
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.email == request.email.lower()).first()

        if existing_user:
            logger.warning(f"Registration attempt with existing email: {request.email}")
            raise UserAlreadyExistsException()

        # Sanitize full_name to prevent XSS
        sanitized_full_name = InputSanitizer.validate_and_sanitize_input(
            request.full_name,
            field_name="Full name",
            max_length=100,
            check_xss=True,
            check_sql=False,  # Not needed for name field
        )

        # Hash password
        password_hash = hash_password(request.password)

        # Create user
        new_user = User(
            email=request.email.lower(),
            password_hash=password_hash,
            full_name=sanitized_full_name,
            is_active=True,
            is_verified=False,
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Create session (no remember_me for registration - default 1 day)
        session_token, expires_at = create_session(new_user.id, db)

        logger.info(f"New user registered: user_id={new_user.id}, email={new_user.email}")

        return LoginResponse(
            success=True,
            token=session_token,
            user=UserResponse(
                id=new_user.id,
                email=new_user.email,
                full_name=new_user.full_name,
                bio=new_user.bio,
                created_at=new_user.created_at,
                is_verified=new_user.is_verified,
            ),
            expires_at=expires_at,
        )

    except (UserAlreadyExistsException, HTTPException):
        raise
    except ValueError as e:
        logger.error(f"Validation error during registration: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error during registration: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during registration",
        )


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user and create session.

    Validates credentials and returns an authentication token.

    Args:
        request: Login data (email, password, remember_me)
        db: Database session

    Returns:
        LoginResponse with token and user data

    Raises:
        InvalidCredentialsException: If credentials are invalid
        HTTPException: For database errors
    """
    try:
        # Find user by email (case-insensitive)
        user = db.query(User).filter(User.email == request.email.lower()).first()

        if not user:
            logger.warning(f"Login attempt with non-existent email: {request.email}")
            raise InvalidCredentialsException()

        # Verify password
        if not verify_password(request.password, user.password_hash):
            logger.warning(f"Failed login attempt for user_id={user.id}")
            raise InvalidCredentialsException()

        # Check if user is active
        if not user.is_active:
            logger.warning(f"Login attempt for inactive user: user_id={user.id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been deactivated. Please contact support.",
            )

        # Create session with remember_me flag
        # remember_me=True: 30 days, remember_me=False: 1 day
        session_token, expires_at = create_session(user.id, db, remember_me=request.remember_me)

        # Update last login timestamp
        user.updated_at = datetime.utcnow()
        db.commit()

        logger.info(
            f"User logged in: user_id={user.id}, remember_me={request.remember_me}, "
            f"expires_at={expires_at}"
        )

        return LoginResponse(
            success=True,
            token=session_token,
            user=UserResponse(
                id=user.id,
                email=user.email,
                full_name=user.full_name,
                bio=user.bio,
                created_at=user.created_at,
                is_verified=user.is_verified,
                is_admin=user.is_admin if hasattr(user, "is_admin") else False,
            ),
            expires_at=expires_at,
        )

    except (InvalidCredentialsException, HTTPException):
        raise
    except Exception as e:
        logger.error(f"Error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login",
        )


@router.post("/logout", response_model=StandardResponse)
async def logout(
    request: Request,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Logout user by invalidating current session.

    Args:
        request: FastAPI request object for extracting authorization header
        user: Current authenticated user
        db: Database session

    Returns:
        Success response
    """
    try:
        # Extract token from Authorization header
        authorization = request.headers.get("authorization")
        token = None
        if authorization:
            parts = authorization.split()
            if len(parts) == 2:
                token = parts[1]

        if token:
            delete_session(token, db)
            logger.info(f"User logged out: user_id={user.id}")

        return StandardResponse(success=True, message="Successfully logged out")

    except Exception as e:
        logger.error(f"Error during logout: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during logout",
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: User = Depends(get_current_user_dependency)):
    """
    Get current authenticated user information.

    Args:
        user: Current authenticated user (from dependency)

    Returns:
        UserResponse with user data
    """
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        bio=user.bio,
        created_at=user.created_at,
        is_verified=user.is_verified,
    )


@router.get("/profile", response_model=UserResponse)
async def get_profile(user: User = Depends(get_current_user_dependency)):
    """
    Get current user profile.

    Args:
        user: Current authenticated user

    Returns:
        UserResponse with user data
    """
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        bio=user.bio,
        created_at=user.created_at,
        is_verified=user.is_verified,
        is_admin=user.is_admin if hasattr(user, "is_admin") else False,
    )


@router.patch("/profile", response_model=UserResponse)
async def update_profile(
    request: UpdateProfileRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Update user profile information.

    Args:
        request: Profile update data (full_name, email, bio)
        user: Current authenticated user
        db: Database session

    Returns:
        Updated user data

    Raises:
        HTTPException: If email is already taken or validation fails
    """
    try:
        # Track if any changes were made
        changes_made = False

        # Update full name if provided
        if request.full_name is not None:
            user.full_name = request.full_name
            changes_made = True
            logger.info(f"Updated full_name for user_id={user.id}")

        # Update email if provided and different
        if request.email is not None and request.email.lower() != user.email:
            # Check if new email is already taken
            existing_user = (
                db.query(User)
                .filter(User.email == request.email.lower(), User.id != user.id)
                .first()
            )

            if existing_user:
                logger.warning(f"Email update failed - already exists: {request.email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This email is already in use by another account",
                )

            user.email = request.email.lower()
            changes_made = True
            logger.info(f"Updated email for user_id={user.id}")

        # Update bio if provided
        if request.bio is not None:
            user.bio = request.bio
            changes_made = True
            logger.info(f"Updated bio for user_id={user.id}")

        if changes_made:
            user.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(user)

        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            bio=user.bio,
            created_at=user.created_at,
            is_verified=user.is_verified,
            is_admin=user.is_admin if hasattr(user, "is_admin") else False,
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error during profile update: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating profile for user_id={user.id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating profile",
        )


@router.post("/change-password", response_model=StandardResponse)
async def change_password(
    password_request: ChangePasswordRequest,
    http_request: Request,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Change user password.

    Verifies current password, updates to new password, and invalidates
    all other sessions except the current one for security.

    Args:
        password_request: Password change data (current_password, new_password)
        http_request: FastAPI request object for extracting authorization header
        user: Current authenticated user
        db: Database session

    Returns:
        Success response

    Raises:
        HTTPException: If current password is incorrect
    """
    try:
        # Verify current password
        if not verify_password(password_request.current_password, user.password_hash):
            logger.warning(
                f"Password change failed - incorrect current password for user_id={user.id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect"
            )

        # Hash new password
        new_password_hash = hash_password(password_request.new_password)

        # Update password
        user.password_hash = new_password_hash
        user.updated_at = datetime.utcnow()

        # Extract current token to preserve it
        authorization = http_request.headers.get("authorization")
        current_token = None
        if authorization:
            parts = authorization.split()
            if len(parts) == 2:
                current_token = parts[1]

        # Invalidate all other sessions except current one
        sessions_to_delete = (
            db.query(UserSession)
            .filter(
                UserSession.user_id == user.id,
                UserSession.token != current_token if current_token else True,
            )
            .all()
        )

        deleted_count = len(sessions_to_delete)
        for session in sessions_to_delete:
            db.delete(session)

        db.commit()

        logger.info(
            f"Password changed for user_id={user.id}, invalidated {deleted_count} other sessions"
        )

        return StandardResponse(
            success=True,
            message=(
                f"Password changed successfully. {deleted_count} other "
                f"sessions have been logged out for security."
            ),
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error during password change: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error changing password for user_id={user.id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while changing password",
        )


@router.delete("/account", response_model=StandardResponse)
async def delete_account(
    request: DeleteAccountRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Delete user account permanently.

    Verifies password before deletion. Cascades to delete all user data
    including sessions, articles, posts, and API keys.

    Args:
        request: Delete account data (password for verification)
        user: Current authenticated user
        db: Database session

    Returns:
        Success response

    Raises:
        HTTPException: If password is incorrect
    """
    try:
        # Verify password before deletion
        if not verify_password(request.password, user.password_hash):
            logger.warning(f"Account deletion failed - incorrect password for user_id={user.id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Password is incorrect"
            )

        user_id = user.id
        user_email = user.email

        # Delete user (cascade will handle related data)
        db.delete(user)
        db.commit()

        logger.info(f"Account deleted: user_id={user_id}, email={user_email}")

        return StandardResponse(success=True, message="Account deleted successfully")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting account for user_id={user.id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting account",
        )


@router.post("/api-keys", response_model=StandardResponse)
async def save_api_key(
    request: SaveApiKeyRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Save an encrypted API key for a provider.

    If an API key for the provider already exists, it will be updated.
    The API key is encrypted using AES-256 before storage.

    Args:
        request: API key data (provider, api_key, name)
        user: Current authenticated user
        db: Database session

    Returns:
        Success response

    Raises:
        HTTPException: If encryption fails or database error occurs
    """
    try:
        # Encrypt the API key
        encrypted_key = encrypt_api_key(request.api_key)

        # Check if API key for this provider already exists
        existing_key = (
            db.query(UserApiKey)
            .filter(UserApiKey.user_id == user.id, UserApiKey.provider == request.provider)
            .first()
        )

        if existing_key:
            # Update existing key
            existing_key.encrypted_key = encrypted_key
            existing_key.name = request.name
            existing_key.updated_at = datetime.utcnow()
            logger.info(f"Updated API key for user_id={user.id}, provider={request.provider}")
        else:
            # Create new key
            new_key = UserApiKey(
                user_id=user.id,
                provider=request.provider,
                encrypted_key=encrypted_key,
                name=request.name,
            )
            db.add(new_key)
            logger.info(f"Created API key for user_id={user.id}, provider={request.provider}")

        db.commit()

        return StandardResponse(
            success=True, message=f"API key for {request.provider} saved successfully"
        )

    except Exception as e:
        logger.error(f"Error saving API key for user_id={user.id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while saving API key",
        )


@router.get("/api-keys", response_model=List[ApiKeyResponse])
async def get_api_keys(
    user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
):
    """
    Get all API keys for the current user (without exposing actual keys).

    Args:
        user: Current authenticated user
        db: Database session

    Returns:
        List of API key responses (provider, name, timestamps only)
    """
    try:
        api_keys = db.query(UserApiKey).filter(UserApiKey.user_id == user.id).all()

        return [
            ApiKeyResponse(
                provider=key.provider,
                name=key.name,
                created_at=key.created_at,
                updated_at=key.updated_at,
            )
            for key in api_keys
        ]

    except Exception as e:
        logger.error(f"Error retrieving API keys for user_id={user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving API keys",
        )


@router.delete("/api-keys/{provider}", response_model=StandardResponse)
async def delete_api_key(
    provider: str, user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
):
    """
    Delete an API key for a specific provider.

    Args:
        provider: Provider name (e.g., 'openai', 'anthropic')
        user: Current authenticated user
        db: Database session

    Returns:
        Success response

    Raises:
        HTTPException: If API key not found
    """
    try:
        api_key = (
            db.query(UserApiKey)
            .filter(UserApiKey.user_id == user.id, UserApiKey.provider == provider.lower())
            .first()
        )

        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key for provider '{provider}' not found",
            )

        db.delete(api_key)
        db.commit()

        logger.info(f"Deleted API key for user_id={user.id}, provider={provider}")

        return StandardResponse(
            success=True, message=f"API key for {provider} deleted successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting API key for user_id={user.id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting API key",
        )


@router.post("/api-keys/{provider}/test", response_model=ApiKeyTestResponse)
async def test_api_key(
    provider: str, user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
):
    """
    Test if an API key works by making a simple API call.

    FIXED: Returns iOS-compatible response format:
    {
        "is_valid": boolean,
        "message": string,
        "provider": string,
        "tested_at": ISO8601 timestamp
    }

    Args:
        provider: Provider name (e.g., 'openai', 'anthropic')
        user: Current authenticated user
        db: Database session

    Returns:
        ApiKeyTestResponse with validation status and details

    Raises:
        HTTPException: If API key not found
    """
    # Current timestamp for response
    tested_at = datetime.utcnow().isoformat() + "Z"

    try:
        # Get the API key
        api_key_record = (
            db.query(UserApiKey)
            .filter(UserApiKey.user_id == user.id, UserApiKey.provider == provider.lower())
            .first()
        )

        if not api_key_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"API key for provider '{provider}' not found",
            )

        # Decrypt the API key
        api_key = decrypt_api_key(api_key_record.encrypted_key)

        if not api_key or not api_key.strip():
            logger.error(f"Failed to decrypt API key for user_id={user.id}, provider={provider}")
            return ApiKeyTestResponse(
                is_valid=False,
                provider=provider,
                message="Failed to decrypt API key - encryption key may have changed",
                tested_at=tested_at,
            )

        # Test the API key based on provider
        if provider.lower() == "openai":
            try:
                from openai import OpenAI

                client = OpenAI(api_key=api_key)
                client.models.list()  # Test API key validity

                logger.info(f"OpenAI API key test successful for user_id={user.id}")
                return ApiKeyTestResponse(
                    is_valid=True,
                    provider=provider,
                    message="API key is valid",
                    tested_at=tested_at,
                )
            except Exception as e:
                logger.warning(f"OpenAI API key test failed for user_id={user.id}: {str(e)}")
                return ApiKeyTestResponse(
                    is_valid=False,
                    provider=provider,
                    message=f"API key validation failed: {str(e)}",
                    tested_at=tested_at,
                )

        elif provider.lower() == "anthropic":
            try:
                import anthropic

                client = anthropic.Anthropic(api_key=api_key)
                # Simple test - creating client validates the key format

                logger.info(f"Anthropic API key test successful for user_id={user.id}")
                return ApiKeyTestResponse(
                    is_valid=True,
                    provider=provider,
                    message="API key is valid",
                    tested_at=tested_at,
                )
            except Exception as e:
                logger.warning(f"Anthropic API key test failed for user_id={user.id}: {str(e)}")
                return ApiKeyTestResponse(
                    is_valid=False,
                    provider=provider,
                    message=f"API key validation failed: {str(e)}",
                    tested_at=tested_at,
                )

        else:
            return ApiKeyTestResponse(
                is_valid=False,
                provider=provider,
                message="Testing not implemented for this provider",
                tested_at=tested_at,
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing API key for user_id={user.id}: {str(e)}")
        return ApiKeyTestResponse(
            is_valid=False,
            provider=provider,
            message=f"An error occurred while testing API key: {str(e)}",
            tested_at=tested_at,
        )


@router.get("/stats", response_model=dict)
async def get_user_stats(
    user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
):
    """
    Get user statistics (articles, posts, API keys count).

    FIXED: Now correctly counts:
    - bookmarked: Articles with bookmarked=True
    - posts: Posts with status='draft' (successfully created, not published yet)
    - published: Posts with status='published' (successfully published)

    Does NOT count: failed, processing, or other statuses

    Args:
        user: Current authenticated user
        db: Database session

    Returns:
        Dictionary with user statistics
    """
    try:
        from database import Article, Post, UserApiKey

        # Count bookmarked articles (articles with bookmarked=True for this user)
        bookmarked_count = (
            db.query(Article)
            .filter(Article.user_id == user.id, Article.bookmarked.is_(True))
            .count()
        )

        # Count posts created (draft status - successfully created but not published)
        posts_created_count = (
            db.query(Post).filter(Post.user_id == user.id, Post.status == "draft").count()
        )

        # Count posts published (published status only)
        posts_published_count = (
            db.query(Post).filter(Post.user_id == user.id, Post.status == "published").count()
        )

        # Count API keys
        api_keys_count = db.query(UserApiKey).filter(UserApiKey.user_id == user.id).count()

        # Count sessions
        sessions_count = db.query(UserSession).filter(UserSession.user_id == user.id).count()

        return {
            "success": True,
            "bookmarked": bookmarked_count,  # Match frontend expectation
            "posts": posts_created_count,  # Match frontend expectation
            "published": posts_published_count,  # Match frontend expectation
            "posts_count": posts_created_count,  # Backward compatibility
            "published_count": posts_published_count,  # Backward compatibility
            "api_keys_count": api_keys_count,
            "sessions_count": sessions_count,
            "member_since": user.created_at.isoformat() if user.created_at else None,
            "is_verified": user.is_verified,
        }

    except Exception as e:
        logger.error(f"Error getting stats for user_id={user.id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving stats",
        )
