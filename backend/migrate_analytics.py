#!/usr/bin/env python3
"""
Analytics System Migration
Adds analytics_events table for tracking user behavior and conversion funnel
"""
import sqlite3
from datetime import datetime
from pathlib import Path


def migrate():
    """Run analytics migration"""
    # Get database path relative to this script
    db_path = Path(__file__).resolve().parent / "ai_news.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    print("Starting Analytics System Migration...")

    try:
        # Check if analytics_events table already exists
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='analytics_events'
        """
        )

        if cursor.fetchone():
            print("⚠️  analytics_events table already exists, skipping...")
        else:
            # Create analytics_events table
            print("Creating analytics_events table...")
            cursor.execute(
                """
                CREATE TABLE analytics_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_name VARCHAR(100) NOT NULL,
                    user_id INTEGER NULL,
                    session_id VARCHAR(64) NULL,
                    properties TEXT,
                    user_agent VARCHAR(500),
                    ip_address VARCHAR(45),
                    referrer VARCHAR(500),
                    page_url VARCHAR(500),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
                )
            """
            )

            # Create indexes for performance
            print("Creating indexes...")
            cursor.execute(
                """
                CREATE INDEX idx_analytics_event_name
                ON analytics_events(event_name)
            """
            )

            cursor.execute(
                """
                CREATE INDEX idx_analytics_user_id
                ON analytics_events(user_id)
            """
            )

            cursor.execute(
                """
                CREATE INDEX idx_analytics_session_id
                ON analytics_events(session_id)
            """
            )

            cursor.execute(
                """
                CREATE INDEX idx_analytics_created_at
                ON analytics_events(created_at)
            """
            )

            print("✅ analytics_events table created successfully")

        conn.commit()
        print("\n✅ Analytics migration completed successfully!")

        # Show table structure
        cursor.execute("PRAGMA table_info(analytics_events)")
        columns = cursor.fetchall()
        print("\nanalytics_events table structure:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")

        # Show indexes
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='index' AND tbl_name='analytics_events'
        """
        )
        indexes = cursor.fetchall()
        print("\nIndexes:")
        for idx in indexes:
            if not idx[0].startswith("sqlite_"):
                print(f"  - {idx[0]}")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
