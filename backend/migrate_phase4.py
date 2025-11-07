"""
Phase 4 Database Migration Script
==================================

This script migrates the database to Phase 4, adding:
1. Password reset fields to User table
2. last_activity to UserSession table
3. UserSecuritySettings table
4. LoginActivity table
5. SecurityAudit table
6. RateLimitLog table

IMPORTANT: This script will backup your database before migration.
"""

import os
import sys
import shutil
from datetime import datetime
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import Session

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import Base, DATABASE_URL


def backup_database():
    """Create a backup of the database before migration"""
    if "sqlite" in DATABASE_URL:
        db_path = DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")
        if os.path.exists(db_path):
            backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(db_path, backup_path)
            print(f"✓ Database backed up to: {backup_path}")
            return backup_path
    else:
        print("⚠ Backup not implemented for non-SQLite databases")
        print("  Please backup your database manually before proceeding")
        response = input("Continue anyway? (yes/no): ")
        if response.lower() != "yes":
            sys.exit(1)
    return None


def check_table_exists(inspector, table_name):
    """Check if a table exists"""
    return table_name in inspector.get_table_names()


def check_column_exists(inspector, table_name, column_name):
    """Check if a column exists in a table"""
    if not check_table_exists(inspector, table_name):
        return False
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def migrate_phase4():
    """Execute Phase 4 migration"""
    print("\n" + "=" * 60)
    print("Phase 4 Migration: Polish & Security")
    print("=" * 60 + "\n")

    # Create engine
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)

    # Backup database
    print("Step 1: Backing up database...")
    backup_path = backup_database()

    # Check current state
    print("\nStep 2: Checking current database state...")
    tables = inspector.get_table_names()
    print(f"Found {len(tables)} existing tables: {', '.join(tables)}")

    # Apply migrations
    print("\nStep 3: Applying migrations...")

    with engine.begin() as conn:
        # 1. Add reset_token fields to users table
        if check_table_exists(inspector, "users"):
            print("\n  Adding password reset fields to users table...")

            if not check_column_exists(inspector, "users", "reset_token"):
                if "sqlite" in DATABASE_URL:
                    conn.execute(text("ALTER TABLE users ADD COLUMN reset_token VARCHAR(64)"))
                    conn.execute(
                        text(
                            "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_reset_token ON users (reset_token)"
                        )
                    )
                else:
                    conn.execute(
                        text("ALTER TABLE users ADD COLUMN reset_token VARCHAR(64) UNIQUE")
                    )
                print("    ✓ Added reset_token column")
            else:
                print("    - reset_token column already exists")

            if not check_column_exists(inspector, "users", "reset_token_expires"):
                conn.execute(text("ALTER TABLE users ADD COLUMN reset_token_expires DATETIME"))
                print("    ✓ Added reset_token_expires column")
            else:
                print("    - reset_token_expires column already exists")

            if not check_column_exists(inspector, "users", "password_changed_at"):
                conn.execute(text("ALTER TABLE users ADD COLUMN password_changed_at DATETIME"))
                print("    ✓ Added password_changed_at column")
            else:
                print("    - password_changed_at column already exists")

        # 2. Add last_activity to sessions table
        if check_table_exists(inspector, "sessions"):
            print("\n  Adding last_activity to sessions table...")

            if not check_column_exists(inspector, "sessions", "last_activity"):
                # SQLite doesn't support DEFAULT with functions in ALTER TABLE
                # So we add it as NULL first, then update
                conn.execute(text("ALTER TABLE sessions ADD COLUMN last_activity DATETIME"))
                # Update existing rows to use created_at as initial value
                conn.execute(
                    text(
                        "UPDATE sessions SET last_activity = created_at WHERE last_activity IS NULL"
                    )
                )
                print("    ✓ Added last_activity column")
            else:
                print("    - last_activity column already exists")

    # Refresh inspector after ALTER TABLE
    inspector = inspect(engine)

    # 3. Create new tables using SQLAlchemy models
    print("\n  Creating new tables...")

    new_tables = ["user_security_settings", "login_activity", "security_audit", "rate_limit_log"]

    tables_to_create = []
    for table_name in new_tables:
        if not check_table_exists(inspector, table_name):
            tables_to_create.append(table_name)

    if tables_to_create:
        # Create only the new tables
        Base.metadata.create_all(
            bind=engine,
            tables=[Base.metadata.tables[table_name] for table_name in tables_to_create],
        )
        for table_name in tables_to_create:
            print(f"    ✓ Created {table_name} table")
    else:
        print("    - All Phase 4 tables already exist")

    # Verify migration
    print("\nStep 4: Verifying migration...")
    inspector = inspect(engine)
    final_tables = inspector.get_table_names()

    required_tables = [
        "users",
        "sessions",
        "user_security_settings",
        "login_activity",
        "security_audit",
        "rate_limit_log",
    ]

    all_present = all(table in final_tables for table in required_tables)

    if all_present:
        print("✓ All required tables present")

        # Check for new columns
        users_columns = [col["name"] for col in inspector.get_columns("users")]
        required_user_columns = ["reset_token", "reset_token_expires", "password_changed_at"]
        user_columns_present = all(col in users_columns for col in required_user_columns)

        sessions_columns = [col["name"] for col in inspector.get_columns("sessions")]
        session_columns_present = "last_activity" in sessions_columns

        if user_columns_present and session_columns_present:
            print("✓ All required columns present")
            print("\n" + "=" * 60)
            print("Migration completed successfully!")
            print("=" * 60)
            print("\nPhase 4 features are now available:")
            print("  - Password reset flow")
            print("  - Session management dashboard")
            print("  - Security score calculation")
            print("  - Login activity tracking")
            print("  - Security audit logging")
            print("  - Rate limiting")
            print("\nNext steps:")
            print("  1. Restart your backend server")
            print("  2. Test password reset flow")
            print("  3. Check security dashboard endpoints")
            print("  4. Review security audit logs")
            if backup_path:
                print(f"\nBackup saved at: {backup_path}")
            return True
        else:
            print("⚠ Some columns missing")
            return False
    else:
        print("⚠ Migration incomplete - some tables missing")
        return False


def rollback_migration(backup_path):
    """Rollback migration by restoring backup"""
    if backup_path and os.path.exists(backup_path):
        db_path = DATABASE_URL.replace("sqlite:///", "").replace("sqlite://", "")
        response = input(f"\nRestore backup from {backup_path}? (yes/no): ")
        if response.lower() == "yes":
            shutil.copy2(backup_path, db_path)
            print("✓ Database restored from backup")
        else:
            print("Rollback cancelled")
    else:
        print("No backup available for rollback")


if __name__ == "__main__":
    try:
        print("\n⚠ WARNING: This will modify your database structure!")
        print("A backup will be created automatically.\n")

        response = input("Do you want to proceed with Phase 4 migration? (yes/no): ")

        if response.lower() != "yes":
            print("Migration cancelled")
            sys.exit(0)

        success = migrate_phase4()

        if not success:
            print("\n⚠ Migration encountered issues")
            sys.exit(1)

    except Exception as e:
        print(f"\n✗ Migration failed: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
