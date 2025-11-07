"""
Patch Script for Phase 4 Integration

This script updates main.py to include:
1. Publishing API import
2. Publishing database tables initialization
3. Publishing API router registration
"""
import re


def apply_phase4_patch():
    """Apply Phase 4 updates to main.py"""

    main_file_path = "/Users/ranhui/ai_post/web/backend/main.py"

    with open(main_file_path, "r") as f:
        content = f.read()

    # 1. Add publishing_api import after feed_aggregator_api
    if "publishing_api" not in content:
        import_section = """from api import (
    subscription,  # User tier and quota management (NO PAYMENT)
    articles,
    posts,
    posts_v2,
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
    social_media_threads,
    social_media_instagram,  # NEW: Instagram OAuth
    admin_oauth_credentials,
    user_oauth_setup,
    social_media_twitter_per_user,
    instagram_images,
    posts_instagram_publish,  # NEW: Instagram publishing
    setup_guide,  # NEW: Setup guide for social media
    health,  # NEW: Comprehensive health check endpoints
    user_feeds,  # NEW: RSS feed management
    mobile_v1,  # NEW: Mobile API v1 for iOS app
    feeds_enhanced,  # NEW: Enhanced RSS feeds for iOS (Task 2.6)
    feed_aggregator_api,  # NEW: Feed aggregator service (Task 2.7)
    publishing_api,  # NEW: Phase 4 - Multi-platform publishing API
)"""

        # Find and replace the import section
        pattern = r"from api import \([^)]+\)"
        content = re.sub(pattern, import_section, content, flags=re.DOTALL)

    # 2. Add publishing table initialization in lifespan
    if "PostPublishingHistory" not in content:
        init_section = """    # Initialize social media tables
    SocialMediaConnection.__table__.create(engine, checkfirst=True)

    # Initialize Phase 4 publishing tables
    from database_publishing import (
        PostPublishingHistory,
        PublishingQueue,
        PublishingRateLimit,
        PublishingWebhook
    )

    PostPublishingHistory.__table__.create(engine, checkfirst=True)
    PublishingQueue.__table__.create(engine, checkfirst=True)
    PublishingRateLimit.__table__.create(engine, checkfirst=True)
    PublishingWebhook.__table__.create(engine, checkfirst=True)

    # Initialize setup guide tables"""

        # Replace the social media table init section
        pattern = r"    # Initialize social media tables\s+SocialMediaConnection\.__table__\.create\(engine, checkfirst=True\)\s+# Initialize setup guide tables"
        content = re.sub(pattern, init_section, content)

    # 3. Add publishing API router registration
    if "publishing_api.router" not in content:
        router_section = """# Feed Aggregator Service API (Task 2.7 - Background article aggregation)
app.include_router(feed_aggregator_api.router, prefix="/api", tags=["feed-aggregator"])

# Phase 4: Publishing API (Multi-platform social media publishing)
app.include_router(publishing_api.router, prefix="/api/publishing", tags=["publishing"])

# Authentication APIs"""

        pattern = r"# Feed Aggregator Service API \(Task 2\.7[^)]*\)\s+app\.include_router\(feed_aggregator_api\.router[^)]+\)\s+# Authentication APIs"
        content = re.sub(pattern, router_section, content)

    # 4. Update version and description
    content = content.replace('version="2.13.0"', 'version="2.14.0"')
    content = content.replace(
        'description="API for managing AI news and social media posts with RSS feed management, background aggregation, Redis caching, Sentry error tracking, and iOS mobile support"',
        'description="API for managing AI news and social media posts with RSS feed management, background aggregation, multi-platform publishing, Redis caching, Sentry error tracking, and iOS mobile support"'
    )

    # 5. Update feature list in /api endpoint
    if "multi_platform_publishing" not in content:
        features_addition = """            "Background Feed Aggregation (Task 2.7)",
            "Feed Health Monitoring",
            "Automatic Article Deduplication",
            "Rate Limiting & Exponential Backoff",
            "Multi-Platform Publishing (Phase 4)",
            "Publishing Status Tracking",
            "Automatic Retry Mechanism",
            "Publishing History",
            "LinkedIn OAuth 2.0 (Per-User Credentials)","""

        pattern = r'"Background Feed Aggregation \(Task 2\.7\)",\s+"Feed Health Monitoring",\s+"Automatic Article Deduplication",\s+"Rate Limiting & Exponential Backoff",\s+"LinkedIn OAuth 2\.0 \(Per-User Credentials\)",'
        content = re.sub(pattern, features_addition, content)

    # Write updated content
    with open(main_file_path, "w") as f:
        f.write(content)

    print("Phase 4 patch applied successfully!")
    print("Updated:")
    print("  - Added publishing_api import")
    print("  - Added publishing database tables initialization")
    print("  - Added publishing API router registration")
    print("  - Updated version to 2.14.0")
    print("  - Updated API description and features")


if __name__ == "__main__":
    apply_phase4_patch()
