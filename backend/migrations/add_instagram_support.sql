-- Migration: Add Instagram Support to AI News Aggregator
-- Created: 2025-10-22
-- Description: Adds Instagram image generation and publishing capabilities
-- Database: SQLite

BEGIN TRANSACTION;

-- ============================================================================
-- 1. UPDATE POSTS TABLE
-- ============================================================================

-- Add Instagram-specific columns to existing posts table
ALTER TABLE posts ADD COLUMN instagram_caption TEXT;
ALTER TABLE posts ADD COLUMN instagram_image_url TEXT;
ALTER TABLE posts ADD COLUMN instagram_image_prompt TEXT;  -- For debugging/regeneration
ALTER TABLE posts ADD COLUMN instagram_hashtags TEXT;  -- JSON array stored as text
ALTER TABLE posts ADD COLUMN instagram_url TEXT;  -- Published post URL
ALTER TABLE posts ADD COLUMN instagram_post_id TEXT;  -- Instagram media ID

-- ============================================================================
-- 2. CREATE INSTAGRAM_IMAGES TABLE
-- ============================================================================

-- Table for caching and tracking generated images
CREATE TABLE IF NOT EXISTS instagram_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    article_id INTEGER,  -- Optional: link to source article

    -- Image metadata
    prompt TEXT NOT NULL,  -- DALL-E prompt used for generation
    prompt_hash VARCHAR(64),  -- SHA-256 hash for deduplication

    -- Storage paths
    image_url TEXT NOT NULL,  -- Full image URL (local path or S3 URL)
    thumbnail_url TEXT,  -- Thumbnail preview URL

    -- Image specifications
    width INTEGER,
    height INTEGER,
    format VARCHAR(10),  -- png, jpg, webp
    file_size_bytes INTEGER,

    -- AI generation metadata
    ai_provider VARCHAR(50) DEFAULT 'openai',  -- openai, stable-diffusion
    ai_model VARCHAR(100),  -- dall-e-3, dall-e-2, sd-xl-1.0
    generation_params TEXT,  -- JSON stored as TEXT in SQLite

    -- Usage tracking
    times_used INTEGER DEFAULT 1,
    last_used_at DATETIME,

    -- Status
    status VARCHAR(50) DEFAULT 'active',  -- active, deleted, failed, expired
    error_message TEXT,

    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key constraints
    FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (article_id) REFERENCES articles (id) ON DELETE SET NULL
);

-- Create indexes for performance
CREATE INDEX idx_instagram_images_user_created ON instagram_images (user_id, created_at);
CREATE INDEX idx_instagram_images_prompt_hash ON instagram_images (prompt_hash);
CREATE INDEX idx_instagram_images_status ON instagram_images (status);
CREATE INDEX idx_instagram_images_post ON instagram_images (post_id);
CREATE INDEX idx_instagram_images_article ON instagram_images (article_id);

-- ============================================================================
-- 3. CREATE IMAGE_GENERATION_JOBS TABLE
-- ============================================================================

-- Table for tracking async image generation jobs
CREATE TABLE IF NOT EXISTS image_generation_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(64) UNIQUE NOT NULL,  -- Unique job identifier
    post_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,

    -- Generation parameters
    prompt TEXT NOT NULL,
    style VARCHAR(50),  -- modern, minimalist, vibrant, professional
    custom_prompt TEXT,  -- User override
    ai_provider VARCHAR(50) DEFAULT 'openai',
    ai_model VARCHAR(100),

    -- Status tracking
    status VARCHAR(50) DEFAULT 'queued',  -- queued, processing, completed, failed, cancelled
    progress INTEGER DEFAULT 0,  -- 0-100
    current_step VARCHAR(255),

    -- Results
    image_id INTEGER,  -- FK to instagram_images
    image_url TEXT,
    thumbnail_url TEXT,
    error_message TEXT,

    -- Performance metrics
    generation_time_seconds REAL,

    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    started_at DATETIME,
    completed_at DATETIME,

    -- Foreign key constraints
    FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (image_id) REFERENCES instagram_images (id) ON DELETE SET NULL
);

-- Create indexes for job tracking
CREATE INDEX idx_image_jobs_status ON image_generation_jobs (status);
CREATE INDEX idx_image_jobs_user ON image_generation_jobs (user_id, created_at);
CREATE INDEX idx_image_jobs_job_id ON image_generation_jobs (job_id);
CREATE INDEX idx_image_jobs_post ON image_generation_jobs (post_id);

-- ============================================================================
-- 4. CREATE IMAGE_GENERATION_QUOTA TABLE
-- ============================================================================

-- Table for tracking user quotas and rate limiting
CREATE TABLE IF NOT EXISTS image_generation_quota (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,

    -- Quota tracking
    daily_limit INTEGER DEFAULT 50,  -- Max images per day
    images_generated_today INTEGER DEFAULT 0,
    quota_reset_date DATE NOT NULL,

    -- Usage statistics
    total_images_generated INTEGER DEFAULT 0,
    total_api_cost_usd REAL DEFAULT 0.0,  -- Track costs

    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

    -- Foreign key constraints
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,

    -- Unique constraint
    UNIQUE (user_id)
);

