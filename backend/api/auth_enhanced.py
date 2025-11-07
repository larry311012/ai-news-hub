"""
Enhanced API endpoint with validation
Add this to the existing auth.py file
"""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
import logging

# Import from project modules
from database import get_db, User, UserApiKey
from utils.auth_selector import get_current_user as get_current_user_dependency
from utils.encryption import encrypt_api_key, decrypt_api_key
from utils.api_key_validator import (
    validate_api_key,
    sanitize_api_key,
    detect_potential_corruption,
    mask_api_key
)

# Initialize router and logger
router = APIRouter()
logger = logging.getLogger(__name__)


# Pydantic models
class SaveApiKeyRequest(BaseModel):
    """Request model for saving API keys"""
    provider: str
    api_key: str
    name: Optional[str] = None


class StandardResponse(BaseModel):
    """Standard API response model"""
    success: bool
    message: str


# Replace the save_api_key function with this enhanced version:

@router.post("/api-keys", response_model=StandardResponse)
async def save_api_key(
    request: SaveApiKeyRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
) -> StandardResponse:
    """
    Save an encrypted API key for a provider.

    Enhanced with validation to prevent corruption:
    - Validates API key format before storage
    - Sanitizes input (removes whitespace, newlines)
    - Detects potential corruption
    - Provides clear error messages

    If an API key for the provider already exists, it will be updated.
    The API key is encrypted using AES-256 before storage.

    Args:
        request: API key data (provider, api_key, name)
        user: Current authenticated user
        db: Database session

    Returns:
        Success response with masked key preview

    Raises:
        HTTPException: If validation fails, encryption fails, or database error occurs
    """
    try:
        # Step 1: Sanitize the API key (remove whitespace, newlines, etc.)
        sanitized_key = sanitize_api_key(request.api_key)

        if not sanitized_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="API key cannot be empty after sanitization"
            )

        # Step 2: Detect potential corruption
        is_corrupted, corruption_desc = detect_potential_corruption(sanitized_key)
        if is_corrupted:
            logger.warning(
                f"Corrupted API key detected for user_id={user.id}, "
                f"provider={request.provider}: {corruption_desc}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"API key appears corrupted: {corruption_desc}. "
                       f"Please verify you copied the entire key correctly."
            )

        # Step 3: Validate API key format
        is_valid, error_message = validate_api_key(request.provider, sanitized_key)

        if not is_valid:
            logger.warning(
                f"Invalid API key format for user_id={user.id}, "
                f"provider={request.provider}: {error_message}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid API key format: {error_message}"
            )

        # Step 4: Encrypt the validated API key
        try:
            encrypted_key = encrypt_api_key(sanitized_key)
        except Exception as e:
            logger.error(f"Encryption failed for user_id={user.id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to encrypt API key. Please try again."
            )

        # Step 5: Test decryption to ensure roundtrip works
        try:
            decrypted_test = decrypt_api_key(encrypted_key)
            if decrypted_test != sanitized_key:
                logger.error(
                    f"Encryption roundtrip failed for user_id={user.id}. "
                    f"Expected: {mask_api_key(sanitized_key)}, "
                    f"Got: {mask_api_key(decrypted_test) if decrypted_test else 'None'}"
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Encryption integrity check failed. Please contact support."
                )
        except Exception as e:
            logger.error(f"Decryption test failed for user_id={user.id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to verify encrypted key. Please try again."
            )

        # Step 6: Store in database
        existing_key = db.query(UserApiKey).filter(
            UserApiKey.user_id == user.id,
            UserApiKey.provider == request.provider
        ).first()

        if existing_key:
            # Update existing key
            existing_key.encrypted_key = encrypted_key  # type: ignore[assignment]
            existing_key.name = request.name  # type: ignore[assignment]
            existing_key.updated_at = datetime.utcnow()  # type: ignore[assignment]
            logger.info(
                f"Updated API key for user_id={user.id}, provider={request.provider}, "
                f"masked_key={mask_api_key(sanitized_key)}"
            )
            action = "updated"
        else:
            # Create new key
            new_key = UserApiKey(
                user_id=user.id,
                provider=request.provider,
                encrypted_key=encrypted_key,
                name=request.name
            )
            db.add(new_key)
            logger.info(
                f"Created API key for user_id={user.id}, provider={request.provider}, "
                f"masked_key={mask_api_key(sanitized_key)}"
            )
            action = "saved"

        db.commit()

        return StandardResponse(
            success=True,
            message=f"API key for {request.provider} {action} successfully. "
                    f"Preview: {mask_api_key(sanitized_key)}"
        )

    except HTTPException:
        # Re-raise HTTP exceptions (already formatted)
        raise

    except ValueError as e:
        # Validation errors
        logger.error(f"Validation error saving API key: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error saving API key for user_id={user.id}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while saving API key. Please try again."
        )
