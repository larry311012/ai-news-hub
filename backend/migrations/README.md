# Database Migrations

This directory contains SQL migration scripts for the AI Post backend database.

## How to Apply Migrations

### 1. Backup Database First (IMPORTANT!)

```bash
cd /Users/ranhui/ai_post/web/backend
cp ai_news.db ai_news.db.backup
```

### 2. Apply Migration

```bash
sqlite3 ai_news.db < migrations/fix_image_generation_quota_schema.sql
```

### 3. Restart Backend

```bash
# Stop the backend (Ctrl+C if running in terminal)
# Start it again
uvicorn main:app --reload --port 8000
```

## Available Migrations

### fix_image_generation_quota_schema.sql

**Date**: 2025-10-23
**Purpose**: Fix schema mismatch between SQLAlchemy model and database

**What it does**:
- Renames `date` column to `quota_reset_date`
- Renames `images_generated` to `images_generated_today`
- Adds `daily_limit` column (default 50)
- Adds `total_images_generated` column
- Changes unique constraint from `user_id` to composite `(user_id, quota_reset_date)`

**Why it's needed**:
The SQLAlchemy model in `database.py` was updated to use different column names,
but the database was never migrated. This causes 500 errors on all Instagram
image generation endpoints.

**Impact**:
- No data loss
- Existing quota records preserved
- Zero downtime if applied during maintenance window

**Rollback**:
If something goes wrong, restore from backup:
```bash
cp ai_news.db.backup ai_news.db
```

## Migration Checklist

Before applying any migration:

- [ ] Backup database
- [ ] Read migration script
- [ ] Test on development database first (if available)
- [ ] Stop backend server
- [ ] Apply migration
- [ ] Verify schema with `PRAGMA table_info(table_name)`
- [ ] Start backend server
- [ ] Test affected endpoints
- [ ] Monitor logs for errors

## Future: Alembic Setup

Consider setting up Alembic for version-controlled migrations:

```bash
pip install alembic
alembic init alembic
# Configure alembic.ini and env.py
alembic revision --autogenerate -m "message"
alembic upgrade head
```

This will provide:
- Automatic migration generation
- Version control
- Rollback capability
- Better tracking of schema changes
