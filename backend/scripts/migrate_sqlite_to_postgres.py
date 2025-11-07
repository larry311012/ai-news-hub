#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script
=====================================

This script migrates all data from SQLite (ai_news.db) to PostgreSQL (ai_news_local).
It handles all tables and preserves data integrity.

Usage:
    python scripts/migrate_sqlite_to_postgres.py

Prerequisites:
    - PostgreSQL database 'ai_news_local' must exist
    - psycopg2-binary must be installed
    - SQLite database ai_news.db must exist
"""

import sys
import os
from datetime import datetime
from sqlalchemy import create_engine, inspect, MetaData, Table, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Add parent directory to path to import database module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class DatabaseMigration:
    """Handles migration from SQLite to PostgreSQL"""

    def __init__(self, sqlite_url, postgres_url):
        """Initialize migration with source and target database URLs"""
        self.sqlite_url = sqlite_url
        self.postgres_url = postgres_url

        # Create engines
        print(f"Connecting to SQLite: {sqlite_url}")
        self.sqlite_engine = create_engine(
            sqlite_url,
            connect_args={"check_same_thread": False},
            poolclass=NullPool
        )

        print(f"Connecting to PostgreSQL: {postgres_url}")
        self.postgres_engine = create_engine(
            postgres_url,
            pool_pre_ping=True,
            poolclass=NullPool
        )

        # Create sessions
        self.sqlite_session = sessionmaker(bind=self.sqlite_engine)()
        self.postgres_session = sessionmaker(bind=self.postgres_engine)()

    def get_table_names(self):
        """Get all table names from SQLite database"""
        inspector = inspect(self.sqlite_engine)
        return inspector.get_table_names()

    def get_row_count(self, engine, table_name):
        """Get row count for a table"""
        try:
            with engine.connect() as conn:
                result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                return result.scalar()
        except Exception as e:
            print(f"Warning: Could not count rows in {table_name}: {e}")
            return 0

    def create_postgres_schema(self):
        """Create PostgreSQL schema from models"""
        print("\n" + "="*60)
        print("Creating PostgreSQL schema...")
        print("="*60)

        try:
            # Import database models to create schema
            from database import Base, engine as db_engine

            # Temporarily override engine with postgres
            original_url = os.getenv("DATABASE_URL", "")
            os.environ["DATABASE_URL"] = self.postgres_url

            # Create all tables
            Base.metadata.create_all(bind=self.postgres_engine)

            # Restore original URL
            if original_url:
                os.environ["DATABASE_URL"] = original_url
            else:
                os.environ.pop("DATABASE_URL", None)

            print("PostgreSQL schema created successfully!")
            return True

        except Exception as e:
            print(f"Error creating PostgreSQL schema: {e}")
            import traceback
            traceback.print_exc()
            return False

    def migrate_table(self, table_name):
        """Migrate a single table from SQLite to PostgreSQL"""
        print(f"\nMigrating table: {table_name}")
        print("-" * 60)

        try:
            # Get table metadata from SQLite
            sqlite_metadata = MetaData()
            sqlite_metadata.reflect(bind=self.sqlite_engine)

            if table_name not in sqlite_metadata.tables:
                print(f"Table {table_name} not found in SQLite database")
                return False

            sqlite_table = sqlite_metadata.tables[table_name]

            # Get table metadata from PostgreSQL
            postgres_metadata = MetaData()
            postgres_metadata.reflect(bind=self.postgres_engine)

            if table_name not in postgres_metadata.tables:
                print(f"Table {table_name} not found in PostgreSQL database - skipping")
                return True

            postgres_table = postgres_metadata.tables[table_name]

            # Get data from SQLite
            with self.sqlite_engine.connect() as sqlite_conn:
                select_query = sqlite_table.select()
                result = sqlite_conn.execute(select_query)
                sqlite_data = result.fetchall()

                if not sqlite_data:
                    print(f"No data to migrate for table {table_name}")
                    return True

                print(f"Found {len(sqlite_data)} rows in SQLite")

                # Get column names from the result
                column_names = result.keys()

                # Filter to only columns that exist in both tables
                sqlite_columns = set([col.name for col in sqlite_table.columns])
                postgres_columns = set([col.name for col in postgres_table.columns])
                common_columns = sqlite_columns.intersection(postgres_columns)

                print(f"Migrating columns: {', '.join(sorted(common_columns))}")

                # Insert data into PostgreSQL
                with self.postgres_engine.connect() as postgres_conn:
                    # Start transaction
                    trans = postgres_conn.begin()

                    try:
                        # Convert rows to dictionaries with only common columns
                        rows_to_insert = []
                        for row in sqlite_data:
                            row_dict = {}
                            for i, col_name in enumerate(column_names):
                                if col_name in common_columns:
                                    row_dict[col_name] = row[i]
                            rows_to_insert.append(row_dict)

                        # Batch insert
                        if rows_to_insert:
                            postgres_conn.execute(postgres_table.insert(), rows_to_insert)

                        trans.commit()
                        print(f"Successfully migrated {len(rows_to_insert)} rows")

                        # Update sequence for tables with auto-increment primary keys
                        self.update_sequence(table_name)

                        return True

                    except Exception as e:
                        trans.rollback()
                        print(f"Error inserting data into {table_name}: {e}")
                        import traceback
                        traceback.print_exc()
                        raise

        except Exception as e:
            print(f"Error migrating table {table_name}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_sequence(self, table_name):
        """Update PostgreSQL sequence for auto-increment columns"""
        try:
            with self.postgres_engine.connect() as conn:
                # Get the maximum ID from the table
                result = conn.execute(text(f'SELECT MAX(id) FROM "{table_name}"'))
                max_id = result.scalar()

                if max_id is not None and max_id > 0:
                    # Update the sequence
                    sequence_name = f"{table_name}_id_seq"
                    conn.execute(text(f"SELECT setval('{sequence_name}', {max_id}, true)"))
                    conn.commit()
                    print(f"Updated sequence {sequence_name} to {max_id}")

        except Exception as e:
            # Some tables might not have sequences, which is fine
            pass

    def verify_migration(self, table_name):
        """Verify that migration was successful"""
        sqlite_count = self.get_row_count(self.sqlite_engine, table_name)
        postgres_count = self.get_row_count(self.postgres_engine, table_name)

        if sqlite_count == postgres_count:
            print(f"Verification PASSED: {table_name} ({postgres_count} rows)")
            return True
        else:
            print(f"Verification FAILED: {table_name}")
            print(f"  SQLite: {sqlite_count} rows")
            print(f"  PostgreSQL: {postgres_count} rows")
            return False

    def migrate_all(self):
        """Migrate all tables from SQLite to PostgreSQL"""
        print("\n" + "="*60)
        print("Starting Database Migration")
        print(f"From: {self.sqlite_url}")
        print(f"To:   {self.postgres_url}")
        print("="*60)

        # Create PostgreSQL schema
        if not self.create_postgres_schema():
            print("Failed to create PostgreSQL schema. Aborting migration.")
            return False

        # Get all tables
        tables = self.get_table_names()

        if not tables:
            print("No tables found in SQLite database")
            return False

        print(f"\nFound {len(tables)} tables to migrate:")
        for table in tables:
            print(f"  - {table}")

        # Migrate each table
        print("\n" + "="*60)
        print("Migrating Tables")
        print("="*60)

        success_count = 0
        failed_tables = []

        # Define migration order to respect foreign key constraints
        # Core tables first
        migration_order = [
            'users',
            'user_security_settings',
            'sessions',
            'user_api_keys',
            'login_activity',
            'security_audit',
            'rate_limit_log',
            'articles',
            'posts',
            'instagram_images',
            'image_generation_quota',
            'settings',
            'ab_experiments',
            'ab_assignments',
            'ab_conversions'
        ]

        # Migrate tables in order
        for table_name in migration_order:
            if table_name in tables:
                if self.migrate_table(table_name):
                    success_count += 1
                else:
                    failed_tables.append(table_name)

        # Migrate any remaining tables not in the predefined order
        for table_name in tables:
            if table_name not in migration_order:
                print(f"\nMigrating additional table: {table_name}")
                if self.migrate_table(table_name):
                    success_count += 1
                else:
                    failed_tables.append(table_name)

        # Verification
        print("\n" + "="*60)
        print("Verifying Migration")
        print("="*60)

        verification_passed = 0
        verification_failed = []

        for table_name in tables:
            if self.verify_migration(table_name):
                verification_passed += 1
            else:
                verification_failed.append(table_name)

        # Summary
        print("\n" + "="*60)
        print("Migration Summary")
        print("="*60)
        print(f"Total tables: {len(tables)}")
        print(f"Successfully migrated: {success_count}")
        print(f"Failed: {len(failed_tables)}")

        if failed_tables:
            print(f"\nFailed tables: {', '.join(failed_tables)}")

        print(f"\nVerification passed: {verification_passed}")
        print(f"Verification failed: {len(verification_failed)}")

        if verification_failed:
            print(f"Failed verification: {', '.join(verification_failed)}")

        # Final status
        if len(failed_tables) == 0:
            print("\n" + "="*60)
            print("SUCCESS: All tables migrated successfully!")
            print("="*60)
            return True
        else:
            print("\n" + "="*60)
            print("WARNING: Migration completed with some errors")
            print("="*60)
            return False

    def close(self):
        """Close database connections"""
        self.sqlite_session.close()
        self.postgres_session.close()
        self.sqlite_engine.dispose()
        self.postgres_engine.dispose()


def main():
    """Main migration function"""
    # Database URLs
    sqlite_url = "sqlite:///./ai_news.db"
    postgres_url = "postgresql://localhost:5432/ai_news_local"

    # Check if SQLite database exists
    if not os.path.exists("ai_news.db"):
        print("Error: SQLite database 'ai_news.db' not found")
        print("Please ensure the database file exists in the current directory")
        sys.exit(1)

    # Create migration instance
    migration = DatabaseMigration(sqlite_url, postgres_url)

    try:
        # Run migration
        success = migration.migrate_all()

        # Close connections
        migration.close()

        if success:
            print("\n" + "="*60)
            print("Next Steps:")
            print("="*60)
            print("1. Update your .env file:")
            print("   DATABASE_URL=postgresql://localhost:5432/ai_news_local")
            print("2. Run indexes script:")
            print("   psql ai_news_local < scripts/add_indexes.sql")
            print("3. Restart your backend server")
            print("="*60)
            sys.exit(0)
        else:
            print("\n" + "="*60)
            print("Migration completed but some tables had errors.")
            print("Please review the logs above.")
            print("="*60)
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nMigration interrupted by user")
        migration.close()
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error during migration: {e}")
        import traceback
        traceback.print_exc()
        migration.close()
        sys.exit(1)


if __name__ == "__main__":
    main()
