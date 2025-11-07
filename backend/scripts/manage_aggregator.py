#!/usr/bin/env python3
"""
Feed Aggregator Management CLI (Task 2.7)

Command-line interface for managing the feed aggregator service.

Usage:
    python scripts/manage_aggregator.py status
    python scripts/manage_aggregator.py fetch-all
    python scripts/manage_aggregator.py fetch-feed <feed_id>
    python scripts/manage_aggregator.py health
    python scripts/manage_aggregator.py run-once
    python scripts/manage_aggregator.py run-continuous

Examples:
    # Check aggregator status
    python scripts/manage_aggregator.py status

    # Fetch all feeds once
    python scripts/manage_aggregator.py fetch-all

    # Fetch specific feed
    python scripts/manage_aggregator.py fetch-feed 1

    # View health dashboard
    python scripts/manage_aggregator.py health

    # Run aggregator once (for cron)
    python scripts/manage_aggregator.py run-once

    # Run aggregator continuously
    python scripts/manage_aggregator.py run-continuous
"""
import sys
import os
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from services.feed_aggregator import (
    FeedAggregator,
    fetch_all_feeds_once,
    fetch_single_feed,
)
from database import get_db
from sqlalchemy import text


# ============================================================================
# CLI COMMANDS
# ============================================================================


async def cmd_status():
    """Get aggregator status"""
    logger.info("Fetching aggregator status...")

    # Get feed statistics from database
    db = next(get_db())

    try:
        # Total feeds
        result = db.execute(text("SELECT COUNT(*) as count FROM user_feeds")).fetchone()
        total_feeds = result.count

        # Active feeds
        result = db.execute(
            text("SELECT COUNT(*) as count FROM user_feeds WHERE is_active = TRUE")
        ).fetchone()
        active_feeds = result.count

        # Health breakdown
        result = db.execute(
            text("""
                SELECT health_status, COUNT(*) as count
                FROM user_feeds
                GROUP BY health_status
            """)
        ).fetchall()

        health_breakdown = {row.health_status: row.count for row in result}

        # Last fetched
        result = db.execute(
            text("""
                SELECT MAX(last_fetched_at) as last_fetched
                FROM user_feeds
            """)
        ).fetchone()

        last_fetched = result.last_fetched if result else None

        # Print status
        print("\n" + "=" * 80)
        print("FEED AGGREGATOR STATUS")
        print("=" * 80)
        print(f"\nTotal Feeds: {total_feeds}")
        print(f"Active Feeds: {active_feeds}")
        print(f"Inactive Feeds: {total_feeds - active_feeds}")
        print("\nHealth Breakdown:")
        for status, count in health_breakdown.items():
            print(f"  {status}: {count}")
        print(f"\nLast Fetch: {last_fetched or 'Never'}")
        print("\n" + "=" * 80)

    finally:
        db.close()


async def cmd_fetch_all():
    """Fetch all feeds once"""
    logger.info("Starting manual feed fetch for all feeds...")

    start_time = datetime.now()

    stats = await fetch_all_feeds_once()

    elapsed = (datetime.now() - start_time).total_seconds()

    print("\n" + "=" * 80)
    print("FEED FETCH COMPLETE")
    print("=" * 80)
    print(f"\nTotal Fetches: {stats['total_fetches']}")
    print(f"Successful: {stats['successful_fetches']}")
    print(f"Failed: {stats['failed_fetches']}")
    print(f"New Articles: {stats['articles_added']}")
    print(f"Duplicates Skipped: {stats['duplicates_skipped']}")
    print(f"\nElapsed Time: {elapsed:.1f}s")
    print("=" * 80 + "\n")


async def cmd_fetch_feed(feed_id: int):
    """Fetch specific feed"""
    logger.info(f"Fetching feed {feed_id}...")

    start_time = datetime.now()

    result = await fetch_single_feed(feed_id)

    elapsed = (datetime.now() - start_time).total_seconds()

    print("\n" + "=" * 80)
    print(f"FEED {feed_id} FETCH COMPLETE")
    print("=" * 80)

    if result.get("success"):
        print(f"\nStatus: SUCCESS")
        print(f"New Articles: {result.get('articles_added', 0)}")
        print(f"Duplicates: {result.get('duplicates_skipped', 0)}")
    else:
        print(f"\nStatus: FAILED")
        print(f"Error: {result.get('error', 'Unknown error')}")

    print(f"\nElapsed Time: {elapsed:.2f}s")
    print("=" * 80 + "\n")


