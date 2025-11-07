-- ============================================================================
-- DATABASE SCHEMA FIX: image_generation_quota Table
-- ============================================================================
--
-- PROBLEM:
-- The code expects a per-user quota tracking system with daily limits,
-- but the database has an old daily-record-based schema.
--
-- CURRENT SCHEMA (OLD):
--   - id, user_id, date, images_generated, total_cost_usd, created_at, updated_at
--   - Creates one record per day per user
--   - Columns: 'date' (not 'quota_reset_date')
--   - Columns: 'images_generated' (not 'images_generated_today')
--   - Missing: 'daily_limit', 'total_images_generated'
--
-- EXPECTED SCHEMA (NEW):
--   - One record per user (not per day)
--   - Columns: daily_limit, images_generated_today, quota_reset_date
--   - Columns: total_images_generated, total_cost_usd
--   - Tracks lifetime stats + today's usage
--
-- ============================================================================

-- Step 1: Backup existing table
CREATE TABLE IF NOT EXISTS image_generation_quota_backup AS
SELECT * FROM image_generation_quota;

-- Step 2: Drop old table
DROP TABLE IF EXISTS image_generation_quota;

-- Step 3: Create new table with correct schema
CREATE TABLE image_generation_quota (
    id INTEGER NOT NULL PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE,

    -- Daily quota tracking
    daily_limit INTEGER DEFAULT 50 NOT NULL,
    images_generated_today INTEGER DEFAULT 0 NOT NULL,
    quota_reset_date DATETIME NOT NULL,

    -- Lifetime statistics
    total_images_generated INTEGER DEFAULT 0 NOT NULL,
    total_cost_usd FLOAT DEFAULT 0.0 NOT NULL,

    -- Timestamps
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Step 4: Create indexes
CREATE INDEX ix_image_generation_quota_user_id ON image_generation_quota (user_id);
CREATE INDEX ix_image_generation_quota_quota_reset_date ON image_generation_quota (quota_reset_date);

-- Step 5: Migrate existing data (if any)
-- Aggregate old daily records into single user records
INSERT INTO image_generation_quota (
    user_id,
    daily_limit,
    images_generated_today,
    quota_reset_date,
    total_images_generated,
    total_cost_usd,
    created_at,
    updated_at
)
SELECT
    user_id,
    50 as daily_limit,  -- Default daily limit
    COALESCE(MAX(CASE WHEN date(date) = date('now') THEN images_generated ELSE 0 END), 0) as images_generated_today,
    datetime('now', '+1 day', 'start of day') as quota_reset_date,  -- Reset at midnight
    COALESCE(SUM(images_generated), 0) as total_images_generated,
    COALESCE(SUM(total_cost_usd), 0.0) as total_cost_usd,
    MIN(created_at) as created_at,
    MAX(updated_at) as updated_at
FROM image_generation_quota_backup
GROUP BY user_id;

-- Step 6: Verify migration
SELECT
    'Migration Summary' as status,
    COUNT(*) as users_migrated,
    SUM(total_images_generated) as total_images,
    SUM(total_cost_usd) as total_cost
FROM image_generation_quota;

-- Step 7: Show sample records
SELECT
    id,
    user_id,
    daily_limit,
    images_generated_today,
    quota_reset_date,
    total_images_generated,
    total_cost_usd
FROM image_generation_quota
LIMIT 5;