-- Create index for quota lookups
CREATE INDEX idx_quota_user_reset ON image_generation_quota (user_id, quota_reset_date);

-- ============================================================================
-- 5. UPDATE SOCIAL_MEDIA_POSTS TABLE (if needed)
-- ============================================================================

-- Note: social_media_posts table already exists and supports Instagram
-- No changes needed, but verify it has these columns:
--   - platform (includes 'instagram')
--   - content (will store caption)
--   - platform_url (Instagram permalink)
--   - platform_post_id (Instagram media ID)

-- ============================================================================
-- 6. CREATE INSTAGRAM_PUBLISH_LOG TABLE
-- ============================================================================

-- Detailed logging for Instagram publishing events
CREATE TABLE IF NOT EXISTS instagram_publish_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    image_id INTEGER,

    -- Publishing details
    caption TEXT,
    image_url TEXT,
    container_id VARCHAR(255),  -- Instagram creation ID
    media_id VARCHAR(255),  -- Published media ID
    permalink TEXT,

    -- Status
    status VARCHAR(50) NOT NULL,  -- initiated, container_created, published, failed
    error_code VARCHAR(100),
    error_message TEXT,

    -- Performance metrics
    container_creation_time_seconds REAL,
    publish_time_seconds REAL,
    total_time_seconds REAL,

    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    published_at DATETIME,

    -- Foreign key constraints
    FOREIGN KEY (post_id) REFERENCES posts (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (image_id) REFERENCES instagram_images (id) ON DELETE SET NULL
);

-- Create indexes for publish log
CREATE INDEX idx_instagram_publish_user ON instagram_publish_log (user_id, created_at);
CREATE INDEX idx_instagram_publish_status ON instagram_publish_log (status);
CREATE INDEX idx_instagram_publish_post ON instagram_publish_log (post_id);

-- ============================================================================
-- 7. INITIALIZE DEFAULT DATA
-- ============================================================================

-- Set default quotas for existing users
INSERT INTO image_generation_quota (user_id, daily_limit, quota_reset_date)
SELECT id, 50, DATE('now')
FROM users
WHERE id NOT IN (SELECT user_id FROM image_generation_quota);

-- ============================================================================
-- 8. CREATE TRIGGERS FOR AUTOMATIC UPDATES
-- ============================================================================

-- Trigger to update instagram_images.updated_at on modification
CREATE TRIGGER update_instagram_images_timestamp
AFTER UPDATE ON instagram_images
FOR EACH ROW
BEGIN
    UPDATE instagram_images
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

-- Trigger to update quota reset date
CREATE TRIGGER reset_daily_quota
AFTER UPDATE ON image_generation_quota
FOR EACH ROW
WHEN NEW.quota_reset_date < DATE('now')
BEGIN
    UPDATE image_generation_quota
    SET images_generated_today = 0,
        quota_reset_date = DATE('now')
    WHERE id = NEW.id;
END;

-- Trigger to increment usage count when image is reused
CREATE TRIGGER increment_image_usage
AFTER UPDATE OF last_used_at ON instagram_images
FOR EACH ROW
WHEN NEW.last_used_at > OLD.last_used_at
BEGIN
    UPDATE instagram_images
    SET times_used = times_used + 1
    WHERE id = NEW.id;
END;

-- ============================================================================
-- 9. MIGRATION VERIFICATION
-- ============================================================================

-- Verify tables were created successfully
SELECT 'Migration completed successfully!' AS status;

-- Show table counts
SELECT
    (SELECT COUNT(*) FROM instagram_images) AS instagram_images_count,
    (SELECT COUNT(*) FROM image_generation_jobs) AS jobs_count,
    (SELECT COUNT(*) FROM image_generation_quota) AS quota_count,
    (SELECT COUNT(*) FROM instagram_publish_log) AS publish_log_count;

COMMIT;

-- ============================================================================
-- ROLLBACK SCRIPT (save for emergency rollback)
-- ============================================================================

/*
BEGIN TRANSACTION;

-- Drop triggers
DROP TRIGGER IF EXISTS update_instagram_images_timestamp;
DROP TRIGGER IF EXISTS reset_daily_quota;
DROP TRIGGER IF EXISTS increment_image_usage;

-- Drop tables
DROP TABLE IF EXISTS instagram_publish_log;
DROP TABLE IF EXISTS image_generation_quota;
DROP TABLE IF EXISTS image_generation_jobs;
DROP TABLE IF EXISTS instagram_images;

-- Remove columns from posts (SQLite doesn't support DROP COLUMN, so would need table recreation)
-- This is complex in SQLite, better to keep columns with NULL values

COMMIT;
*/
