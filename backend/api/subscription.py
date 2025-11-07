"""
Subscription and User Tier Management API

Endpoints for checking quota and managing user tiers.
NO PAYMENT PROCESSING - This is a self-hosted open-source tool.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import logging

from database import get_db, User, AdminSettings
from utils.auth_selector import get_current_user as get_current_user_dependency
from middleware.quota_checker import QuotaManager, get_quota_info

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class QuotaResponse(BaseModel):
    """User quota information response"""

    tier: str
    limit: int
    used: int
    remaining: int
    reset_at: Optional[str]
    can_publish: bool

    class Config:
        from_attributes = True


class TierInfoResponse(BaseModel):
    """User tier details response"""

    current_tier: str
    tier_name: str
    quota_limit: int
    can_publish: bool
    benefits: list[str]
    limitations: list[str]

    class Config:
        from_attributes = True


# ============================================================================
# QUOTA ENDPOINTS
# ============================================================================


@router.get("/quota", response_model=QuotaResponse)
async def get_user_quota(
    user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
):
    """
    Get current user's quota information

    Returns:
        Quota details including usage, limits, and reset time
    """
    quota_manager = QuotaManager(db)
    has_quota, quota_info = quota_manager.check_quota(user)

    return QuotaResponse(
        tier=user.user_tier,
        limit=quota_info["limit"],
        used=quota_info["used"],
        remaining=quota_info["remaining"],
        reset_at=quota_info["reset_at"],
        can_publish=quota_manager.can_publish(user),
    )


@router.get("/tier", response_model=TierInfoResponse)
async def get_user_tier(
    user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
):
    """
    Get current user's tier information with benefits and limitations

    Returns:
        Tier details including current tier, benefits, and quota
    """
    quota_manager = QuotaManager(db)
    quota_limit = quota_manager.get_quota_limit(user.user_tier)

    # Define tier benefits and limitations
    tier_info = {
        "guest": {
            "name": "Guest",
            "benefits": [
                "Preview 1 post generation",
                "No account required",
            ],
            "limitations": [
                "Cannot publish posts",
                "Limited to 1 post preview",
                "No access to multi-platform publishing",
            ],
        },
        "free": {
            "name": "Free",
            "benefits": [
                "Unlimited post generations",
                "Publish to all platforms",
                "Multi-platform optimization",
                "AI-powered content generation",
                "Full feature access",
            ],
            "limitations": [
                "None - This is open source!",
            ],
        },
        "paid": {
            "name": "Premium (Legacy)",
            "benefits": [
                "Unlimited post generations",
                "Full feature access",
                "All platforms supported",
            ],
            "limitations": [
                "None - Payment no longer required",
            ],
        },
    }

    tier_data = tier_info.get(user.user_tier, tier_info["free"])

    return TierInfoResponse(
        current_tier=user.user_tier,
        tier_name=tier_data["name"],
        quota_limit=quota_limit,
        can_publish=quota_manager.can_publish(user),
        benefits=tier_data["benefits"],
        limitations=tier_data["limitations"],
    )


@router.get("/available-tiers")
async def get_available_tiers():
    """
    Get list of available tiers

    Returns:
        List of tier options with features (NO PAYMENT - all free)
    """
    tiers = [
        {
            "tier": "free",
            "name": "Free",
            "price": "$0 - Open Source",
            "quota": "Unlimited",
            "features": [
                "AI-powered content generation",
                "Multi-platform publishing",
                "Twitter, LinkedIn, Instagram, Threads",
                "Unlimited posts per day",
                "Full feature access",
                "Self-hosted deployment",
            ],
            "popular": True,
        },
    ]

    return {
        "tiers": tiers,
        "billing_info": "This is an open-source self-hosted tool. No payment required!",
        "note": "All features are available to all users. Enjoy!",
    }


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================


@router.post("/admin/set-quota-limit")
async def set_tier_quota_limit(
    tier: str,
    limit: int,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    """
    Admin endpoint to set quota limit for a tier

    Args:
        tier: User tier (guest, free, paid)
        limit: New quota limit

    Returns:
        Success response

    Raises:
        HTTPException: If user is not admin
    """
    # Check admin privileges
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    # Validate inputs
    if tier not in ["guest", "free", "paid"]:
        raise HTTPException(
            status_code=400, detail="Invalid tier. Must be 'guest', 'free', or 'paid'."
        )

    if limit < 0:
        raise HTTPException(status_code=400, detail="Quota limit must be positive")

    # Update or create admin setting
    setting_key = f"{tier}_quota_limit"
    setting = db.query(AdminSettings).filter(AdminSettings.key == setting_key).first()

    if setting:
        setting.value = str(limit)
    else:
        setting = AdminSettings(
            key=setting_key,
            value=str(limit),
            encrypted=False,
            description=f"Daily quota limit for {tier} tier users",
        )
        db.add(setting)

    db.commit()

    logger.info(f"Admin {user.id} set {tier} tier quota limit to {limit}")

    return {
        "success": True,
        "message": f"Quota limit for {tier} tier set to {limit}",
        "tier": tier,
        "new_limit": limit,
    }


@router.get("/admin/quota-limits")
async def get_all_quota_limits(
    user: User = Depends(get_current_user_dependency), db: Session = Depends(get_db)
):
    """
    Admin endpoint to get all tier quota limits

    Returns:
        Dict of tier quota limits

    Raises:
        HTTPException: If user is not admin
    """
    # Check admin privileges
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin privileges required")

    quota_manager = QuotaManager(db)

    limits = {
        "guest": quota_manager.get_quota_limit("guest"),
        "free": quota_manager.get_quota_limit("free"),
        "paid": quota_manager.get_quota_limit("paid"),
    }

    return {
        "quota_limits": limits,
        "default_limits": quota_manager.DEFAULT_QUOTAS,
        "note": "This is an open-source tool. Consider setting unlimited quotas (999999) for free tier.",
    }
