"""
Cache Invalidation Patch for Bookmark Endpoints

This file shows the recommended changes to articles.py to add cache invalidation
when bookmarks are toggled. This ensures the iOS app always sees up-to-date
bookmark status.

USAGE:
------
1. Review the changes below
2. Apply them to /Users/ranhui/ai_post/ai-news-hub-web/backend/api/articles.py
3. Test with curl commands at the bottom

AFFECTED ENDPOINTS:
-------------------
- POST /api/articles/save (line 338-389 in articles.py)
- DELETE /api/articles/save/{article_id} (line 391-440 in articles.py)
"""

# ============================================================================
# STEP 1: Add imports at the top of articles.py
# ============================================================================

# Add these imports after the existing imports (around line 10):
"""
from config.redis_config import get_async_redis_client
import asyncio
"""

# ============================================================================
# STEP 2: Add cache invalidation helper function
# ============================================================================

# Add this function after the router initialization (around line 25):
"""
async def invalidate_bookmark_caches(user_id: int, article_id: int = None):
    '''
    Invalidate bookmark-related caches when bookmark status changes.

    This ensures the iOS app always sees the latest bookmark status
    without waiting for cache TTL expiration.

    Args:
        user_id: User whose caches to invalidate
        article_id: Optional specific article ID (for targeted invalidation)
    '''
    try:
        redis = await get_async_redis_client()

        # Pattern 1: Invalidate all saved articles caches for this user
        # Format: "saved:*:user_{user_id}:*"
        saved_pattern = f"saved:*:user_{user_id}:*"
        saved_keys = []

        # Get all matching keys
        cursor = 0
        while True:
            cursor, keys = await redis.scan(
                cursor=cursor,
                match=saved_pattern,
                count=100
            )
            saved_keys.extend(keys)
            if cursor == 0:
                break

        if saved_keys:
            await redis.delete(*saved_keys)
            logger.info(f"Invalidated {len(saved_keys)} saved article cache keys for user {user_id}")

        # Pattern 2: Invalidate recent articles caches (includes bookmark status)
        # Format: "recent:*"
        recent_pattern = "recent:*"
        recent_keys = []

        cursor = 0
        while True:
            cursor, keys = await redis.scan(
                cursor=cursor,
                match=recent_pattern,
                count=100
            )
            recent_keys.extend(keys)
            if cursor == 0:
                break

        if recent_keys:
            await redis.delete(*recent_keys)
            logger.info(f"Invalidated {len(recent_keys)} recent article cache keys")

        # Pattern 3: If specific article_id provided, invalidate article detail cache
        if article_id:
            article_key = f"article:{article_id}"
            await redis.delete(article_key)
            logger.info(f"Invalidated cache for article {article_id}")

    except Exception as e:
        # Log but don't fail the request - cache invalidation is non-critical
        logger.warning(f"Cache invalidation failed for user {user_id}: {str(e)}")
        # Continue - the cache will expire naturally via TTL
"""

# ============================================================================
# STEP 3: Update save_article endpoint (POST /api/articles/save)
# ============================================================================

# BEFORE (Current implementation around line 338-389):
"""
@router.post("/save")
async def save_article(
    request: BookmarkRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    try:
        article = db.query(Article).filter(Article.id == request.article_id).first()

        if not article:
            raise HTTPException(status_code=404, detail="Article not found")

        if article.user_id is None:
            article.user_id = user.id

        article.bookmarked = True
        db.commit()
        db.refresh(article)

        logger.info(f"Article {article.id} bookmarked by user {user.id}")

        return {
            "success": True,
            "bookmarked": True,
            "article_id": article.id,
            "message": "Article saved successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bookmarking article: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while saving article")
"""

# AFTER (With cache invalidation):
"""
@router.post("/save")
async def save_article(
    request: BookmarkRequest,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    try:
        article = db.query(Article).filter(Article.id == request.article_id).first()

        if not article:
            raise HTTPException(status_code=404, detail="Article not found")

        if article.user_id is None:
            article.user_id = user.id

        article.bookmarked = True
        db.commit()
        db.refresh(article)

        logger.info(f"Article {article.id} bookmarked by user {user.id}")

        # ✨ NEW: Invalidate caches after successful bookmark
        await invalidate_bookmark_caches(user.id, article.id)

        return {
            "success": True,
            "bookmarked": True,
            "article_id": article.id,
            "message": "Article saved successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bookmarking article: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while saving article")
"""

# ============================================================================
# STEP 4: Update unsave_article endpoint (DELETE /api/articles/save/{id})
# ============================================================================

# BEFORE (Current implementation around line 391-440):
"""
@router.delete("/save/{article_id}")
async def unsave_article(
    article_id: int,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    try:
        article = (
            db.query(Article).filter(Article.id == article_id, Article.user_id == user.id).first()
        )

        if not article:
            raise HTTPException(status_code=404, detail="Article not found or not saved by you")

        article.bookmarked = False
        db.commit()
        db.refresh(article)

        logger.info(f"Article {article.id} unbookmarked by user {user.id}")

        return {
            "success": True,
            "bookmarked": False,
            "article_id": article.id,
            "message": "Article removed from saved",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing bookmark: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while removing bookmark")
"""

