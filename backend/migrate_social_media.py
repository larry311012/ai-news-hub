"""
Database Migration: Social Media Connections

This migration adds tables for managing social media platform connections,
OAuth tokens, and publishing history for LinkedIn, Twitter, and Threads.

Run this script to add the social media connection tables to your database:
    python migrate_social_media.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import create_engine, inspect
from database import Base, DATABASE_URL
from database_social_media import (
    SocialMediaConnection,
    SocialMediaPost,
    SocialMediaRateLimit,
    SocialMediaWebhook,
)
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_table_exists(engine, table_name: str) -> bool:
    """Check if a table exists in the database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def migrate():
    """Run the migration to create social media tables"""
    try:
        logger.info("=" * 80)
        logger.info("Social Media Connection Migration")
        logger.info("=" * 80)

        # Create engine
        engine = create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
        )

        logger.info(f"Connected to database: {DATABASE_URL}")

        # Check existing tables
        logger.info("\nChecking existing tables...")
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        logger.info(f"Found {len(existing_tables)} existing tables")

        # Tables to create
        new_tables = [
            "social_media_connections",
            "social_media_posts",
            "social_media_rate_limits",
            "social_media_webhooks",
        ]

        # Check which tables need to be created
        tables_to_create = []
        for table_name in new_tables:
            if table_name in existing_tables:
                logger.info(f"✓ Table '{table_name}' already exists")
            else:
                logger.info(f"✗ Table '{table_name}' needs to be created")
                tables_to_create.append(table_name)

        if not tables_to_create:
            logger.info("\n✓ All social media tables already exist. No migration needed.")
            return

        # Create new tables
        logger.info(f"\nCreating {len(tables_to_create)} new tables...")

        # Create tables
        Base.metadata.create_all(
            bind=engine,
            tables=[
                SocialMediaConnection.__table__,
                SocialMediaPost.__table__,
                SocialMediaRateLimit.__table__,
                SocialMediaWebhook.__table__,
            ],
        )

        # Verify tables were created
        logger.info("\nVerifying table creation...")
        inspector = inspect(engine)
        updated_tables = inspector.get_table_names()

        for table_name in tables_to_create:
            if table_name in updated_tables:
                logger.info(f"✓ Table '{table_name}' created successfully")

                # Show table schema
                columns = inspector.get_columns(table_name)
                logger.info(f"  Columns: {len(columns)}")
                for col in columns:
                    logger.info(f"    - {col['name']}: {col['type']}")
            else:
                logger.error(f"✗ Failed to create table '{table_name}'")

        logger.info("\n" + "=" * 80)
        logger.info("Migration completed successfully!")
        logger.info("=" * 80)

        # Print summary
        logger.info("\nSummary:")
        logger.info(f"  - Tables created: {len(tables_to_create)}")
        logger.info(f"  - Total tables: {len(updated_tables)}")

        logger.info("\nNext steps:")
        logger.info("  1. Configure OAuth credentials in .env file:")
        logger.info("     - LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET")
        logger.info("     - TWITTER_CLIENT_ID and TWITTER_CLIENT_SECRET")
        logger.info("     - THREADS_CLIENT_ID and THREADS_CLIENT_SECRET")
        logger.info("  2. Update redirect URIs in OAuth provider settings")
        logger.info("  3. Restart the backend server")
        logger.info("  4. Test OAuth flows via /api/social endpoints")

        logger.info("\nNew API endpoints available:")
        logger.info("  - GET  /api/social-media/{platform}/connect - Initiate OAuth")
        logger.info("  - GET  /api/social-media/{platform}/callback - OAuth callback")
        logger.info("  - GET  /api/social-media/connections - List all connections")
        logger.info("  - GET  /api/social-media/{platform}/status - Check connection status")
        logger.info("  - DELETE /api/social-media/{platform}/disconnect - Remove connection")
        logger.info("  - POST /api/social-media/{platform}/refresh - Refresh token")
        logger.info("  - POST /api/social-media/publish - Publish to platforms")

    except Exception as e:
        logger.error(f"\n✗ Migration failed: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    migrate()
