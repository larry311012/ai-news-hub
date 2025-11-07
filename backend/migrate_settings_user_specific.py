"""
Migration: Make Settings table user-specific

This migration adds user_id column to the settings table to make settings
user-specific instead of global. This fixes the 500 error when authenticated
users try to load their settings.

Changes:
- Add user_id column to settings table (nullable for backward compatibility)
- Add foreign key constraint to users table
- Add index on user_id for performance
- Add composite unique constraint on (user_id, key) to prevent duplicate settings per user

Usage:
    python migrate_settings_user_specific.py
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from database import engine, SessionLocal
from loguru import logger


def migrate():
    """Run migration to add user_id to settings table"""

    db = SessionLocal()

    try:
        logger.info("Starting settings table migration...")

        # Check database type
        database_url = os.getenv("DATABASE_URL", "sqlite:///./ai_news.db")
        is_sqlite = "sqlite" in database_url

        # Step 1: Check if user_id column already exists
        if is_sqlite:
            # SQLite: Query table info
            result = db.execute(text("PRAGMA table_info(settings)"))
            columns = [row[1] for row in result.fetchall()]
        else:
            # PostgreSQL: Query information_schema
            result = db.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'settings' AND column_name = 'user_id'
            """))
            columns = [row[0] for row in result.fetchall()]

        if 'user_id' in columns or any('user_id' in str(col).lower() for col in columns):
            logger.info("Migration already applied - user_id column exists")
            return

        logger.info("Adding user_id column to settings table...")

        # Step 2: Add user_id column (nullable for backward compatibility)
        if is_sqlite:
            # SQLite doesn't support ADD COLUMN with foreign key in one statement
            db.execute(text("""
                ALTER TABLE settings
                ADD COLUMN user_id INTEGER
            """))
            logger.info("Added user_id column (SQLite)")
        else:
            # PostgreSQL supports full constraints
            db.execute(text("""
                ALTER TABLE settings
                ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE
            """))
            logger.info("Added user_id column with foreign key (PostgreSQL)")

        db.commit()

        # Step 3: Add index on user_id for performance
        logger.info("Adding index on user_id...")
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_settings_user_id ON settings(user_id)
        """))
        db.commit()
        logger.info("Added index on user_id")

        # Step 4: Add composite unique constraint to prevent duplicate settings per user
        # Note: We allow NULL user_id for global settings
        logger.info("Adding composite unique constraint...")

        if is_sqlite:
            # SQLite: We'll handle this in application logic since SQLite has limitations
            logger.info("Skipping unique constraint for SQLite (will be enforced in application)")
        else:
            # PostgreSQL: Add partial unique index that allows multiple NULL user_ids
            db.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_settings_user_key
                ON settings(user_id, key)
                WHERE user_id IS NOT NULL
            """))
            logger.info("Added composite unique constraint")

        db.commit()

        logger.info("✓ Migration completed successfully!")
        logger.info("Settings table is now user-specific")

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
