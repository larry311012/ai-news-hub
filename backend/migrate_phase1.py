"""
Phase 1 Database Migration Script

This script migrates the existing database to add authentication support:
1. Creates users table
2. Creates sessions table
3. Adds user_id column to articles table
4. Adds user_id column to posts table

The migration is designed to be backward compatible - all existing data is preserved,
and user_id columns are nullable to support existing records.
"""
import sqlite3
import os
from datetime import datetime

# Database path
DB_PATH = os.path.join(os.path.dirname(__file__), "ai_news.db")


def check_table_exists(cursor, table_name):
    """Check if a table exists in the database"""
    cursor.execute(
        f"""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='{table_name}'
    """
    )
    return cursor.fetchone() is not None


def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns


def migrate():
    """Run the Phase 1 migration"""
    print("=" * 60)
    print("Phase 1 Database Migration - User Authentication")
    print("=" * 60)
    print(f"\nDatabase: {DB_PATH}")
    print(f"Migration started at: {datetime.now()}\n")

    if not os.path.exists(DB_PATH):
        print("Error: Database file not found!")
        print("Please run the application first to create the database.")
        return False

    # Backup database first
    backup_path = f"{DB_PATH}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"Creating backup: {backup_path}")

    import shutil

    shutil.copy2(DB_PATH, backup_path)
    print("Backup created successfully!\n")

    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        print("Starting migration steps...\n")

        # Step 1: Create users table
        print("1. Creating 'users' table...")
        if check_table_exists(cursor, "users"):
            print("   ✓ Table 'users' already exists, skipping")
        else:
            cursor.execute(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255) NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    is_verified BOOLEAN NOT NULL DEFAULT 0,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """
            )
            cursor.execute("CREATE INDEX idx_users_email ON users(email)")
            print("   ✓ Table 'users' created successfully")

        # Step 2: Create sessions table
        print("\n2. Creating 'sessions' table...")
        if check_table_exists(cursor, "sessions"):
            print("   ✓ Table 'sessions' already exists, skipping")
        else:
            cursor.execute(
                """
                CREATE TABLE sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token VARCHAR(64) UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    user_agent VARCHAR(500),
                    ip_address VARCHAR(45),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """
            )
            cursor.execute("CREATE INDEX idx_sessions_user_id ON sessions(user_id)")
            cursor.execute("CREATE INDEX idx_sessions_token ON sessions(token)")
            print("   ✓ Table 'sessions' created successfully")

        # Step 3: Add user_id to articles table
        print("\n3. Adding 'user_id' column to 'articles' table...")
        if check_table_exists(cursor, "articles"):
            if check_column_exists(cursor, "articles", "user_id"):
                print("   ✓ Column 'user_id' already exists in 'articles', skipping")
            else:
                cursor.execute(
                    """
                    ALTER TABLE articles
                    ADD COLUMN user_id INTEGER
                    REFERENCES users(id) ON DELETE SET NULL
                """
                )
                cursor.execute("CREATE INDEX idx_articles_user_id ON articles(user_id)")
                print("   ✓ Column 'user_id' added to 'articles' successfully")
        else:
            print("   ⚠ Table 'articles' does not exist, skipping")

        # Step 4: Add user_id to posts table
        print("\n4. Adding 'user_id' column to 'posts' table...")
        if check_table_exists(cursor, "posts"):
            if check_column_exists(cursor, "posts", "user_id"):
                print("   ✓ Column 'user_id' already exists in 'posts', skipping")
            else:
                cursor.execute(
                    """
                    ALTER TABLE posts
                    ADD COLUMN user_id INTEGER
                    REFERENCES users(id) ON DELETE SET NULL
                """
                )
                cursor.execute("CREATE INDEX idx_posts_user_id ON posts(user_id)")
                print("   ✓ Column 'user_id' added to 'posts' successfully")
        else:
            print("   ⚠ Table 'posts' does not exist, skipping")

        # Commit all changes
        conn.commit()
        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)

        # Display summary
        print("\nDatabase Schema Summary:")
        print("-" * 60)

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()

        for table in tables:
            table_name = table[0]
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            print(f"\n{table_name}:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")

        print("\n" + "=" * 60)
        print("Next Steps:")
        print("=" * 60)
        print("1. Install new dependencies:")
        print("   pip install -r requirements.txt")
        print("\n2. Restart the FastAPI server:")
        print("   python main.py")
        print("\n3. Test the authentication endpoints:")
        print("   - POST /api/auth/register")
        print("   - POST /api/auth/login")
        print("   - GET /api/auth/me")
        print("   - POST /api/auth/logout")
        print("\n4. Visit http://localhost:8001/docs for API documentation")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ Error during migration: {str(e)}")
        print(f"Rolling back changes...")
        conn.rollback()
        print(f"\nRestoring from backup: {backup_path}")
        conn.close()

        import shutil

        shutil.copy2(backup_path, DB_PATH)
        print("Database restored from backup")

        return False

    finally:
        conn.close()


if __name__ == "__main__":
    success = migrate()
    exit(0 if success else 1)
