-- ============================================================================
-- Database Indexes for PostgreSQL
-- ============================================================================
-- This script creates performance-optimizing indexes for the AI Post Generator
-- application. These indexes improve query performance for common operations.
--
-- Usage:
--   psql ai_news_local < scripts/add_indexes.sql
--
-- Performance Impact:
--   - Speeds up user lookups by email
--   - Accelerates post filtering by user_id, status, and created_at
--   - Optimizes OAuth credential lookups
--   - Improves social media connection queries
--   - Enhances security audit and activity log searches
-- ============================================================================

-- Note: Most indexes are already created via SQLAlchemy model definitions
-- This script adds additional composite and performance-critical indexes

-- ============================================================================
-- Users Table Indexes
-- ============================================================================
-- Email lookup is already indexed via model (unique=True, index=True)
-- Adding composite indexes for common query patterns

-- Speed up OAuth user lookups
CREATE INDEX IF NOT EXISTS idx_users_oauth_provider_id
ON users(oauth_provider, oauth_id)
WHERE oauth_provider IS NOT NULL;

-- Guest user filtering
CREATE INDEX IF NOT EXISTS idx_users_guest_active
ON users(is_guest, is_active)
WHERE is_guest = TRUE;

-- Admin user queries
CREATE INDEX IF NOT EXISTS idx_users_admin_active
ON users(is_admin, is_active)
WHERE is_admin = TRUE;

-- ============================================================================
-- Posts Table Indexes
-- ============================================================================
-- Core indexes already exist (user_id, status, created_at)
-- Adding composite indexes for dashboard queries

-- User's recent posts (most common query)
CREATE INDEX IF NOT EXISTS idx_posts_user_created
ON posts(user_id, created_at DESC);

-- User's posts by status
CREATE INDEX IF NOT EXISTS idx_posts_user_status
ON posts(user_id, status);

-- Published posts with timestamps
CREATE INDEX IF NOT EXISTS idx_posts_status_published
ON posts(status, published_at DESC NULLS LAST)
WHERE status = 'published';

-- Instagram posts for analytics
CREATE INDEX IF NOT EXISTS idx_posts_instagram_post_id
ON posts(instagram_post_id)
WHERE instagram_post_id IS NOT NULL;

-- ============================================================================
-- Articles Table Indexes
-- ============================================================================
-- User article lookups
CREATE INDEX IF NOT EXISTS idx_articles_user_fetched
ON articles(user_id, fetched_at DESC);

-- Bookmarked articles
CREATE INDEX IF NOT EXISTS idx_articles_user_bookmarked
ON articles(user_id, bookmarked)
WHERE bookmarked = TRUE;

-- Category filtering
CREATE INDEX IF NOT EXISTS idx_articles_category_fetched
ON articles(category, fetched_at DESC)
WHERE category IS NOT NULL;

-- Source filtering
CREATE INDEX IF NOT EXISTS idx_articles_source_fetched
ON articles(source, fetched_at DESC)
WHERE source IS NOT NULL;

-- ============================================================================
-- Sessions Table Indexes
-- ============================================================================
-- Active sessions lookup (most critical for auth)
CREATE INDEX IF NOT EXISTS idx_sessions_user_expires
ON sessions(user_id, expires_at DESC)
WHERE expires_at > NOW();

-- Token expiration cleanup
CREATE INDEX IF NOT EXISTS idx_sessions_expires_at
ON sessions(expires_at)
WHERE expires_at > NOW();

-- Recent activity tracking
CREATE INDEX IF NOT EXISTS idx_sessions_last_activity
ON sessions(user_id, last_activity DESC);

-- ============================================================================
-- User API Keys Table Indexes
-- ============================================================================
-- Provider-based lookups (already has basic index)
-- Adding composite for efficiency
CREATE INDEX IF NOT EXISTS idx_user_api_keys_user_provider
ON user_api_keys(user_id, provider);

-- ============================================================================
-- Instagram Images Table Indexes
-- ============================================================================
-- User's recent images
CREATE INDEX IF NOT EXISTS idx_instagram_images_user_created
ON instagram_images(user_id, created_at DESC);

-- Image cache lookups by prompt hash
CREATE INDEX IF NOT EXISTS idx_instagram_images_prompt_hash_status
ON instagram_images(prompt_hash, status)
WHERE status = 'active';

-- Post association lookups
CREATE INDEX IF NOT EXISTS idx_instagram_images_post_id
ON instagram_images(post_id)
WHERE post_id IS NOT NULL;