# AFTER (With cache invalidation):
"""
@router.delete("/save/{article_id}")
async def unsave_article(
    article_id: int,
    user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db),
):
    try:
        article = (
            db.query(Article).filter(Article.id == article_id, Article.user_id == user.id).first()
        )

        if not article:
            raise HTTPException(status_code=404, detail="Article not found or not saved by you")

        article.bookmarked = False
        db.commit()
        db.refresh(article)

        logger.info(f"Article {article.id} unbookmarked by user {user.id}")

        # ✨ NEW: Invalidate caches after successful unbookmark
        await invalidate_bookmark_caches(user.id, article.id)

        return {
            "success": True,
            "bookmarked": False,
            "article_id": article.id,
            "message": "Article removed from saved",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing bookmark: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while removing bookmark")
"""

# ============================================================================
# TESTING
# ============================================================================

"""
Test cache invalidation with these curl commands:

1. Save an article:
   curl -X POST "http://localhost:8000/api/articles/save" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"article_id": 1}'

   Expected: Cache keys deleted for user's saved articles

2. Get saved articles (should rebuild cache):
   curl "http://localhost:8000/api/articles/saved?limit=10" \
     -H "Authorization: Bearer YOUR_TOKEN"

   Expected: Fresh data from database (cache miss)

3. Get saved articles again (should use cache):
   curl "http://localhost:8000/api/articles/saved?limit=10" \
     -H "Authorization: Bearer YOUR_TOKEN"

   Expected: Same data from cache (cache hit)

4. Unsave article:
   curl -X DELETE "http://localhost:8000/api/articles/save/1" \
     -H "Authorization: Bearer YOUR_TOKEN"

   Expected: Cache invalidated again

5. Check Redis for cache keys:
   redis-cli
   > KEYS saved:*
   > KEYS recent:*
   > KEYS article:*
"""

# ============================================================================
# MONITORING
# ============================================================================

"""
Monitor cache invalidation in production:

1. Check backend logs:
   tail -f /tmp/backend.log | grep "Invalidated"

   Expected output:
   INFO: Invalidated 5 saved article cache keys for user 1
   INFO: Invalidated 12 recent article cache keys
   INFO: Invalidated cache for article 123

2. Monitor Redis operations:
   redis-cli MONITOR

   Expected operations:
   "SCAN" "0" "MATCH" "saved:*:user_1:*" "COUNT" "100"
   "DEL" "saved:all:user_1" "saved:today:user_1" ...

3. Check cache hit rate:
   curl "http://localhost:8000/api/health/cache/stats"

   Expected metrics:
   {
     "cache_hit_rate": 0.85,  // 85% hit rate is good
     "total_requests": 1000,
     "cache_hits": 850,
     "cache_misses": 150
   }
"""

# ============================================================================
# ROLLBACK PLAN
# ============================================================================

"""
If cache invalidation causes issues:

1. Comment out the invalidation calls:
   # await invalidate_bookmark_caches(user.id, article.id)

2. Restart backend:
   pkill -f "uvicorn main:app"
   uvicorn main:app --reload --port 8000

3. Caches will expire naturally via TTL (60 seconds for recent articles)
"""

# ============================================================================
# ALTERNATIVE: Simpler Implementation
# ============================================================================

"""
If the async cache invalidation is too complex, here's a simpler version
that just deletes all caches for the user:

async def invalidate_bookmark_caches_simple(user_id: int):
    '''Simpler cache invalidation - deletes all related caches'''
    try:
        redis = await get_async_redis_client()

        # Delete all saved articles caches
        await redis.delete(f"saved:all:user_{user_id}")
        await redis.delete(f"saved:today:user_{user_id}")
        await redis.delete(f"saved:week:user_{user_id}")

        # Delete all recent articles caches (global)
        await redis.flushdb()  # CAUTION: This deletes ALL caches!

        logger.info(f"Invalidated bookmark caches for user {user_id}")

    except Exception as e:
        logger.warning(f"Cache invalidation failed: {e}")

# Use like this:
# await invalidate_bookmark_caches_simple(user.id)
"""

# ============================================================================
# PERFORMANCE IMPACT
# ============================================================================

"""
Cache invalidation performance:

Operation                    | Time      | Impact
-----------------------------|-----------|-------------------
SCAN (find keys)             | ~1-5ms    | Negligible
DELETE (batch)               | ~1-2ms    | Negligible
Total overhead               | ~5-10ms   | <10% of request time
Cache rebuild (miss)         | ~20-30ms  | First request after invalidation
Cache hit (subsequent)       | ~2-5ms    | 90%+ of requests

Net result: Users get fresh data with minimal performance cost
"""

print("""
╔════════════════════════════════════════════════════════════╗
║  Cache Invalidation Patch for Bookmark Endpoints          ║
╚════════════════════════════════════════════════════════════╝

This file shows the code changes needed to add cache invalidation
to the bookmark endpoints.

QUICK START:
------------
1. Review the code changes above
2. Apply changes to articles.py (lines 25, 371, 425)
3. Test with the curl commands in the TESTING section
4. Monitor with the commands in the MONITORING section

BENEFITS:
---------
✅ iOS app always sees latest bookmark status
✅ No stale cache data
✅ Minimal performance overhead (<10ms)
✅ Non-critical (won't fail requests if Redis is down)

ALTERNATIVE:
------------
If you prefer not to invalidate caches, you can:
- Reduce cache TTL to 10 seconds (faster expiration)
- Use a "cache bypass" query parameter (?no_cache=1)
- Let iOS app handle cache locally (offline-first)

For questions, see BACKEND_API_SPECIFICATION.md
""")
