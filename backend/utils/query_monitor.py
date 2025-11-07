"""
Query Performance Monitoring and Analysis
"""
import time
from contextlib import contextmanager
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import statistics
import logging
import re
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class QueryStats:
    """Statistics for a single query pattern."""
    query_hash: str
    query_template: str
    count: int
    total_time: float
    min_time: float
    max_time: float
    avg_time: float
    median_time: float
    slow_count: int  # queries > 100ms

    def to_dict(self) -> dict:
        return {
            "query_hash": self.query_hash,
            "query_template": self.query_template[:200],
            "count": self.count,
            "total_time_ms": round(self.total_time * 1000, 2),
            "avg_time_ms": round(self.avg_time * 1000, 2),
            "median_time_ms": round(self.median_time * 1000, 2),
            "min_time_ms": round(self.min_time * 1000, 2),
            "max_time_ms": round(self.max_time * 1000, 2),
            "slow_count": self.slow_count,
            "slow_percentage": round((self.slow_count / self.count) * 100, 1) if self.count > 0 else 0
        }


class QueryMonitor:
    """Monitor and collect query performance statistics."""

    def __init__(self):
        self.queries: Dict[str, dict] = {}
        self.enabled = True

    def record_query(self, query: str, duration: float):
        """Record a query execution."""
        if not self.enabled:
            return

        # Create hash of query (normalize parameters)
        query_hash = self._normalize_query(query)

        if query_hash not in self.queries:
            self.queries[query_hash] = {
                "template": query[:200],
                "times": []
            }

        self.queries[query_hash]["times"].append(duration)

    def _normalize_query(self, query: str) -> str:
        """Normalize query by removing parameter values."""
        # Remove numbers, strings in quotes, UUIDs
        normalized = re.sub(r'\d+', 'N', query)
        normalized = re.sub(r"'[^']*'", "'S'", normalized)
        normalized = re.sub(r'"[^"]*"', '"S"', normalized)

        # Create hash
        return hashlib.md5(normalized.encode()).hexdigest()[:16]

    def get_stats(self) -> List[QueryStats]:
        """Get statistics for all queries."""
        stats = []

        for query_hash, data in self.queries.items():
            times = data["times"]
            if not times:
                continue

            stats.append(QueryStats(
                query_hash=query_hash,
                query_template=data["template"],
                count=len(times),
                total_time=sum(times),
                min_time=min(times),
                max_time=max(times),
                avg_time=statistics.mean(times),
                median_time=statistics.median(times),
                slow_count=sum(1 for t in times if t > 0.1)
            ))

        # Sort by total time (most impactful queries first)
        stats.sort(key=lambda s: s.total_time, reverse=True)
        return stats

    def reset(self):
        """Reset all statistics."""
        self.queries.clear()


# Global query monitor instance
query_monitor = QueryMonitor()


@contextmanager
def monitor_query(query: str):
    """Context manager for monitoring query execution."""
    start = time.time()
    try:
        yield
    finally:
        duration = time.time() - start
        query_monitor.record_query(query, duration)

        if duration > 0.1:  # Log slow queries
            logger.warning(f"Slow query ({duration:.3f}s): {query[:200]}")
