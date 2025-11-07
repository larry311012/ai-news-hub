-- ============================================
-- Performance Indexes for Query Optimization
-- ============================================
-- Created: 2025-10-27
-- Purpose: Add strategic indexes to eliminate N+1 problems and improve query performance
-- Target: Achieve 95%+ queries under 100ms

-- Note: Using CONCURRENTLY to avoid locking tables during index creation
-- This allows normal operations to continue while indexes are being built

\timing on

-- ============================================
-- POSTS TABLE OPTIMIZATIONS
-- ============================================

-- Composite index for most common query: user's posts filtered by status, ordered by date
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_user_status_created
    ON posts(user_id, status, created_at DESC);
-- Covers: SELECT * FROM posts WHERE user_id=? AND status=? ORDER BY created_at DESC

-- Partial index for published posts queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_published_date
    ON posts(published_at DESC NULLS LAST)
    WHERE published_at IS NOT NULL AND status = 'published';
-- Covers: SELECT * FROM posts WHERE published_at IS NOT NULL ORDER BY published_at DESC

-- GIN index for platform array searches (if using array queries)
-- Note: Only create if posts.platforms is actually queried with array operators
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_platforms_gin
--     ON posts USING GIN(platforms);

-- Partial indexes for specific status queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_draft_user
    ON posts(user_id, created_at DESC)
    WHERE status = 'draft';
-- Fast draft posts lookup

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_processing_created
    ON posts(created_at DESC)
    WHERE status = 'processing';
-- Monitor stuck processing jobs

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_failed_user
    ON posts(user_id, created_at DESC)
    WHERE status = 'failed';
-- Failed posts for user


-- ============================================
-- ARTICLES TABLE OPTIMIZATIONS
-- ============================================

-- Composite index for source + date queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_articles_source_published
    ON articles(source, published DESC);
-- Covers: SELECT * FROM articles WHERE source=? ORDER BY published DESC

-- Composite index for user's articles
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_articles_user_published
    ON articles(user_id, published DESC)
    WHERE user_id IS NOT NULL;
-- Covers: SELECT * FROM articles WHERE user_id=? ORDER BY published DESC

-- Full-text search on titles (requires pg_trgm extension)
-- Uncomment if pg_trgm extension is installed
-- CREATE EXTENSION IF NOT EXISTS pg_trgm;
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_articles_title_trgm
--     ON articles USING gin(title gin_trgm_ops);


-- ============================================
-- SOCIAL MEDIA CONNECTIONS OPTIMIZATIONS
-- ============================================

-- Composite index for active connections lookup
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_social_connections_user_platform_active
    ON social_media_connections(user_id, platform)
    WHERE is_active = true;
-- Covers: SELECT * FROM social_media_connections WHERE user_id=? AND platform=? AND is_active=true

-- Index for checking expired tokens
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_social_connections_expires
    ON social_media_connections(expires_at)
    WHERE is_active = true AND expires_at IS NOT NULL;
-- Covers: SELECT * FROM social_media_connections WHERE is_active=true AND expires_at < NOW()


-- ============================================
-- SOCIAL MEDIA POSTS OPTIMIZATIONS
-- ============================================

-- Composite index for platform-specific post status
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_social_posts_post_platform_status
    ON social_media_posts(post_id, platform, status);
-- Covers: SELECT * FROM social_media_posts WHERE post_id=? AND platform=?

-- Index for user's published posts timeline
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_social_posts_user_published
    ON social_media_posts(user_id, published_at DESC)
    WHERE published_at IS NOT NULL;
-- Covers: SELECT * FROM social_media_posts WHERE user_id=? AND published_at IS NOT NULL ORDER BY published_at DESC

-- Index for pending posts that need to be processed
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_social_posts_status_created
    ON social_media_posts(status, created_at DESC)
    WHERE status = 'pending';
-- Covers: SELECT * FROM social_media_posts WHERE status='pending' ORDER BY created_at DESC


-- ============================================
-- USER API KEYS OPTIMIZATIONS
-- ============================================

-- Note: Composite index is defined in the model via __table_args__
-- If not created, uncomment this:
-- CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_api_keys_user_provider_active
--     ON user_api_keys(user_id, provider)
--     WHERE is_active = true;


-- ============================================
-- SESSIONS OPTIMIZATIONS
-- ============================================

-- Composite index for active session lookups
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_user_expires_active
    ON sessions(user_id, expires_at DESC)
    WHERE expires_at > NOW();
-- Covers: SELECT * FROM sessions WHERE user_id=? AND expires_at > NOW() ORDER BY expires_at DESC

-- Index for session cleanup jobs
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_expires_cleanup
    ON sessions(expires_at)
    WHERE expires_at < NOW();
-- Covers: DELETE FROM sessions WHERE expires_at < NOW()


-- ============================================
-- INSTAGRAM IMAGES OPTIMIZATIONS
-- ============================================

-- Composite index for user's active images
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_instagram_images_user_status_created
    ON instagram_images(user_id, status, created_at DESC)
    WHERE status = 'active';
-- Covers: SELECT * FROM instagram_images WHERE user_id=? AND status='active' ORDER BY created_at DESC


-- ============================================
-- COVERING INDEXES (Include Additional Columns)
-- ============================================

-- Covering index for posts list queries (avoids table lookups)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_posts_user_covering
    ON posts(user_id, created_at DESC)
    INCLUDE (status, article_title, published_at);
-- Covering index reduces need to access heap table


-- ============================================
-- ANALYZE TABLES TO UPDATE STATISTICS
-- ============================================

ANALYZE posts;
ANALYZE articles;
ANALYZE social_media_connections;
ANALYZE social_media_posts;
ANALYZE user_api_keys;
ANALYZE sessions;
ANALYZE instagram_images;

-- ============================================
-- REPORT: Index Usage Statistics
-- ============================================

\echo ''
\echo '============================================'
\echo 'INDEX CREATION COMPLETE'
\echo '============================================'
\echo ''
\echo 'Index Usage Statistics (ordered by scan count):'
\echo ''

SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan as times_used,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND tablename IN ('posts', 'articles', 'social_media_connections', 'social_media_posts', 'user_api_keys', 'sessions', 'instagram_images')
ORDER BY idx_scan DESC, tablename
LIMIT 30;

\echo ''
\echo 'Unused Indexes (never scanned):'
\echo ''

SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND idx_scan = 0
  AND indexname NOT LIKE '%_pkey'
ORDER BY pg_relation_size(indexrelid) DESC
LIMIT 10;

\echo ''
\echo 'Table Sizes:'
\echo ''

SELECT
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) as indexes_size
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('posts', 'articles', 'social_media_connections', 'social_media_posts', 'user_api_keys', 'sessions', 'instagram_images')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

\echo ''
\echo '============================================'
\echo 'OPTIMIZATION RECOMMENDATIONS'
\echo '============================================'
\echo ''
\echo '1. Enable SQL_DEBUG=true in .env to monitor query performance'
\echo '2. Use OptimizedQuery helpers in utils/query_helpers.py to avoid N+1 problems'
\echo '3. Monitor /api/health/database/query-stats endpoint for slow queries'
\echo '4. Review unused indexes after 1 week and consider dropping them'
\echo '5. Run VACUUM ANALYZE monthly to maintain query planner statistics'
\echo ''
