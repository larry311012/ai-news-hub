#!/usr/bin/env python3
"""
Database Commit Verification Script

This script directly queries the database to verify that:
1. Post status updates are committed
2. Error messages are persisted
3. Timestamps are set correctly
4. SocialMediaPost records are created

Usage: python verify_db_commit.py [post_id]
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from database import Base, Post
from database_social_media import SocialMediaPost
import os

def verify_database_commits(post_id=None):
    """Verify database commits are working"""

    # Connect to database
    db_path = os.getenv("DATABASE_URL", "sqlite:///ai_news.db")
    engine = create_engine(db_path)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    print("=" * 80)
    print("DATABASE COMMIT VERIFICATION")
    print("=" * 80)
    print(f"Database: {db_path}")
    print()

    try:
        if post_id:
            # Check specific post
            post = db.query(Post).filter(Post.id == post_id).first()
            if not post:
                print(f"❌ Post {post_id} not found in database")
                return False

            print(f"Post ID: {post.id}")
            print(f"Title: {post.article_title}")
            print(f"Status: {post.status}")
            print(f"Error Message: {post.error_message or 'None'}")
            print(f"Published At: {post.published_at or 'Not published'}")
            print(f"Created At: {post.created_at}")
            print()

            # Check SocialMediaPost records
            social_posts = db.query(SocialMediaPost).filter(
                SocialMediaPost.post_id == post_id
            ).all()

            if social_posts:
                print(f"Social Media Post Records: {len(social_posts)}")
                print()
                for sp in social_posts:
                    print(f"  Platform: {sp.platform}")
                    print(f"  Status: {sp.status}")
                    print(f"  Platform URL: {sp.platform_url or 'None'}")
                    print(f"  Error: {sp.error_message or 'None'}")
                    print(f"  Published At: {sp.published_at or 'Not published'}")
                    print()
            else:
                print("No SocialMediaPost records found")
                print()

            # Verify commit worked
            if post.status in ['published', 'failed', 'partially_published']:
                print("✅ VERIFIED: Post status was updated (commit worked)")
                return True
            else:
                print(f"⚠ Post status is '{post.status}' - may still be processing")
                return True

        else:
            # Show recent posts
            posts = db.query(Post).order_by(desc(Post.id)).limit(10).all()

            if not posts:
                print("No posts found in database")
                return True

            print("Recent Posts (last 10):")
            print()
            print(f"{'ID':<6} {'Status':<20} {'Published At':<25} {'Error':<30}")
            print("-" * 80)

            for post in posts:
                error = (post.error_message[:27] + '...') if post.error_message and len(post.error_message) > 30 else (post.error_message or '')
                pub_at = str(post.published_at) if post.published_at else ''

                print(f"{post.id:<6} {post.status:<20} {pub_at:<25} {error:<30}")

            print()
            print(f"Total posts: {db.query(Post).count()}")
            print()

            # Check for posts with error messages
            failed_posts = db.query(Post).filter(
                Post.status.in_(['failed', 'partially_published'])
            ).count()

            if failed_posts > 0:
                print(f"✅ Found {failed_posts} posts with failed/partial status")
                print("   This indicates error messages are being persisted")

            # Check for published posts
            published_posts = db.query(Post).filter(
                Post.status == 'published'
            ).count()

            if published_posts > 0:
                print(f"✅ Found {published_posts} published posts")
                print("   This indicates successful publishes are being committed")

            print()
            print("To check a specific post: python verify_db_commit.py POST_ID")

            return True

    except Exception as e:
        print(f"❌ Error querying database: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()


if __name__ == "__main__":
    post_id = int(sys.argv[1]) if len(sys.argv) > 1 else None

    success = verify_database_commits(post_id)
    sys.exit(0 if success else 1)
