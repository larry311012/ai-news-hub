"""
Comprehensive Health Check API

Provides detailed health status for monitoring and alerting.
Checks all critical system components including database, services, and dependencies.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from typing import Dict, Any
import os
from pathlib import Path

from database import get_db
from loguru import logger

# Import cache utilities
import sys
sys.path.append(str(Path(__file__).parent.parent))
from utils.cache_manager import CacheStats
from utils.query_monitor import query_monitor

router = APIRouter()


class HealthCheckService:
    """Service for comprehensive health checks"""

    @staticmethod
    def check_database(db: Session) -> Dict[str, Any]:
        """
        Check database connectivity and basic operations

        Returns:
            dict: Database health status
        """
        try:
            # Test connection with simple query
            result = db.execute(text("SELECT 1")).scalar()

            if result != 1:
                return {
                    "status": "unhealthy",
                    "message": "Database query returned unexpected result",
                    "response_time_ms": 0
                }

            # Check critical tables exist
            tables = ['users', 'posts', 'articles', 'sessions', 'instagram_images']
            for table in tables:
                try:
                    db.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
                except Exception as e:
                    return {
                        "status": "degraded",
                        "message": f"Table {table} missing or inaccessible",
                        "error": str(e)
                    }

            return {
                "status": "healthy",
                "message": "Database operational",
                "tables_verified": len(tables)
            }

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "message": "Database connection failed",
                "error": str(e)
            }

    @staticmethod
    async def check_redis() -> Dict[str, Any]:
        """
        Check Redis cache connectivity and performance

        Returns:
            dict: Redis health status with stats
        """
        try:
            stats = await CacheStats.get_stats()

            if not stats.get("connected"):
                return {
                    "status": "unavailable",
                    "message": "Redis not connected",
                    "error": stats.get("error", "Unknown error")
                }

            # Check hit rate
            hit_rate = stats.get("hit_rate_percent", 0)
            status = "healthy"

            if hit_rate < 30:
                status = "degraded"
                message = f"Low cache hit rate: {hit_rate}%"
            elif hit_rate < 50:
                status = "warning"
                message = f"Moderate cache hit rate: {hit_rate}%"
            else:
                message = f"Good cache hit rate: {hit_rate}%"

            return {
                "status": status,
                "message": message,
                "hit_rate_percent": hit_rate,
                "memory_used": stats.get("used_memory_human"),
                "connected_clients": stats.get("connected_clients"),
                "uptime_seconds": stats.get("uptime_seconds"),
                "version": stats.get("redis_version")
            }

        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "error",
                "message": "Failed to check Redis",
                "error": str(e)
            }

    @staticmethod
    def check_openai_config() -> Dict[str, Any]:
        """
        Check OpenAI API configuration

        Returns:
            dict: OpenAI configuration status
        """
        api_key = os.getenv("OPENAI_API_KEY", "")

        if not api_key:
            return {
                "status": "not_configured",
                "message": "OpenAI API key not set in environment"
            }

        # Basic validation
        if len(api_key) < 20:
            return {
                "status": "invalid",
                "message": "OpenAI API key appears invalid (too short)"
            }

        if not api_key.startswith("sk-"):
            return {
                "status": "warning",
                "message": "OpenAI API key doesn't match expected format"
            }

        return {
            "status": "configured",
            "message": "OpenAI API key configured",
            "key_prefix": api_key[:7] + "..." if len(api_key) >= 7 else "***"
        }

    @staticmethod
    def check_storage() -> Dict[str, Any]:
        """
        Check image storage availability

        Returns:
            dict: Storage health status
        """
        # Get base directory (where this file is located, then go up to backend/)
        BASE_DIR = Path(__file__).resolve().parent.parent
        storage_path = os.getenv(
            "IMAGE_STORAGE_PATH",
            str(BASE_DIR / "static" / "instagram_images")
        )

        try:
            path = Path(storage_path)

            # Check if path exists
            if not path.exists():
                return {
                    "status": "unhealthy",
                    "message": f"Storage path does not exist: {storage_path}"
                }

            # Check if writable
            if not os.access(storage_path, os.W_OK):
                return {
                    "status": "unhealthy",
                    "message": "Storage path not writable"
                }

            # Get disk usage stats
            stat = os.statvfs(storage_path)
            free_space_gb = (stat.f_bavail * stat.f_frsize) / (1024 ** 3)
            total_space_gb = (stat.f_blocks * stat.f_frsize) / (1024 ** 3)
            usage_percent = ((total_space_gb - free_space_gb) / total_space_gb) * 100

            status = "healthy"
            if usage_percent > 95:
                status = "critical"
            elif usage_percent > 85:
                status = "warning"

            return {
                "status": status,
                "message": "Storage operational",
                "path": storage_path,
                "free_space_gb": round(free_space_gb, 2),
                "total_space_gb": round(total_space_gb, 2),
                "usage_percent": round(usage_percent, 2)
            }

        except Exception as e:
            logger.error(f"Storage health check failed: {e}")
            return {
                "status": "error",
                "message": "Failed to check storage",
                "error": str(e)
            }

    @staticmethod
    def check_encryption() -> Dict[str, Any]:
        """
        Check encryption configuration

        Returns:
            dict: Encryption status
        """
        encryption_key = os.getenv("ENCRYPTION_KEY", "")

        if not encryption_key:
            return {
                "status": "not_configured",
                "message": "Encryption key not set (using default - INSECURE)"
            }

        # Check key length (Fernet requires 32 bytes base64-encoded = 44 chars)
        if len(encryption_key) < 40:
            return {
                "status": "weak",
                "message": "Encryption key may be too weak"
            }

        return {
            "status": "configured",
            "message": "Encryption key configured properly"
        }

    @staticmethod
    def get_system_metrics() -> Dict[str, Any]:
        """
        Get basic system metrics

        Returns:
            dict: System metrics
        """
        import psutil

        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            }
        except Exception:
            # psutil not available, return minimal info
            return {
                "available": False
            }


@router.get("/health/detailed")
async def health_check_detailed(db: Session = Depends(get_db)):
    """
    Comprehensive health check with component status

    Checks:
    - Database connectivity
    - Redis cache connectivity and performance
    - Critical tables
    - API configuration
    - Storage availability
    - Encryption setup
    - System metrics (if available)

    Returns:
        200: All systems operational
        503: One or more critical systems unhealthy

    Response includes detailed status for each component.
    """
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.8.0",  # Updated for query optimization
        "environment": os.getenv("ENVIRONMENT", "development"),
        "components": {}
    }

    critical_failures = []
    warnings = []

    # Check Database
    db_status = HealthCheckService.check_database(db)
    health["components"]["database"] = db_status

    if db_status["status"] == "unhealthy":
        critical_failures.append("database")
        health["status"] = "unhealthy"
    elif db_status["status"] == "degraded":
        warnings.append("database")
        if health["status"] == "healthy":
            health["status"] = "degraded"

    # Check Redis Cache
    redis_status = await HealthCheckService.check_redis()
    health["components"]["redis_cache"] = redis_status

    if redis_status["status"] in ["error", "unavailable"]:
        warnings.append("redis_cache")
        # Redis is not critical - app can run without it
    elif redis_status["status"] == "degraded":
        warnings.append("redis_cache_performance")

    # Check OpenAI Configuration
    openai_status = HealthCheckService.check_openai_config()
    health["components"]["openai"] = openai_status

    if openai_status["status"] in ["invalid", "not_configured"]:
        warnings.append("openai")

    # Check Storage
    storage_status = HealthCheckService.check_storage()
    health["components"]["storage"] = storage_status

    if storage_status["status"] in ["unhealthy", "critical"]:
        critical_failures.append("storage")
        health["status"] = "unhealthy"
    elif storage_status["status"] == "warning":
        warnings.append("storage")

    # Check Encryption
    encryption_status = HealthCheckService.check_encryption()
    health["components"]["encryption"] = encryption_status

    if encryption_status["status"] == "not_configured":
        warnings.append("encryption")

    # Get System Metrics (optional)
    try:
        system_metrics = HealthCheckService.get_system_metrics()
        health["system_metrics"] = system_metrics
    except Exception as e:
        logger.debug(f"System metrics unavailable: {e}")

    # Summary
    health["summary"] = {
        "critical_failures": critical_failures,
        "warnings": warnings,
        "components_checked": len(health["components"])
    }

    # Set HTTP status code
    status_code = 200
    if health["status"] == "unhealthy":
        status_code = 503
    elif health["status"] == "degraded":
        status_code = 200  # Still return 200 for degraded (service usable)

    return JSONResponse(content=health, status_code=status_code)


@router.get("/health/cache/stats")
async def get_cache_stats():
    """
    Get Redis cache statistics and performance metrics

    Returns detailed cache statistics including:
    - Hit/miss rates
    - Memory usage
    - Connection info
    - Eviction stats

    Useful for monitoring cache effectiveness and tuning TTL values.
    """
    try:
        stats = await CacheStats.get_stats()

        return {
            "success": True,
            "stats": stats,
            "recommendations": _get_cache_recommendations(stats)
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/health/database/query-stats")
async def get_query_stats():
    """
    Get database query performance statistics.

    Returns performance metrics for all queries executed since last reset:
    - Average/median/min/max query times
    - Slow query counts (>100ms)
    - Query patterns and frequencies
    - Total time spent in queries

    Enable SQL_DEBUG=true in .env to populate these statistics.
    """
    try:
        stats = query_monitor.get_stats()

        # Calculate summary metrics
        total_queries = sum(s.count for s in stats)
        total_time = sum(s.total_time for s in stats)
        slow_queries = sum(s.slow_count for s in stats)

        summary = {
            "total_queries": total_queries,
            "total_time_ms": round(total_time * 1000, 2),
            "slow_queries": slow_queries,
            "slow_percentage": round((slow_queries / total_queries) * 100, 1) if total_queries > 0 else 0,
            "avg_query_time_ms": round((total_time / total_queries) * 1000, 2) if total_queries > 0 else 0
        }

        # Determine health status based on slow query percentage
        if summary["slow_percentage"] > 20:
            status = "critical"
            message = f"High percentage of slow queries ({summary['slow_percentage']}%)"
        elif summary["slow_percentage"] > 10:
            status = "warning"
            message = f"Moderate percentage of slow queries ({summary['slow_percentage']}%)"
        elif summary["slow_percentage"] > 5:
            status = "acceptable"
            message = f"Acceptable slow query rate ({summary['slow_percentage']}%)"
        else:
            status = "excellent"
            message = f"Low slow query rate ({summary['slow_percentage']}%)"

        return {
            "success": True,
            "status": status,
            "message": message,
            "summary": summary,
            "top_queries_by_time": [s.to_dict() for s in stats[:20]],  # Top 20 by total time
            "recommendations": _get_query_recommendations(summary, stats)
        }

    except Exception as e:
        logger.error(f"Failed to get query stats: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Make sure SQL_DEBUG=true is set in .env to enable query monitoring"
        }


@router.post("/health/database/query-stats/reset")
async def reset_query_stats():
    """
    Reset query statistics.

    Useful after making optimizations to measure improvements.
    """
    try:
        query_monitor.reset()
        return {
            "success": True,
            "message": "Query statistics reset successfully"
        }
    except Exception as e:
        logger.error(f"Failed to reset query stats: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/health/database/indexes")
async def get_index_usage(db: Session = Depends(get_db)):
    """
    Get database index usage statistics.

    Returns information about which indexes are being used and their effectiveness.
    Helps identify unused indexes that can be dropped.
    """
    try:
        # Query to get index usage stats
        query = text("""
            SELECT
                schemaname,
                tablename,
                indexname,
                idx_scan as scan_count,
                idx_tup_read as tuples_read,
                idx_tup_fetch as tuples_fetched,
                pg_size_pretty(pg_relation_size(indexrelid)) as index_size
            FROM pg_stat_user_indexes
            WHERE schemaname = 'public'
              AND tablename IN ('posts', 'articles', 'social_media_connections',
                               'social_media_posts', 'user_api_keys', 'sessions',
                               'instagram_images', 'users')
            ORDER BY idx_scan DESC
            LIMIT 30;
        """)

        result = db.execute(query).fetchall()

        indexes = [
            {
                "table": row[1],
                "index": row[2],
                "scan_count": row[3],
                "tuples_read": row[4],
                "tuples_fetched": row[5],
                "size": row[6]
            }
            for row in result
        ]

        # Find unused indexes
        unused_query = text("""
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
        """)

        unused_result = db.execute(unused_query).fetchall()

        unused_indexes = [
            {
                "table": row[1],
                "index": row[2],
                "size": row[3]
            }
            for row in unused_result
        ]

        return {
            "success": True,
            "top_used_indexes": indexes,
            "unused_indexes": unused_indexes,
            "recommendations": _get_index_recommendations(indexes, unused_indexes)
        }

    except Exception as e:
        logger.error(f"Failed to get index usage: {e}")
        return {
            "success": False,
            "error": str(e)
        }


def _get_cache_recommendations(stats: dict) -> list:
    """
    Generate recommendations based on cache statistics.

    Args:
        stats: Cache statistics dictionary

    Returns:
        List of recommendation strings
    """
    recommendations = []

    if not stats.get("connected"):
        recommendations.append("Redis is not connected. Install and start Redis for performance improvements.")
        return recommendations

    hit_rate = stats.get("hit_rate_percent", 0)

    if hit_rate < 30:
        recommendations.append(
            "Cache hit rate is low (<30%). Consider increasing TTL values or caching more endpoints."
        )
    elif hit_rate < 50:
        recommendations.append(
            "Cache hit rate is moderate (30-50%). Review which endpoints are cached."
        )
    elif hit_rate >= 80:
        recommendations.append(
            "Excellent cache hit rate (>80%)! Cache is performing well."
        )

    evicted = stats.get("evicted_keys", 0)
    if evicted > 1000:
        recommendations.append(
            f"High key eviction count ({evicted}). Consider increasing Redis max memory or reducing TTL."
        )

    return recommendations


def _get_query_recommendations(summary: dict, stats: list) -> list:
    """
    Generate recommendations based on query statistics.

    Args:
        summary: Query summary statistics
        stats: List of QueryStats objects

    Returns:
        List of recommendation strings
    """
    recommendations = []

    slow_pct = summary.get("slow_percentage", 0)

    if slow_pct > 20:
        recommendations.append(
            "CRITICAL: Over 20% of queries are slow (>100ms). Review query patterns and add indexes."
        )
    elif slow_pct > 10:
        recommendations.append(
            "WARNING: Over 10% of queries are slow. Consider query optimization."
        )

    # Check for N+1 patterns
    if stats:
        high_count_queries = [s for s in stats if s.count > 50]
        if high_count_queries:
            recommendations.append(
                f"Detected {len(high_count_queries)} queries executed >50 times. Check for N+1 problems."
            )

    # Check average query time
    avg_time = summary.get("avg_query_time_ms", 0)
    if avg_time > 100:
        recommendations.append(
            f"Average query time is {avg_time}ms (target: <50ms). Review slow queries."
        )

    if not recommendations:
        recommendations.append("Query performance looks good! Keep monitoring.")

    return recommendations


def _get_index_recommendations(used_indexes: list, unused_indexes: list) -> list:
    """
    Generate recommendations based on index usage.

    Args:
        used_indexes: List of used indexes with statistics
        unused_indexes: List of unused indexes

    Returns:
        List of recommendation strings
    """
    recommendations = []

    if unused_indexes:
        recommendations.append(
            f"Found {len(unused_indexes)} unused indexes. Consider dropping after monitoring for 1-2 weeks."
        )

    # Check for indexes with low usage
    if used_indexes:
        low_usage = [idx for idx in used_indexes if idx["scan_count"] < 10]
        if low_usage:
            recommendations.append(
                f"Found {len(low_usage)} indexes with <10 scans. Monitor for potential removal."
            )

    if not recommendations:
        recommendations.append("Index usage looks healthy.")

    return recommendations


@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Kubernetes-style readiness probe

    Returns 200 if service is ready to accept traffic.
    Returns 503 if service is starting up or not ready.

    Checks:
    - Database connectivity
    - Critical dependencies
    """
    try:
        # Quick database check
        db.execute(text("SELECT 1"))

        # Check critical environment variables
        required_vars = ["DATABASE_URL"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            return JSONResponse(
                content={
                    "ready": False,
                    "reason": f"Missing environment variables: {missing_vars}"
                },
                status_code=503
            )

        return {
            "ready": True,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        return JSONResponse(
            content={
                "ready": False,
                "reason": str(e)
            },
            status_code=503
        )


@router.get("/health/live")
async def liveness_check():
    """
    Kubernetes-style liveness probe

    Returns 200 if service process is alive.
    This should always succeed unless the process is completely hung.
    """
    return {
        "alive": True,
        "timestamp": datetime.utcnow().isoformat()
    }
