"""
Add error_details JSON column to posts table for structured error information

This migration adds support for detailed error tracking including:
- Error type (quota_exceeded, invalid_api_key, rate_limit, etc.)
- Provider (openai, anthropic)
- Action guidance for users
- Documentation links
- Retry information
"""
import os
import sys
from sqlalchemy import create_engine, text, JSON, Column, Text
from sqlalchemy.orm import sessionmaker

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://ranhui@localhost/ai_news_test")

def migrate():
    """Add error_details column to posts table"""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        # Check if column exists
        check_query = text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name='posts' AND column_name='error_details'
        """)
        result = conn.execute(check_query)
        exists = result.fetchone() is not None

        if not exists:
            print("Adding error_details column to posts table...")
            alter_query = text("""
                ALTER TABLE posts
                ADD COLUMN error_details JSON NULL
            """)
            conn.execute(alter_query)
            conn.commit()
            print("✓ error_details column added successfully")
        else:
            print("✓ error_details column already exists")

if __name__ == "__main__":
    migrate()
