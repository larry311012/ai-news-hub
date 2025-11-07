#!/usr/bin/env python3
"""
Phase 2 Database Migration Script

This script migrates the database schema for Phase 2 features:
1. Adds 'bio' field to users table
2. Creates user_api_keys table for encrypted API key storage
3. Handles existing data gracefully

Usage:
    python3 migrate_phase2.py
"""

import sqlite3
import sys
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def get_db_path():
    """Get the database file path"""
    backend_dir = Path(__file__).parent
    db_path = backend_dir / "ai_news.db"
    return db_path


def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    return column_name in column_names


def check_table_exists(cursor, table_name):
    """Check if a table exists"""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
    return cursor.fetchone() is not None


def add_bio_column(cursor):
    """Add bio column to users table if it doesn't exist"""
    logger.info("Checking users table for bio column...")

    if not check_table_exists(cursor, "users"):
        logger.error("users table does not exist! Run Phase 1 migration first.")
        return False

    if check_column_exists(cursor, "users", "bio"):
        logger.info("✓ bio column already exists in users table")
        return True

    try:
        logger.info("Adding bio column to users table...")
        cursor.execute(
            """
            ALTER TABLE users
            ADD COLUMN bio TEXT
        """
        )
        logger.info("✓ Successfully added bio column to users table")
        return True
    except Exception as e:
        logger.error(f"Failed to add bio column: {str(e)}")
        return False


def create_user_api_keys_table(cursor):
    """Create user_api_keys table if it doesn't exist"""
    logger.info("Checking for user_api_keys table...")

    if check_table_exists(cursor, "user_api_keys"):
        logger.info("✓ user_api_keys table already exists")
        return True

    try:
        logger.info("Creating user_api_keys table...")
        cursor.execute(
            """
            CREATE TABLE user_api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                provider VARCHAR(50) NOT NULL,
                encrypted_key TEXT NOT NULL,
                name VARCHAR(255),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
            )
        """
        )

        # Create indexes for performance
        cursor.execute(
            """
            CREATE INDEX idx_user_api_keys_user_id
            ON user_api_keys (user_id)
        """
        )

        cursor.execute(
            """
            CREATE INDEX idx_user_api_keys_provider
            ON user_api_keys (provider)
        """
        )

        # Create unique constraint on user_id + provider
        cursor.execute(
            """
            CREATE UNIQUE INDEX idx_user_api_keys_user_provider
            ON user_api_keys (user_id, provider)
        """
        )

        logger.info("✓ Successfully created user_api_keys table with indexes")
        return True
    except Exception as e:
        logger.error(f"Failed to create user_api_keys table: {str(e)}")
        return False


def update_cascade_deletes(cursor):
    """
    Update cascade delete behavior for articles and posts tables.

    Note: SQLite doesn't support modifying foreign keys directly.
    This is informational - the cascade is already set in database.py
    and will be applied when tables are recreated.
    """
    logger.info("Checking cascade delete configuration...")

    # Check if articles table has proper cascade
    cursor.execute("PRAGMA foreign_key_list(articles)")
    articles_fks = cursor.fetchall()

    # Check if posts table has proper cascade
    cursor.execute("PRAGMA foreign_key_list(posts)")
    posts_fks = cursor.fetchall()

    has_articles_cascade = any(fk[3] == "users" and fk[5] == "CASCADE" for fk in articles_fks)

    has_posts_cascade = any(fk[3] == "users" and fk[5] == "CASCADE" for fk in posts_fks)

    if has_articles_cascade and has_posts_cascade:
        logger.info("✓ Cascade delete already configured for articles and posts")
    else:
        logger.warning("⚠ Cascade delete not fully configured (will be set in database.py)")
        logger.warning("  If you need to recreate tables, drop and re-run init_db()")

    return True


