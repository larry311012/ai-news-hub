# API module - Import all routers

from . import (
    articles,
    posts,
    posts_v2,  # Enhanced post generation API with comprehensive features
    settings,
    auth,
    oauth,
    oauth_mock,
    auth_phase3,
    auth_phase4,
    security,
    ab_testing,
    analytics,
    ai_chat,
    social_media,
    social_media_twitter_oauth1,
    social_media_twitter_per_user,
    social_media_threads,  # Threads OAuth 2.0
    admin_oauth_credentials,
    user_oauth_setup,
)

__all__ = [
    "articles",
    "posts",
    "posts_v2",
    "settings",
    "auth",
    "oauth",
    "oauth_mock",
    "auth_phase3",
    "auth_phase4",
    "security",
    "ab_testing",
    "analytics",
    "ai_chat",
    "social_media",
    "social_media_twitter_oauth1",
    "social_media_twitter_per_user",
    "social_media_threads",  # Threads OAuth 2.0
    "admin_oauth_credentials",
    "user_oauth_setup",
]
