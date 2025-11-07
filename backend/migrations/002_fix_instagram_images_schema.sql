-- Migration: Fix instagram_images table schema mismatches
-- Date: 2025-10-23
-- Issue: Schema mismatch between model and database causing SQLite errors
--
-- Problems found:
-- 1. post_id is NOT NULL in DB but nullable=True in model
-- 2. user_id foreign key missing CASCADE on delete
-- 3. revised_prompt column exists but may have issues
--
-- SQLite doesn't support ALTER COLUMN, so we need to recreate the table

-- Begin transaction
BEGIN TRANSACTION;

-- Step 1: Create new table with correct schema
CREATE TABLE instagram_images_new (
    id INTEGER NOT NULL,
    post_id INTEGER,  -- Changed to nullable
    user_id INTEGER NOT NULL,
    article_id INTEGER,
    prompt TEXT NOT NULL,
    prompt_hash VARCHAR(64),
    image_url TEXT NOT NULL,
    thumbnail_url TEXT,
    width INTEGER,
    height INTEGER,
    format VARCHAR(10),
    file_size_bytes INTEGER,
    ai_provider VARCHAR(50),
    ai_model VARCHAR(100),
    generation_params TEXT,
    revised_prompt TEXT,  -- In correct position now
    times_used INTEGER,
    last_used_at DATETIME,
    status VARCHAR(50),
    error_message TEXT,
    created_at DATETIME,
    updated_at DATETIME,
    PRIMARY KEY (id),
    FOREIGN KEY(post_id) REFERENCES posts (id) ON DELETE SET NULL,
    FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY(article_id) REFERENCES articles (id) ON DELETE SET NULL
);

-- Step 2: Copy data from old table to new table
INSERT INTO instagram_images_new (
    id, post_id, user_id, article_id, prompt, prompt_hash,
    image_url, thumbnail_url, width, height, format, file_size_bytes,
    ai_provider, ai_model, generation_params, revised_prompt,
    times_used, last_used_at, status, error_message,
    created_at, updated_at
)
SELECT
    id, post_id, user_id, article_id, prompt, prompt_hash,
    image_url, thumbnail_url, width, height, format, file_size_bytes,
    ai_provider, ai_model, generation_params, revised_prompt,
    times_used, last_used_at, status, error_message,
    created_at, updated_at
FROM instagram_images;

-- Step 3: Drop old table
DROP TABLE instagram_images;

-- Step 4: Rename new table to original name
ALTER TABLE instagram_images_new RENAME TO instagram_images;

-- Step 5: Recreate indexes
CREATE INDEX ix_instagram_images_id ON instagram_images (id);
CREATE INDEX ix_instagram_images_post_id ON instagram_images (post_id);
CREATE INDEX ix_instagram_images_user_id ON instagram_images (user_id);
CREATE INDEX ix_instagram_images_article_id ON instagram_images (article_id);
CREATE INDEX ix_instagram_images_prompt_hash ON instagram_images (prompt_hash);
CREATE INDEX idx_instagram_images_status ON instagram_images(status);
CREATE INDEX idx_instagram_images_created ON instagram_images(created_at DESC);

-- Commit transaction
COMMIT;

-- Verify the migration
SELECT 'Migration completed successfully!' as status;
