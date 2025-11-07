"""
Settings API endpoints - User-specific settings
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from cryptography.fernet import Fernet
import os

from database import get_db, Settings, User
from utils.auth_selector import get_current_user as get_current_user_dependency

router = APIRouter()

# Encryption key (in production, store securely in env)
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
cipher_suite = Fernet(ENCRYPTION_KEY.encode())


# Pydantic models
class SettingRequest(BaseModel):
    key: str
    value: str
    encrypted: bool = False


class SettingResponse(BaseModel):
    key: str
    value: str
    encrypted: bool

    class Config:
        from_attributes = True


@router.get("", response_model=List[SettingResponse])
async def get_settings(
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Get all settings for the authenticated user (decrypted)

    This endpoint requires authentication and returns only the settings
    for the current user.

    Returns:
        List of user settings with decrypted values
    """
    # Query settings for this specific user
    settings = db.query(Settings).filter(Settings.user_id == user.id).all()

    result = []
    for setting in settings:
        value = setting.value
        if setting.encrypted:
            try:
                value = cipher_suite.decrypt(value.encode()).decode()
            except Exception:
                value = "***ENCRYPTED***"

        result.append({"key": setting.key, "value": value, "encrypted": setting.encrypted})

    return result


@router.get("/{key}")
async def get_setting(
    key: str,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Get a specific setting for the authenticated user

    Args:
        key: Setting key to retrieve

    Returns:
        Setting object with decrypted value

    Raises:
        HTTPException: 404 if setting not found
    """
    setting = db.query(Settings).filter(
        Settings.user_id == user.id,
        Settings.key == key
    ).first()

    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    value = setting.value
    if setting.encrypted:
        try:
            value = cipher_suite.decrypt(value.encode()).decode()
        except Exception:
            raise HTTPException(status_code=500, detail="Failed to decrypt setting")

    return {"key": setting.key, "value": value, "encrypted": setting.encrypted}


@router.post("")
async def create_or_update_setting(
    request: SettingRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Create or update a setting for the authenticated user

    Args:
        request: Setting data (key, value, encrypted flag)

    Returns:
        Success response with setting key
    """
    # Check if setting exists for this user
    setting = db.query(Settings).filter(
        Settings.user_id == user.id,
        Settings.key == request.key
    ).first()

    # Encrypt if needed
    value = request.value
    if request.encrypted:
        try:
            value = cipher_suite.encrypt(value.encode()).decode()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to encrypt setting: {str(e)}")

    if setting:
        # Update existing setting
        setting.value = value
        setting.encrypted = request.encrypted
    else:
        # Create new setting for this user
        setting = Settings(
            user_id=user.id,
            key=request.key,
            value=value,
            encrypted=request.encrypted
        )
        db.add(setting)

    try:
        db.commit()
        return {"success": True, "key": request.key}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save setting: {str(e)}")


@router.delete("/{key}")
async def delete_setting(
    key: str,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Delete a setting for the authenticated user

    Args:
        key: Setting key to delete

    Returns:
        Success response

    Raises:
        HTTPException: 404 if setting not found
    """
    setting = db.query(Settings).filter(
        Settings.user_id == user.id,
        Settings.key == key
    ).first()

    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    try:
        db.delete(setting)
        db.commit()
        return {"success": True}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete setting: {str(e)}")


@router.post("/validate-api-key")
async def validate_api_key(
    provider: str,
    api_key: str,
    user: User = Depends(get_current_user_dependency)
):
    """
    Validate an API key

    This endpoint requires authentication to prevent abuse.

    Args:
        provider: API provider (openai, anthropic, deepseek)
        api_key: API key to validate

    Returns:
        Validation result
    """
    try:
        if provider == "openai":
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            # Try a simple request
            client.models.list()
            return {"valid": True, "provider": provider}

        elif provider == "anthropic":
            from anthropic import Anthropic

            client = Anthropic(api_key=api_key)
            # Try a simple request
            client.models.list()
            return {"valid": True, "provider": provider}

        elif provider == "deepseek":
            # Import DeepSeek validation function
            from utils.deepseek_client import validate_deepseek_api_key

            is_valid, error_message = validate_deepseek_api_key(api_key, timeout=10.0)

            if is_valid:
                return {"valid": True, "provider": provider}
            else:
                return {"valid": False, "error": error_message}

        else:
            return {"valid": False, "error": "Unknown provider"}

    except Exception as e:
        return {"valid": False, "error": str(e)}
