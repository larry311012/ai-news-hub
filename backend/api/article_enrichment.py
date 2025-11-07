"""
Article Enrichment API Endpoints (Tasks 2.8 + 2.13)

Provides API endpoints for managing and testing article enrichment features.

Endpoints:
- POST /api/articles/{article_id}/enrich - Enrich a single article
- POST /api/articles/enrich-batch - Enrich multiple articles
- GET /api/articles/enrichment/stats - Get enrichment statistics
- POST /api/articles/enrichment/migrate - Migrate existing articles
- POST /api/articles/enrichment/test - Test enrichment on a URL

Authentication: Required (JWT token)
Rate Limiting: Applied
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from loguru import logger

from database import get_db
from utils.auth import get_current_user
from services.article_enrichment_service import (
    ArticleEnrichmentService,
    enrich_article_by_url,
    enrich_existing_articles
)
from services.feed_aggregator_enriched import (
    add_enrichment_columns_to_articles,
    migrate_existing_articles
)

router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class EnrichArticleRequest(BaseModel):
    """Request to enrich a single article by URL"""
    url: HttpUrl
    fetch_content: bool = True


class EnrichBatchRequest(BaseModel):
    """Request to enrich multiple articles"""
    article_ids: List[int]
    force_refresh: bool = False


class MigrateArticlesRequest(BaseModel):
    """Request to migrate existing articles"""
    limit: int = 50
    user_id: Optional[int] = None


class EnrichmentStatsResponse(BaseModel):
    """Enrichment statistics"""
    articles_enriched: int
    images_extracted: int
    categories_assigned: int
    summaries_generated: int
    quality_failures: int
    cache_size: int


class ArticleEnrichmentResponse(BaseModel):
    """Response with enriched article data"""
    success: bool
    article_id: Optional[int] = None
    url: str
    title: Optional[str] = None
    category: Optional[str] = None
    featured_image: Optional[str] = None
    auto_summary: Optional[str] = None
    quality_score: Optional[int] = None
    author: Optional[str] = None
    reading_time: Optional[int] = None
    topics: Optional[List[str]] = None
    error: Optional[str] = None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/articles/{article_id}/enrich", response_model=ArticleEnrichmentResponse)
async def enrich_article(
    article_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enrich a single article by ID

    Fetches the article from the database and enriches it with:
    - Full-text extraction
    - Featured image
    - Category classification
    - Summary generation
    - Metadata extraction

    The enriched data is saved back to the database.

    **Authentication Required**: Yes
    **Rate Limit**: 30 requests per minute
    """
    try:
        user_id = current_user["id"]

        # Get article
        result = db.execute(
            text("""
                SELECT id, title, link, content, category
                FROM articles
                WHERE id = :article_id AND user_id = :user_id
            """),
            {"article_id": article_id, "user_id": user_id}
        ).fetchone()

        if not result:
            raise HTTPException(status_code=404, detail="Article not found")

        article = result

        # Enrich article
        service = ArticleEnrichmentService()
        enriched = await service.enrich_article(
            url=article.link,
            existing_content=article.content,
            existing_data={
                "title": article.title,
                "category": article.category,
            }
        )

        # Update database (basic fields - extend as needed)
        db.execute(
            text("""
                UPDATE articles
                SET
                    content = COALESCE(:content, content),
                    category = COALESCE(:category, category),
                    summary = COALESCE(:summary, summary)
                WHERE id = :article_id
            """),
            {
                "article_id": article_id,
                "content": enriched.get("content_for_ai"),
                "category": enriched.get("category"),
                "summary": enriched.get("auto_summary"),
            }
        )
        db.commit()

        logger.info(f"Article {article_id} enriched successfully")

        return ArticleEnrichmentResponse(
            success=True,
            article_id=article_id,
            url=article.link,
            title=enriched.get("title"),
            category=enriched.get("category"),
            featured_image=enriched.get("featured_image"),
            auto_summary=enriched.get("auto_summary"),
            quality_score=enriched.get("quality_score"),
            author=enriched.get("author"),
            reading_time=enriched.get("reading_time"),
            topics=enriched.get("topics"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enriching article {article_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {str(e)}")


@router.post("/articles/enrich/test", response_model=ArticleEnrichmentResponse)
async def test_enrichment(
    request: EnrichArticleRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Test article enrichment on a URL

    This endpoint allows you to test the enrichment service on any article URL
    without saving to the database. Useful for testing and debugging.

    **Authentication Required**: Yes
    **Rate Limit**: 10 requests per minute
    """
    try:
        # Enrich article
        enriched = await enrich_article_by_url(str(request.url))

        return ArticleEnrichmentResponse(
            success=True,
            url=str(request.url),
            title=enriched.get("title"),
            category=enriched.get("category"),
            featured_image=enriched.get("featured_image"),
            auto_summary=enriched.get("auto_summary"),
            quality_score=enriched.get("quality_score"),
            author=enriched.get("author"),
            reading_time=enriched.get("reading_time"),
            topics=enriched.get("topics"),
        )

    except Exception as e:
        logger.error(f"Error testing enrichment for {request.url}: {e}")
        return ArticleEnrichmentResponse(
            success=False,
            url=str(request.url),
            error=str(e)
        )


@router.post("/articles/enrich-batch")
async def enrich_batch(
    request: EnrichBatchRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Enrich multiple articles in batch

    Processes multiple articles in the background.
    Returns immediately with a task ID.

    **Authentication Required**: Yes
    **Rate Limit**: 5 requests per minute
    """
    try:
        user_id = current_user["id"]

        # Verify articles exist and belong to user
        placeholders = ','.join([f':id{i}' for i in range(len(request.article_ids))])
        params = {f'id{i}': aid for i, aid in enumerate(request.article_ids)}
        params['user_id'] = user_id

        result = db.execute(
            text(f"""
                SELECT COUNT(*) as count
                FROM articles
                WHERE id IN ({placeholders}) AND user_id = :user_id
            """),
            params
        ).fetchone()

        if result.count != len(request.article_ids):
            raise HTTPException(
                status_code=400,
                detail="Some articles not found or don't belong to user"
            )

        # Add background task
        async def enrich_articles_background():
            service = ArticleEnrichmentService()
            enriched_count = 0

            for article_id in request.article_ids:
                try:
                    # Get article
                    article_result = db.execute(
                        text("""
                            SELECT id, link, content
                            FROM articles
                            WHERE id = :article_id
                        """),
                        {"article_id": article_id}
                    ).fetchone()

                    if article_result:
                        # Enrich
                        enriched = await service.enrich_article(
                            url=article_result.link,
                            existing_content=article_result.content
                        )

                        # Update database
                        db.execute(
                            text("""
                                UPDATE articles
                                SET
                                    content = COALESCE(:content, content),
                                    category = COALESCE(:category, category),
                                    summary = COALESCE(:summary, summary)
                                WHERE id = :article_id
                            """),
                            {
                                "article_id": article_id,
                                "content": enriched.get("content_for_ai"),
                                "category": enriched.get("category"),
                                "summary": enriched.get("auto_summary"),
                            }
                        )
                        enriched_count += 1

                except Exception as e:
                    logger.error(f"Error enriching article {article_id}: {e}")
                    continue

            db.commit()
            logger.info(f"Batch enrichment complete: {enriched_count}/{len(request.article_ids)} articles")

        background_tasks.add_task(enrich_articles_background)

        return {
            "success": True,
            "message": f"Enriching {len(request.article_ids)} articles in background",
            "article_count": len(request.article_ids)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting batch enrichment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/articles/enrichment/stats", response_model=EnrichmentStatsResponse)
async def get_enrichment_stats(
    current_user: dict = Depends(get_current_user)
):
    """
    Get enrichment service statistics

    Returns statistics about the enrichment service performance.

    **Authentication Required**: Yes
    **Rate Limit**: 60 requests per minute
    """
    try:
        service = ArticleEnrichmentService()
        stats = service.get_stats()

        return EnrichmentStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting enrichment stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/articles/enrichment/migrate")
async def migrate_articles(
    request: MigrateArticlesRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Migrate existing articles to add enrichment data

    Processes existing articles in the background to add:
    - Full-text extraction
    - Featured images
    - Categories
    - Summaries
    - Metadata

    This is useful for enriching articles that were added before
    the enrichment service was implemented.

    **Authentication Required**: Yes
    **Rate Limit**: 3 requests per minute
    **Admin Only**: Yes (optional - can be restricted)
    """
    try:
        user_id = request.user_id or current_user["id"]

        # Add background task
        async def migrate_background():
            try:
                stats = await migrate_existing_articles(user_id, request.limit)
                logger.info(f"Migration complete for user {user_id}: {stats}")
            except Exception as e:
                logger.error(f"Migration error: {e}")

        background_tasks.add_task(migrate_background)

        return {
            "success": True,
            "message": f"Started migration for up to {request.limit} articles",
            "user_id": user_id
        }

    except Exception as e:
        logger.error(f"Error starting migration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/articles/enrichment/init-db")
async def initialize_enrichment_database(
    current_user: dict = Depends(get_current_user)
):
    """
    Initialize database for article enrichment

    Adds required columns to the articles table for storing enrichment data.
    This is a one-time setup operation.

    **Authentication Required**: Yes
    **Admin Only**: Yes (recommended)
    """
    try:
        # Check if user is admin (optional - implement your admin check)
        # For now, allow any authenticated user

        add_enrichment_columns_to_articles()

        return {
            "success": True,
            "message": "Enrichment columns added to articles table"
        }

    except Exception as e:
        logger.error(f"Error initializing enrichment database: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/articles/enrichment/health")
async def enrichment_health_check():
    """
    Health check for enrichment service

    Public endpoint to verify enrichment service is operational.

    **Authentication Required**: No
    """
    try:
        service = ArticleEnrichmentService()
        stats = service.get_stats()

        return {
            "status": "healthy",
            "service": "article_enrichment",
            "features": {
                "full_text_extraction": True,
                "image_extraction": True,
                "category_classification": True,
                "quality_scoring": True,
                "summarization": True,
                "metadata_extraction": True,
            },
            "stats": stats
        }

    except Exception as e:
        logger.error(f"Enrichment health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }
