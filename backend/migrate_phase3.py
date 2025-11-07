#!/usr/bin/env python3
"""
Phase 3 Database Migration Script
Adds OAuth, email verification, and guest mode fields to User model
"""
import sqlite3
import shutil
from datetime import datetime
from pathlib import Path
import sys


def backup_database(db_path):
    """Create a backup of the database before migration"""
    backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(db_path, backup_path)
    print(f"Database backed up to: {backup_path}")
    return backup_path


def check_column_exists(cursor, table, column):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def migrate_phase3(db_path="ai_news.db"):
    """
    Migrate database to Phase 3 schema.

    Adds:
    - oauth_provider, oauth_id, oauth_profile_picture to users
    - verification_token, verification_token_expires to users
    - is_guest to users
    - Makes password_hash nullable
    """
    if not Path(db_path).exists():
        print(f"Error: Database file not found at {db_path}")
        sys.exit(1)

    print("=" * 80)
    print("Phase 3 Database Migration")
    print("=" * 80)
    print()

    # Backup database
    backup_path = backup_database(db_path)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        print("Checking current schema...")

        # Check which columns need to be added
        columns_to_add = []

        oauth_columns = {
            "oauth_provider": "VARCHAR(50)",
            "oauth_id": "VARCHAR(255)",
            "oauth_profile_picture": "VARCHAR(500)",
            "verification_token": "VARCHAR(64)",
            "verification_token_expires": "DATETIME",
            "is_guest": "BOOLEAN DEFAULT 0",
        }

        for column, column_type in oauth_columns.items():
            if not check_column_exists(cursor, "users", column):
                columns_to_add.append((column, column_type))

        if not columns_to_add:
            print("All Phase 3 columns already exist. No migration needed.")
            conn.close()
            return

        print(f"Found {len(columns_to_add)} columns to add:")
        for col, col_type in columns_to_add:
            print(f"  - {col} ({col_type})")
        print()

        # Add new columns
        print("Adding new columns...")
        for column, column_type in columns_to_add:
            try:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {column} {column_type}")
                print(f"  ✓ Added column: {column}")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e).lower():
                    print(f"  - Column {column} already exists, skipping")
                else:
                    raise

        # Create indices for new columns
        print("\nCreating indices...")
        indices = [
            ("idx_users_oauth_provider", "users", "oauth_provider"),
            ("idx_users_oauth_id", "users", "oauth_id"),
            ("idx_users_verification_token", "users", "verification_token"),
            ("idx_users_is_guest", "users", "is_guest"),
        ]

        for idx_name, table, column in indices:
            try:
                cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")
                print(f"  ✓ Created index: {idx_name}")
            except sqlite3.OperationalError as e:
                print(f"  - Index {idx_name} may already exist: {e}")

        # Update existing users to set is_guest=False if NULL
        print("\nUpdating existing users...")
        cursor.execute("UPDATE users SET is_guest = 0 WHERE is_guest IS NULL")
        updated_count = cursor.rowcount
        print(f"  ✓ Set is_guest=False for {updated_count} existing users")

        # Commit changes
        conn.commit()

        # Verify migration
        print("\nVerifying migration...")
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()

        expected_columns = [
            "oauth_provider",
            "oauth_id",
            "oauth_profile_picture",
            "verification_token",
            "verification_token_expires",
            "is_guest",
        ]

        existing_columns = [col[1] for col in columns]
        all_present = all(col in existing_columns for col in expected_columns)

        if all_present:
            print("  ✓ All Phase 3 columns present")
        else:
            missing = [col for col in expected_columns if col not in existing_columns]
            print(f"  ✗ Missing columns: {', '.join(missing)}")
            raise Exception("Migration verification failed")

        # Display updated schema
        print("\nUpdated User table schema:")
        print("-" * 80)
        for col in columns:
            print(f"  {col[1]:30s} {col[2]:20s} {'NOT NULL' if col[3] else 'NULL':10s}")
        print("-" * 80)

        conn.close()

        print()
        print("=" * 80)
        print("Phase 3 Migration completed successfully!")
        print("=" * 80)
        print()
        print("New features enabled:")
        print("  ✓ Google OAuth authentication")
        print("  ✓ Email verification with tokens")
        print("  ✓ Guest mode for anonymous users")
        print("  ✓ OAuth account linking")
        print()
        print("Next steps:")
        print("  1. Configure OAuth credentials in .env")
        print("  2. Configure email service in .env")
        print("  3. Test OAuth flow: GET /api/auth/oauth/google")
        print("  4. Test guest mode: POST /api/auth/guest")
        print("  5. Test email verification: POST /api/auth/send-verification")
        print()
        print(f"Backup saved at: {backup_path}")
        print()

    except Exception as e:
        print()
        print("=" * 80)
        print("ERROR: Migration failed!")
        print("=" * 80)
        print(f"Error: {str(e)}")
        print()
        print(f"Database backup available at: {backup_path}")
        print("You can restore the backup if needed:")
        print(f"  cp {backup_path} {db_path}")
        sys.exit(1)


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "ai_news.db"
    migrate_phase3(db_path)