def verify_migration(cursor):
    """Verify that the migration was successful"""
    logger.info("\nVerifying migration...")

    # Check users table
    if not check_table_exists(cursor, "users"):
        logger.error("✗ users table missing")
        return False

    if not check_column_exists(cursor, "users", "bio"):
        logger.error("✗ bio column missing from users table")
        return False

    logger.info("✓ users table has bio column")

    # Check user_api_keys table
    if not check_table_exists(cursor, "user_api_keys"):
        logger.error("✗ user_api_keys table missing")
        return False

    logger.info("✓ user_api_keys table exists")

    # Check user_api_keys columns
    required_columns = [
        "id",
        "user_id",
        "provider",
        "encrypted_key",
        "name",
        "created_at",
        "updated_at",
    ]

    for column in required_columns:
        if not check_column_exists(cursor, "user_api_keys", column):
            logger.error(f"✗ {column} column missing from user_api_keys table")
            return False

    logger.info("✓ user_api_keys table has all required columns")

    # Check indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='user_api_keys'")
    indexes = cursor.fetchall()
    index_names = [idx[0] for idx in indexes]

    expected_indexes = [
        "idx_user_api_keys_user_id",
        "idx_user_api_keys_provider",
        "idx_user_api_keys_user_provider",
    ]

    for idx_name in expected_indexes:
        if idx_name in index_names:
            logger.info(f"✓ Index {idx_name} exists")
        else:
            logger.warning(f"⚠ Index {idx_name} missing (may be OK if using different name)")

    return True


def get_table_stats(cursor):
    """Get statistics about the tables"""
    stats = {}

    # Count users
    cursor.execute("SELECT COUNT(*) FROM users")
    stats["users"] = cursor.fetchone()[0]

    # Count sessions
    if check_table_exists(cursor, "sessions"):
        cursor.execute("SELECT COUNT(*) FROM sessions")
        stats["sessions"] = cursor.fetchone()[0]

    # Count API keys
    if check_table_exists(cursor, "user_api_keys"):
        cursor.execute("SELECT COUNT(*) FROM user_api_keys")
        stats["api_keys"] = cursor.fetchone()[0]
    else:
        stats["api_keys"] = 0

    # Count articles
    if check_table_exists(cursor, "articles"):
        cursor.execute("SELECT COUNT(*) FROM articles")
        stats["articles"] = cursor.fetchone()[0]

    # Count posts
    if check_table_exists(cursor, "posts"):
        cursor.execute("SELECT COUNT(*) FROM posts")
        stats["posts"] = cursor.fetchone()[0]

    return stats


def main():
    """Main migration function"""
    print("=" * 70)
    print("Phase 2 Database Migration")
    print("=" * 70)
    print()

    # Get database path
    db_path = get_db_path()

    if not db_path.exists():
        logger.error(f"Database file not found: {db_path}")
        logger.error("Please run the backend server first to create the database")
        sys.exit(1)

    logger.info(f"Database: {db_path}")
    print()

    # Connect to database
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")

        logger.info("Connected to database successfully")
        print()

        # Get stats before migration
        logger.info("Database statistics before migration:")
        stats_before = get_table_stats(cursor)
        for table, count in stats_before.items():
            logger.info(f"  {table}: {count} rows")
        print()

        # Run migrations
        success = True

        # 1. Add bio column to users table
        if not add_bio_column(cursor):
            success = False

        print()

        # 2. Create user_api_keys table
        if not create_user_api_keys_table(cursor):
            success = False

        print()

        # 3. Update cascade delete configuration
        if not update_cascade_deletes(cursor):
            success = False

        print()

        if not success:
            logger.error("Migration failed! Rolling back changes...")
            conn.rollback()
            sys.exit(1)

        # Commit changes
        conn.commit()
        logger.info("✓ All changes committed successfully")
        print()

        # Verify migration
        if not verify_migration(cursor):
            logger.error("Migration verification failed!")
            sys.exit(1)

        print()

        # Get stats after migration
        logger.info("Database statistics after migration:")
        stats_after = get_table_stats(cursor)
        for table, count in stats_after.items():
            logger.info(f"  {table}: {count} rows")
        print()

        # Success message
        print("=" * 70)
        print("Migration completed successfully!")
        print("=" * 70)
        print()
        print("Phase 2 features are now available:")
        print("  • User profile bio field")
        print("  • Encrypted API key management")
        print("  • Password change functionality")
        print("  • Account deletion")
        print()
        print("New API endpoints:")
        print("  • PATCH /api/auth/profile - Update profile")
        print("  • POST /api/auth/change-password - Change password")
        print("  • DELETE /api/auth/account - Delete account")
        print("  • POST /api/auth/api-keys - Save API key")
        print("  • GET /api/auth/api-keys - List API keys")
        print("  • DELETE /api/auth/api-keys/{provider} - Delete API key")
        print("  • POST /api/auth/api-keys/{provider}/test - Test API key")
        print()
        print("=" * 70)

    except sqlite3.Error as e:
        logger.error(f"Database error: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()
            logger.info("Database connection closed")


if __name__ == "__main__":
    main()
