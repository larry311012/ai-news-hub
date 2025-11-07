"""
Database Optimization Script

Creates indexes and optimizes database schema for production performance.

Run this script to add performance-critical indexes:
    python database_optimization.py

Indexes added:
- Posts: user_id, created_at, status
- Instagram Images: post_id, user_id, prompt_hash, status
- Image Generation Quota: user_id, quota_reset_date
- Articles: user_id, published, fetched_at
- Social Media Connections: user_id, platform, status
- Sessions: user_id, expires_at, last_activity
"""
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError
import os
from loguru import logger


def get_database_engine():
    """Get database engine"""
    database_url = os.getenv("DATABASE_URL", "sqlite:///./ai_news.db")
    return create_engine(database_url)


def index_exists(engine, table_name: str, index_name: str) -> bool:
    """Check if index already exists"""
    inspector = inspect(engine)

    try:
        indexes = inspector.get_indexes(table_name)
        return any(idx['name'] == index_name for idx in indexes)
    except Exception:
        return False


def create_index_safe(engine, index_sql: str, index_name: str, table_name: str):
    """Create index if it doesn't exist"""
    if index_exists(engine, table_name, index_name):
        logger.info(f"  ✓ Index {index_name} already exists")
        return True

    try:
        with engine.connect() as conn:
            conn.execute(text(index_sql))
            conn.commit()
        logger.info(f"  ✓ Created index: {index_name}")
        return True
    except OperationalError as e:
        if "already exists" in str(e).lower():
            logger.info(f"  ✓ Index {index_name} already exists")
            return True
        else:
            logger.error(f"  ✗ Failed to create index {index_name}: {e}")
            return False
    except Exception as e:
        logger.error(f"  ✗ Failed to create index {index_name}: {e}")
        return False


