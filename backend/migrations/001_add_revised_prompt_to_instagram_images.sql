-- Migration: Add revised_prompt column to instagram_images table
-- Date: 2025-10-23
-- Issue: Missing revised_prompt column causing "no such column" error
--
-- This migration adds the revised_prompt column that stores DALL-E's
-- revised/enhanced version of the user's prompt.

-- Add revised_prompt column
ALTER TABLE instagram_images ADD COLUMN revised_prompt TEXT;

-- Create index for potential searches on revised_prompt
CREATE INDEX IF NOT EXISTS idx_instagram_images_revised_prompt ON instagram_images(revised_prompt);

-- Verify the column was added successfully
-- (This is a comment, but you can run this query after migration to verify)
-- SELECT COUNT(*) as has_revised_prompt FROM pragma_table_info('instagram_images') WHERE name='revised_prompt';
