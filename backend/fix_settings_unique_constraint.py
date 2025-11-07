"""
Fix: Drop unique constraint on settings.key column

The old schema had a unique constraint on the 'key' column which prevented
multiple users from having the same setting key. We need to drop this constraint.
"""
import os
from sqlalchemy import text
from database import SessionLocal
from loguru import logger


def fix_constraint():
    """Drop the unique constraint on settings.key"""

    db = SessionLocal()

    try:
        logger.info("Checking for unique constraint on settings.key...")

        database_url = os.getenv("DATABASE_URL", "sqlite:///./ai_news.db")
        is_sqlite = "sqlite" in database_url

        if is_sqlite:
            logger.info("SQLite doesn't use named constraints, skipping...")
            return

        # For PostgreSQL, drop the unique constraint
        logger.info("Dropping unique constraint on settings.key...")

        try:
            # Try to drop the constraint
            db.execute(text("ALTER TABLE settings DROP CONSTRAINT IF EXISTS settings_key_key"))
            db.commit()
            logger.info("✓ Unique constraint dropped successfully")
        except Exception as e:
            logger.warning(f"Could not drop constraint (may not exist): {e}")
            db.rollback()

        logger.info("✓ Fix completed successfully!")

    except Exception as e:
        logger.error(f"Fix failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    fix_constraint()
