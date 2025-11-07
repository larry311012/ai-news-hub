-- ============================================================================
-- Database Migration: Mobile-Optimized Indexes for iOS App
-- ============================================================================
-- Task 1.8: Database Indexing for Mobile (iOS App Phase 1)
--
-- Purpose: Optimize database queries for mobile app to ensure all
--          authentication and data queries complete in < 50ms
--
-- Target Queries:
--   1. User login by email
--   2. User's recent posts (with pagination)
--   3. OAuth credential lookups
--   4. Active social media connections
--
-- Acceptance Criteria:
--   - All auth queries < 50ms
--   - No N+1 queries
--   - Composite indexes for common patterns
-- ============================================================================

-- Start transaction
BEGIN;

-- ============================================================================
-- INDEX 1: users(email) - Fast Login Lookups
-- ============================================================================
CREATE UNIQUE INDEX IF NOT EXISTS ix_users_email ON users(email);

-- ============================================================================
-- INDEX 2: posts(user_id, created_at) - User's Recent Posts
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_posts_user_id_created ON posts(user_id, created_at DESC);

-- ============================================================================
-- INDEX 3: user_oauth_credentials(user_id, platform, is_active)
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_user_platform_active
ON user_oauth_credentials(user_id, platform, is_active);

-- ============================================================================
-- INDEX 4: social_media_connections(user_id, is_active) - NEW INDEX
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_social_connections_user_active
ON social_media_connections(user_id, is_active) WHERE is_active = true;

-- ============================================================================
-- INDEX 5: sessions(user_id, expires_at) - NEW INDEX
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_sessions_user_expires ON sessions(user_id, expires_at);

-- ============================================================================
-- INDEX 6: sessions(token) - Token Lookup
-- ============================================================================
CREATE UNIQUE INDEX IF NOT EXISTS ix_sessions_token ON sessions(token);

-- ============================================================================
-- ANALYZE: Update Query Planner Statistics
-- ============================================================================
ANALYZE users;
ANALYZE posts;
ANALYZE user_oauth_credentials;
ANALYZE social_media_connections;
ANALYZE sessions;

COMMIT;