def optimize_database():
    """
    Apply database optimizations

    Creates indexes on frequently queried columns to improve performance.
    """
    logger.info("Starting database optimization...")

    engine = get_database_engine()

    # Track results
    indexes_created = 0
    indexes_failed = 0

    # ========================================================================
    # POSTS TABLE OPTIMIZATION
    # ========================================================================
    logger.info("\n1. Optimizing posts table...")

    post_indexes = [
        (
            "CREATE INDEX IF NOT EXISTS idx_posts_user_id_created ON posts(user_id, created_at DESC)",
            "idx_posts_user_id_created",
            "posts",
            "User's posts ordered by creation date (fast post listings)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status)",
            "idx_posts_status",
            "posts",
            "Filter posts by status (draft, published, failed)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC)",
            "idx_posts_created_at",
            "posts",
            "Order posts by creation date"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_posts_user_status ON posts(user_id, status)",
            "idx_posts_user_status",
            "posts",
            "User's posts filtered by status"
        )
    ]

    for sql, name, table, description in post_indexes:
        logger.info(f"  Creating {name}: {description}")
        if create_index_safe(engine, sql, name, table):
            indexes_created += 1
        else:
            indexes_failed += 1

    # ========================================================================
    # INSTAGRAM IMAGES TABLE OPTIMIZATION
    # ========================================================================
    logger.info("\n2. Optimizing instagram_images table...")

    image_indexes = [
        (
            "CREATE INDEX IF NOT EXISTS idx_instagram_images_post_id ON instagram_images(post_id)",
            "idx_instagram_images_post_id",
            "instagram_images",
            "Find images by post ID (fast image retrieval)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_instagram_images_user_id ON instagram_images(user_id)",
            "idx_instagram_images_user_id",
            "instagram_images",
            "Find user's images"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_instagram_images_prompt_hash ON instagram_images(prompt_hash)",
            "idx_instagram_images_prompt_hash",
            "instagram_images",
            "Fast prompt cache lookups (60-75% cost savings)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_instagram_images_status ON instagram_images(status)",
            "idx_instagram_images_status",
            "instagram_images",
            "Filter images by status (active, deleted)"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_instagram_images_created ON instagram_images(created_at DESC)",
            "idx_instagram_images_created",
            "instagram_images",
            "Recent images lookup"
        )
    ]

    for sql, name, table, description in image_indexes:
        logger.info(f"  Creating {name}: {description}")
        if create_index_safe(engine, sql, name, table):
            indexes_created += 1
        else:
            indexes_failed += 1

    # ========================================================================
    # IMAGE GENERATION QUOTA TABLE OPTIMIZATION
    # ========================================================================
    logger.info("\n3. Optimizing image_generation_quota table...")

    quota_indexes = [
        (
            "CREATE INDEX IF NOT EXISTS idx_quota_user_date ON image_generation_quota(user_id, quota_reset_date)",
            "idx_quota_user_date",
            "image_generation_quota",
            "Fast quota checks (used on every image generation)"
        )
    ]

    for sql, name, table, description in quota_indexes:
        logger.info(f"  Creating {name}: {description}")
        if create_index_safe(engine, sql, name, table):
            indexes_created += 1
        else:
            indexes_failed += 1

    # ========================================================================
    # ARTICLES TABLE OPTIMIZATION
    # ========================================================================
    logger.info("\n4. Optimizing articles table...")

    article_indexes = [
        (
            "CREATE INDEX IF NOT EXISTS idx_articles_user_id ON articles(user_id)",
            "idx_articles_user_id",
            "articles",
            "User's articles"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published DESC)",
            "idx_articles_published",
            "articles",
            "Recent articles ordering"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_articles_fetched ON articles(fetched_at DESC)",
            "idx_articles_fetched",
            "articles",
            "Recently fetched articles"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category)",
            "idx_articles_category",
            "articles",
            "Filter by category"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_articles_bookmarked ON articles(user_id, bookmarked)",
            "idx_articles_bookmarked",
            "articles",
            "User's bookmarked articles"
        )
    ]

    for sql, name, table, description in article_indexes:
        logger.info(f"  Creating {name}: {description}")
        if create_index_safe(engine, sql, name, table):
            indexes_created += 1
        else:
            indexes_failed += 1

    # ========================================================================
    # SESSIONS TABLE OPTIMIZATION
    # ========================================================================
    logger.info("\n5. Optimizing sessions table...")

    session_indexes = [
        (
            "CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at)",
            "idx_sessions_expires_at",
            "sessions",
            "Fast expired session cleanup"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_sessions_last_activity ON sessions(last_activity DESC)",
            "idx_sessions_last_activity",
            "sessions",
            "Active sessions tracking"
        )
    ]

    for sql, name, table, description in session_indexes:
        logger.info(f"  Creating {name}: {description}")
        if create_index_safe(engine, sql, name, table):
            indexes_created += 1
        else:
            indexes_failed += 1

    # ========================================================================
    # SOCIAL MEDIA CONNECTIONS TABLE OPTIMIZATION
    # ========================================================================
    logger.info("\n6. Optimizing social_media_connections table...")

    social_indexes = [
        (
            "CREATE INDEX IF NOT EXISTS idx_social_connections_user_platform ON social_media_connections(user_id, platform)",
            "idx_social_connections_user_platform",
            "social_media_connections",
            "Fast connection lookups by user and platform"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_social_connections_status ON social_media_connections(status)",
            "idx_social_connections_status",
            "social_media_connections",
            "Filter by connection status"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_social_connections_expires ON social_media_connections(token_expires_at)",
            "idx_social_connections_expires",
            "social_media_connections",
            "Find expiring tokens for refresh"
        )
    ]

    for sql, name, table, description in social_indexes:
        logger.info(f"  Creating {name}: {description}")
        if create_index_safe(engine, sql, name, table):
            indexes_created += 1
        else:
            indexes_failed += 1

    # ========================================================================
    # LOGIN ACTIVITY TABLE OPTIMIZATION
    # ========================================================================
    logger.info("\n7. Optimizing login_activity table...")

    activity_indexes = [
        (
            "CREATE INDEX IF NOT EXISTS idx_login_activity_user_created ON login_activity(user_id, created_at DESC)",
            "idx_login_activity_user_created",
            "login_activity",
            "User's recent login history"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_login_activity_action ON login_activity(action)",
            "idx_login_activity_action",
            "login_activity",
            "Filter by action type"
        )
    ]

    for sql, name, table, description in activity_indexes:
        logger.info(f"  Creating {name}: {description}")
        if create_index_safe(engine, sql, name, table):
            indexes_created += 1
        else:
            indexes_failed += 1

    # ========================================================================
    # SECURITY AUDIT TABLE OPTIMIZATION
    # ========================================================================
    logger.info("\n8. Optimizing security_audit table...")

    audit_indexes = [
        (
            "CREATE INDEX IF NOT EXISTS idx_security_audit_user_created ON security_audit(user_id, created_at DESC)",
            "idx_security_audit_user_created",
            "security_audit",
            "User's security events"
        ),
        (
            "CREATE INDEX IF NOT EXISTS idx_security_audit_risk_level ON security_audit(risk_level, created_at DESC)",
            "idx_security_audit_risk_level",
            "security_audit",
            "High-risk events monitoring"
        )
    ]

    for sql, name, table, description in audit_indexes:
        logger.info(f"  Creating {name}: {description}")
        if create_index_safe(engine, sql, name, table):
            indexes_created += 1
        else:
            indexes_failed += 1

    # ========================================================================
    # SUMMARY
    # ========================================================================
    logger.info("\n" + "=" * 70)
    logger.info("DATABASE OPTIMIZATION COMPLETE")
    logger.info("=" * 70)
    logger.info(f"✓ Indexes created: {indexes_created}")
    logger.info(f"✗ Indexes failed: {indexes_failed}")
    logger.info("=" * 70)

    if indexes_failed == 0:
        logger.info("\n✓ All optimizations applied successfully!")
    else:
        logger.warning(f"\n⚠ {indexes_failed} index(es) failed to create. Check logs for details.")

    return indexes_created, indexes_failed


def analyze_query_performance():
    """
    Analyze query performance (SQLite EXPLAIN QUERY PLAN)

    Useful for debugging slow queries
    """
    logger.info("\nAnalyzing common query patterns...")

    engine = get_database_engine()

    queries = [
        ("Get user's recent posts", "SELECT * FROM posts WHERE user_id = 1 ORDER BY created_at DESC LIMIT 10"),
        ("Get post by ID", "SELECT * FROM posts WHERE id = 1 AND user_id = 1"),
        ("Check image cache", "SELECT * FROM instagram_images WHERE prompt_hash = 'abc123' AND status = 'active'"),
        ("Get user quota", "SELECT * FROM image_generation_quota WHERE user_id = 1"),
        ("Get active sessions", "SELECT * FROM sessions WHERE user_id = 1 AND expires_at > datetime('now')")
    ]

    for name, query in queries:
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f"EXPLAIN QUERY PLAN {query}"))
                plan = result.fetchall()

            logger.info(f"\n{name}:")
            for row in plan:
                logger.info(f"  {row}")

        except Exception as e:
            logger.error(f"Failed to analyze query '{name}': {e}")


if __name__ == "__main__":
    # Run optimization
    optimize_database()

    # Analyze performance (optional)
    # analyze_query_performance()
