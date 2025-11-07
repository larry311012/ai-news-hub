"""
Migration script for Twitter OAuth 1.0a Complete Implementation

This script creates database tables for the enhanced Twitter OAuth implementation:
- TwitterOAuthRequestToken: Temporary request token storage
- TwitterOAuthState: OAuth flow tracking and CSRF protection
- TwitterWebhook: Twitter webhook event storage
- TwitterRateLimitLog: API rate limit tracking
- TwitterOAuthAudit: OAuth operation audit log

Run this script to migrate your database:
    python migrate_twitter_oauth_complete.py migrate
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import create_engine, inspect
from database import Base, engine, SessionLocal
# Import social media models first to ensure tables exist
from database_social_media import SocialMediaConnection, SocialMediaPost
# Import Twitter OAuth models
from database_twitter_oauth import (
    TwitterOAuthRequestToken,
    TwitterOAuthState,
    TwitterWebhook,
    TwitterRateLimitLog,
    TwitterOAuthAudit
)
import logging
import argparse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def migrate():
    """Run the migration"""
    logger.info("=" * 80)
    logger.info("Twitter OAuth 1.0a Complete Implementation - Database Migration")
    logger.info("=" * 80)

    try:
        # Create all tables
        logger.info("\nCreating Twitter OAuth tables...")
        Base.metadata.create_all(bind=engine)

        # Verify tables were created
        logger.info("\nVerifying tables...")
        tables = [
            "twitter_oauth_request_tokens",
            "twitter_oauth_states",
            "twitter_webhooks",
            "twitter_rate_limit_logs",
            "twitter_oauth_audit"
        ]

        all_exist = True
        for table in tables:
            exists = table_exists(table)
            status = "✓" if exists else "✗"
            logger.info(f"{status} Table '{table}': {'exists' if exists else 'missing'}")
            if not exists:
                all_exist = False

        if all_exist:
            logger.info("\n✓ Migration completed successfully!")
            logger.info("All Twitter OAuth 1.0a tables have been created.")
        else:
            logger.error("\n✗ Migration completed with errors.")
            logger.error("Some tables were not created successfully.")
            return False

        return True

    except Exception as e:
        logger.error(f"\n✗ Migration failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def rollback():
    """Rollback the migration (drop tables)"""
    logger.info("=" * 80)
    logger.info("Twitter OAuth 1.0a - Rollback Migration")
    logger.info("=" * 80)

    try:
        tables = [
            "twitter_oauth_audit",
            "twitter_rate_limit_logs",
            "twitter_webhooks",
            "twitter_oauth_states",
            "twitter_oauth_request_tokens"
        ]

        logger.info("\nDropping Twitter OAuth tables...")
        from sqlalchemy import text

        db = SessionLocal()
        for table in tables:
            if table_exists(table):
                logger.info(f"Dropping table: {table}")
                db.execute(text(f"DROP TABLE {table}"))
                db.commit()

        db.close()

        logger.info("\n✓ Rollback completed successfully!")
        return True

    except Exception as e:
        logger.error(f"\n✗ Rollback failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def verify():
    """Verify the migration"""
    logger.info("=" * 80)
    logger.info("Twitter OAuth 1.0a - Verify Migration")
    logger.info("=" * 80)

    try:
        tables = [
            "twitter_oauth_request_tokens",
            "twitter_oauth_states",
            "twitter_webhooks",
            "twitter_rate_limit_logs",
            "twitter_oauth_audit"
        ]

        logger.info("\nChecking tables...")
        all_exist = True
        for table in tables:
            exists = table_exists(table)
            status = "✓" if exists else "✗"
            logger.info(f"{status} Table '{table}': {'exists' if exists else 'missing'}")
            if not exists:
                all_exist = False

        if all_exist:
            logger.info("\n✓ All tables exist!")

            # Get row counts
            logger.info("\nTable statistics:")
            db = SessionLocal()
            from sqlalchemy import text
            for table in tables:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                logger.info(f"  {table}: {count} rows")
            db.close()

            return True
        else:
            logger.error("\n✗ Some tables are missing!")
            return False

    except Exception as e:
        logger.error(f"\n✗ Verification failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Twitter OAuth 1.0a Database Migration")
    parser.add_argument("action", choices=["migrate", "rollback", "verify"],
                       help="Action to perform")

    args = parser.parse_args()

    if args.action == "migrate":
        success = migrate()
    elif args.action == "rollback":
        success = rollback()
    elif args.action == "verify":
        success = verify()

    sys.exit(0 if success else 1)