async def cmd_health():
    """View health dashboard"""
    logger.info("Fetching health dashboard...")

    db = next(get_db())

    try:
        # Get all feeds with health issues
        result = db.execute(
            text("""
                SELECT
                    id,
                    feed_name,
                    feed_url,
                    health_status,
                    error_message,
                    COALESCE(consecutive_failures, 0) as consecutive_failures,
                    last_successful_fetch,
                    is_active
                FROM user_feeds
                WHERE health_status IN ('error', 'warning')
                OR consecutive_failures > 0
                ORDER BY consecutive_failures DESC, health_status
            """)
        ).fetchall()

        print("\n" + "=" * 80)
        print("FEED HEALTH DASHBOARD")
        print("=" * 80)

        if not result:
            print("\nAll feeds are healthy!")
        else:
            print(f"\nFeeds Needing Attention: {len(result)}\n")

            for feed in result:
                status_emoji = {
                    "error": "❌",
                    "warning": "⚠️",
                    "healthy": "✓"
                }.get(feed.health_status, "?")

                active_status = "ACTIVE" if feed.is_active else "INACTIVE"

                print(f"{status_emoji} Feed #{feed.id}: {feed.feed_name} [{active_status}]")
                print(f"   URL: {feed.feed_url}")
                print(f"   Status: {feed.health_status}")

                if feed.consecutive_failures > 0:
                    print(f"   Consecutive Failures: {feed.consecutive_failures}")

                if feed.error_message:
                    print(f"   Error: {feed.error_message[:100]}")

                if feed.last_successful_fetch:
                    print(f"   Last Success: {feed.last_successful_fetch}")

                print()

        print("=" * 80 + "\n")

    finally:
        db.close()


async def cmd_run_once():
    """Run aggregator once (for cron jobs)"""
    logger.info("Running aggregator once...")

    start_time = datetime.now()

    stats = await fetch_all_feeds_once()

    elapsed = (datetime.now() - start_time).total_seconds()

    logger.info(
        f"Aggregator run complete: "
        f"{stats['successful_fetches']}/{stats['total_fetches']} successful, "
        f"{stats['articles_added']} new articles, "
        f"{elapsed:.1f}s"
    )


async def cmd_run_continuous():
    """Run aggregator continuously (background service)"""
    logger.info("Starting continuous aggregator service...")

    print("\n" + "=" * 80)
    print("FEED AGGREGATOR SERVICE")
    print("=" * 80)
    print("\nStarting continuous aggregation...")
    print("Press Ctrl+C to stop\n")
    print("=" * 80 + "\n")

    aggregator = FeedAggregator()

    try:
        await aggregator.start()
    except KeyboardInterrupt:
        logger.info("Stopping aggregator...")
        aggregator.stop()
        print("\nAggregator stopped.")


# ============================================================================
# MAIN CLI
# ============================================================================


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Feed Aggregator Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Status command
    subparsers.add_parser("status", help="Show aggregator status")

    # Fetch all command
    subparsers.add_parser("fetch-all", help="Fetch all feeds once")

    # Fetch feed command
    fetch_feed_parser = subparsers.add_parser("fetch-feed", help="Fetch specific feed")
    fetch_feed_parser.add_argument("feed_id", type=int, help="Feed ID to fetch")

    # Health command
    subparsers.add_parser("health", help="Show health dashboard")

    # Run once command
    subparsers.add_parser("run-once", help="Run aggregator once (for cron)")

    # Run continuous command
    subparsers.add_parser("run-continuous", help="Run aggregator continuously")

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Run command
    try:
        if args.command == "status":
            asyncio.run(cmd_status())
        elif args.command == "fetch-all":
            asyncio.run(cmd_fetch_all())
        elif args.command == "fetch-feed":
            asyncio.run(cmd_fetch_feed(args.feed_id))
        elif args.command == "health":
            asyncio.run(cmd_health())
        elif args.command == "run-once":
            asyncio.run(cmd_run_once())
        elif args.command == "run-continuous":
            asyncio.run(cmd_run_continuous())
        else:
            parser.print_help()
            sys.exit(1)

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
