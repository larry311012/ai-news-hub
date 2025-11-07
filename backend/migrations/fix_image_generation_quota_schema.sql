-- ============================================================================
-- Migration: Fix image_generation_quota schema mismatch
-- Date: 2025-10-23
-- Issue: SQLAlchemy model expects different column names than database has
--
-- Changes:
--   - Rename 'date' to 'quota_reset_date'
--   - Rename 'images_generated' to 'images_generated_today'
--   - Add 'daily_limit' column (default 50)
--   - Add 'total_images_generated' column
--   - Change user_id constraint from unique to composite (user_id, quota_reset_date)
-- ============================================================================

-- Backup command (run before this script):
-- .backup /Users/ranhui/ai_post/web/backend/ai_news.db.backup

BEGIN TRANSACTION;

-- ============================================================================
-- STEP 1: Create new table with correct schema
-- ============================================================================

CREATE TABLE image_generation_quota_new (
    id INTEGER NOT NULL PRIMARY KEY,
    user_id INTEGER NOT NULL,

    -- Daily quota tracking
    daily_limit INTEGER NOT NULL DEFAULT 50,
    images_generated_today INTEGER NOT NULL DEFAULT 0,
    quota_reset_date DATETIME NOT NULL,

    -- Lifetime tracking
    total_images_generated INTEGER NOT NULL DEFAULT 0,
    total_cost_usd FLOAT NOT NULL DEFAULT 0.0,

    -- Timestamps
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,

    -- One record per user per day
    UNIQUE(user_id, quota_reset_date)
);

-- ============================================================================
-- STEP 2: Copy existing data with column mapping
-- ============================================================================

INSERT INTO image_generation_quota_new
    (id, user_id, daily_limit, images_generated_today, quota_reset_date,
     total_images_generated, total_cost_usd, created_at, updated_at)
SELECT
    id,
    user_id,
    50 as daily_limit,  -- Default value for all existing records
    COALESCE(images_generated, 0) as images_generated_today,
    date as quota_reset_date,  -- Rename column
    COALESCE(images_generated, 0) as total_images_generated,  -- Initialize from current
    COALESCE(total_cost_usd, 0.0) as total_cost_usd,
    COALESCE(created_at, CURRENT_TIMESTAMP) as created_at,
    COALESCE(updated_at, CURRENT_TIMESTAMP) as updated_at
FROM image_generation_quota;

-- ============================================================================
-- STEP 3: Drop old table and rename new table
-- ============================================================================

DROP TABLE image_generation_quota;

ALTER TABLE image_generation_quota_new RENAME TO image_generation_quota;

-- ============================================================================
-- STEP 4: Recreate indexes
-- ============================================================================

CREATE INDEX ix_image_generation_quota_user_id
    ON image_generation_quota (user_id);

CREATE INDEX ix_image_generation_quota_quota_reset_date
    ON image_generation_quota (quota_reset_date);

-- ============================================================================
-- COMMIT TRANSACTION
-- ============================================================================

COMMIT;

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

SELECT '============================================================================' as '';
SELECT 'MIGRATION COMPLETED SUCCESSFULLY' as status;
SELECT '============================================================================' as '';

SELECT 'Verifying schema...' as '';
PRAGMA table_info(image_generation_quota);

SELECT '' as '';
SELECT 'Verifying indexes...' as '';
SELECT name, sql FROM sqlite_master
WHERE type = 'index' AND tbl_name = 'image_generation_quota';

SELECT '' as '';
SELECT 'Checking data...' as '';
SELECT
    COUNT(*) as total_records,
    SUM(images_generated_today) as total_images_today,
    SUM(total_images_generated) as total_images_all_time,
    SUM(total_cost_usd) as total_cost
FROM image_generation_quota;

SELECT '' as '';
SELECT 'Migration complete! Restart backend server to apply changes.' as '';
SELECT '============================================================================' as '';