-- Article association lookups
CREATE INDEX IF NOT EXISTS idx_instagram_images_article_id
ON instagram_images(article_id)
WHERE article_id IS NOT NULL;

-- ============================================================================
-- Image Generation Quota Table Indexes
-- ============================================================================
-- User quota lookups (already has user_id index)
-- Adding quota reset date for cleanup
CREATE INDEX IF NOT EXISTS idx_image_quota_reset_date
ON image_generation_quota(quota_reset_date);

-- ============================================================================
-- Security Audit Table Indexes
-- ============================================================================
-- Security incident investigation
CREATE INDEX IF NOT EXISTS idx_security_audit_risk_created
ON security_audit(risk_level, created_at DESC)
WHERE risk_level IN ('medium', 'high');

-- User security timeline
CREATE INDEX IF NOT EXISTS idx_security_audit_user_event_created
ON security_audit(user_id, event_type, created_at DESC);

-- Event type analysis
CREATE INDEX IF NOT EXISTS idx_security_audit_event_type_created
ON security_audit(event_type, created_at DESC);

-- IP address tracking
CREATE INDEX IF NOT EXISTS idx_security_audit_ip_created
ON security_audit(ip_address, created_at DESC)
WHERE ip_address IS NOT NULL;

-- ============================================================================
-- Login Activity Table Indexes
-- ============================================================================
-- User login history
CREATE INDEX IF NOT EXISTS idx_login_activity_user_created
ON login_activity(user_id, created_at DESC);

-- Failed login attempts monitoring
CREATE INDEX IF NOT EXISTS idx_login_activity_user_action_success
ON login_activity(user_id, action, success, created_at DESC)
WHERE success = FALSE;

-- Recent activity by action
CREATE INDEX IF NOT EXISTS idx_login_activity_action_created
ON login_activity(action, created_at DESC);

-- ============================================================================
-- Rate Limit Log Table Indexes
-- ============================================================================
-- Rate limit enforcement lookups
CREATE INDEX IF NOT EXISTS idx_rate_limit_identifier_endpoint_window
ON rate_limit_log(identifier, endpoint, window_start DESC);

-- Blocked requests monitoring
CREATE INDEX IF NOT EXISTS idx_rate_limit_blocked_until
ON rate_limit_log(blocked_until)
WHERE blocked_until IS NOT NULL AND blocked_until > NOW();

-- Endpoint analytics
CREATE INDEX IF NOT EXISTS idx_rate_limit_endpoint_window
ON rate_limit_log(endpoint, window_start DESC);

-- ============================================================================
-- A/B Testing Tables Indexes
-- ============================================================================
-- Active experiments
CREATE INDEX IF NOT EXISTS idx_ab_experiments_active
ON ab_experiments(is_active, start_date DESC)
WHERE is_active = TRUE;

-- Assignment lookups
CREATE INDEX IF NOT EXISTS idx_ab_assignments_experiment_variant
ON ab_assignments(experiment_id, variant);

-- Conversion analytics
CREATE INDEX IF NOT EXISTS idx_ab_conversions_experiment_event
ON ab_conversions(experiment_id, event_name, converted_at DESC);

-- ============================================================================
-- Settings Table Indexes
-- ============================================================================
-- Key lookups (already unique indexed)
-- No additional indexes needed

-- ============================================================================
-- User Security Settings Table Indexes
-- ============================================================================
-- User lookups (already unique indexed on user_id)
-- No additional indexes needed

-- ============================================================================
-- Verification
-- ============================================================================
-- List all indexes in the database
-- Uncomment to verify indexes after running this script:
-- SELECT
--     tablename,
--     indexname,
--     indexdef
-- FROM
--     pg_indexes
-- WHERE
--     schemaname = 'public'
-- ORDER BY
--     tablename,
--     indexname;

-- ============================================================================
-- Maintenance Notes
-- ============================================================================
-- 1. Monitor index usage with:
--    SELECT * FROM pg_stat_user_indexes ORDER BY idx_scan DESC;
--
-- 2. Find unused indexes with:
--    SELECT * FROM pg_stat_user_indexes WHERE idx_scan = 0;
--
-- 3. Rebuild indexes periodically (production only):
--    REINDEX DATABASE ai_news_production;
--
-- 4. Analyze tables after bulk operations:
--    ANALYZE users, posts, articles;
--
-- 5. Check index bloat:
--    SELECT * FROM pg_stat_user_indexes WHERE idx_tup_read > 0;
-- ============================================================================

-- Success message
SELECT 'Database indexes created successfully!' AS status;
