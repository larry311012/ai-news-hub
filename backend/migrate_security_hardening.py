"""
Database migration for security hardening features
Adds session_fingerprint column to sessions table
"""
from sqlalchemy import text
from database import engine, SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate():
    """Run migration to add security hardening columns"""
    db = SessionLocal()

    try:
        logger.info("Starting security hardening migration...")

        # Check if session_fingerprint column exists
        with engine.connect() as conn:
            # For SQLite
            result = conn.execute(text("PRAGMA table_info(sessions)"))
            columns = [row[1] for row in result]

            if "session_fingerprint" not in columns:
                logger.info("Adding session_fingerprint column to sessions table...")
                conn.execute(
                    text("ALTER TABLE sessions ADD COLUMN session_fingerprint VARCHAR(64)")
                )
                conn.commit()
                logger.info("Successfully added session_fingerprint column")
            else:
                logger.info("session_fingerprint column already exists")

        logger.info("Migration completed successfully!")

    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
