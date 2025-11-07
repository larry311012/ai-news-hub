"""
Migration script to create user_feeds table for RSS feed management

Run this script to create the necessary database tables:
    python migrate_user_feeds.py
"""

import sqlite3
import os
from pathlib import Path

def create_user_feeds_table():
    """Create user_feeds table for user's RSS feed subscriptions"""

    # Get database path
    BASE_DIR = Path(__file__).resolve().parent
    db_path = os.getenv("DATABASE_URL", "sqlite:///ai_news.db").replace("sqlite:///", "")

    # Handle relative paths
    if not os.path.isabs(db_path):
        db_path = os.path.join(BASE_DIR, db_path)

    print(f"Using database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create user_feeds table
    print("Creating user_feeds table...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_feeds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            feed_url TEXT NOT NULL,
            feed_name TEXT,
            feed_description TEXT,
            feed_type TEXT DEFAULT 'rss',
            website_url TEXT,
            update_frequency INTEGER DEFAULT 3600,
            last_fetched_at TIMESTAMP,
            last_successful_fetch TIMESTAMP,
            health_status TEXT DEFAULT 'unknown',
            error_message TEXT,
            total_items_fetched INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, feed_url)
        )
    """)

    # Create index on user_id for faster queries
    print("Creating index on user_id...")
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_feeds_user_id
        ON user_feeds(user_id)
    """)

    # Create index on health_status for filtering
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_feeds_health_status
        ON user_feeds(health_status)
    """)

    # Create index on is_active for filtering
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_feeds_is_active
        ON user_feeds(is_active)
    """)

    conn.commit()
    conn.close()

    print("✓ Migration completed successfully!")
    print("  - user_feeds table created")
    print("  - Indexes created for performance")
    print("\nYou can now use the RSS feed management features!")

if __name__ == "__main__":
    create_user_feeds_table()
