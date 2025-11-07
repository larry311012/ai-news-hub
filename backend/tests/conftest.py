"""
Shared test fixtures and configuration for all tests.

This file is automatically loaded by pytest and provides common fixtures.
"""
import pytest
import sys
import os
import uuid
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path (web/backend) - MUST be first priority
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# Add project root to Python path for imports from src package
# This allows tests to import from src.generators, src.publishers, etc.
project_root = Path(__file__).resolve().parent.parent.parent.parent  # Project root

if str(project_root) not in sys.path:
    sys.path.append(str(project_root))  # Use append to not override backend utils

# Set OAuth environment variables for testing BEFORE modules load
os.environ.setdefault("LINKEDIN_CLIENT_ID", "test_linkedin_client_id")
os.environ.setdefault("LINKEDIN_CLIENT_SECRET", "test_linkedin_client_secret")
os.environ.setdefault(
    "LINKEDIN_REDIRECT_URI", "http://localhost:8000/api/social-media/linkedin/callback"
)
os.environ.setdefault("TWITTER_CLIENT_ID", "test_twitter_client_id")
os.environ.setdefault("TWITTER_CLIENT_SECRET", "test_twitter_client_secret")
os.environ.setdefault(
    "TWITTER_REDIRECT_URI", "http://localhost:8000/api/social-media/twitter/callback"
)
os.environ.setdefault("THREADS_CLIENT_ID", "test_threads_client_id")
os.environ.setdefault("THREADS_CLIENT_SECRET", "test_threads_client_secret")
os.environ.setdefault(
    "THREADS_REDIRECT_URI", "http://localhost:8000/api/social-media/threads/callback"
)

# Set Twitter OAuth 1.0a environment variables for testing
os.environ.setdefault("TWITTER_API_KEY", "test_twitter_api_key")
os.environ.setdefault("TWITTER_API_SECRET", "test_twitter_api_secret")
os.environ.setdefault(
    "TWITTER_CALLBACK_URL", "http://localhost:8000/api/social-media/twitter-oauth1/callback"
)

# Disable CSRF protection in tests (would require CSRF tokens in every request)
os.environ["CSRF_ENABLED"] = "false"

# Set test mode environment variables
os.environ["TESTING"] = "true"
os.environ["ENABLE_RATE_LIMITING"] = "false"

# Import database BEFORE main app to allow patching
import database
from database import Base

# Import all database models to ensure tables are created
import database_social_media
import database_twitter_oauth
import database_oauth_credentials

# Disable rate limiting for tests
import utils.rate_limiter


def mock_check_rate_limit(*args, **kwargs):
    """Mock rate limiter that always allows requests"""
    return (True, None)  # (allowed, retry_after)


utils.rate_limiter.RateLimiter.check_rate_limit = staticmethod(mock_check_rate_limit)


# Test engine fixture - creates tables once per session for speed
@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine with all tables (session-scoped for performance)"""
    # Use PostgreSQL test database
    test_db_url = os.getenv("TEST_DATABASE_URL", "postgresql://ranhui@localhost/ai_news_test")

    # Create engine with PostgreSQL-specific settings
    engine = create_engine(
        test_db_url,
        pool_pre_ping=True,  # Verify connections before using
        pool_size=10,
        max_overflow=20,
    )

    # Create all tables ONCE for the entire test session
    # Skip drop - let create_all handle it with checkfirst
    Base.metadata.create_all(engine, checkfirst=True)

    yield engine

    # Clean up: Disabled for speed during debugging
    # Base.metadata.drop_all(engine)  # This is VERY slow with many tables
    engine.dispose()


# Per-function cleanup fixture - DISABLED for faster test runs during debugging
# We'll rely on test isolation through transactions instead
# @pytest.fixture(scope="function", autouse=True)
# def cleanup_data(test_engine):
#     """Clean all data between tests (keeps schema)"""
#     yield  # Run test first
#     # Cleanup disabled - tests should use transactions for isolation


# Database session fixture
@pytest.fixture
def db_session(test_engine):
    """Create database session for test setup"""
    TestSessionLocal = sessionmaker(bind=test_engine)
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


# Database session alias for convenience
@pytest.fixture
def db(db_session):
    """Alias for db_session for convenience"""
    return db_session


# Test client fixture
@pytest.fixture
def client(test_engine):
    """Create test client with database override"""
    from fastapi.testclient import TestClient
    from main import app
    from database import get_db

    TestSessionLocal = sessionmaker(bind=test_engine)

    # Patch SessionLocal used by middleware
    original_session_local = database.SessionLocal
    database.SessionLocal = TestSessionLocal

    def override_get_db():
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    database.SessionLocal = original_session_local


# Custom dict-like class that also supports attribute access
class TestUserDict(dict):
    """Dict that supports both dict['key'] and dict.key access patterns"""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name, value):
        self[name] = value


# Test user fixture
@pytest.fixture
def test_user(db_session):
    """Create a test user in the database and return hybrid dict/object"""
    from database import User
    from utils.auth import hash_password

    # Clean up existing user
    existing = db_session.query(User).filter(User.email == "test@example.com").first()
    if existing:
        db_session.delete(existing)
        db_session.commit()

    password = "testpassword123"
    user = User(
        email="test@example.com",
        password_hash=hash_password(password),
        full_name="Test User",
        is_active=True,
        is_verified=True,
        is_admin=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Return hybrid dict that supports both test_user["email"] and test_user.id
    result = TestUserDict({
        "id": user.id,
        "email": user.email,
        "password": password,  # Plain password for login tests
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_verified": user.is_verified,
        "is_admin": user.is_admin,
        "user_object": user  # For tests that need the ORM object
    })
    return result


# Authenticated client fixture
@pytest.fixture
def auth_client(test_engine):
    """Create test client with authentication and database overrides"""
    from fastapi.testclient import TestClient
    from main import app
    from database import get_db, User
    from utils.auth import get_current_user_dependency, hash_password

    TestSessionLocal = sessionmaker(bind=test_engine)

    # Patch SessionLocal used by middleware
    original_session_local = database.SessionLocal
    database.SessionLocal = TestSessionLocal

    def override_get_db():
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()

    # Create REAL user in database (not a mock) for authentication
    # This ensures foreign key constraints are satisfied
    session = TestSessionLocal()
    try:
        # Clean up existing user
        existing = session.query(User).filter(User.email == "test@example.com").first()
        if existing:
            session.delete(existing)
            session.commit()

        # Create real user with id=1
        user = User(
            id=1,
            email="test@example.com",
            password_hash=hash_password("testpassword123"),
            full_name="Test User",
            is_active=True,
            is_verified=True,
            is_admin=False,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        created_user_id = user.id
    finally:
        session.close()

    # Return the real user from database
    def override_get_current_user():
        session = TestSessionLocal()
        user = session.query(User).filter(User.id == created_user_id).first()
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_dependency] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    database.SessionLocal = original_session_local


# ============================================================================
# Instagram-specific fixtures
# ============================================================================


@pytest.fixture
def image_generation_service(db_session):
    """Create ImageGenerationService instance for testing"""
    from services.image_generation_service import ImageGenerationService

    service = ImageGenerationService(db_session)
    service.dalle_api_key = "test_api_key"
    return service


@pytest.fixture
def sample_image_bytes():
    """Generate sample PNG bytes for testing"""
    from PIL import Image
    from io import BytesIO

    img = Image.new("RGB", (1024, 1024), color="red")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()


@pytest.fixture
def sample_jpg_bytes():
    """Generate sample JPG bytes for testing"""
    from PIL import Image
    from io import BytesIO

    img = Image.new("RGB", (1024, 1024), color="blue")
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    buffer.seek(0)
    return buffer.getvalue()


@pytest.fixture
def mock_openai_client(monkeypatch):
    """Mock OpenAI API responses for image generation"""
    import base64
    from unittest.mock import Mock, AsyncMock

    mock_response = Mock()
    mock_response.status_code = 200

    # Create mock image bytes
    from PIL import Image
    from io import BytesIO

    img = Image.new("RGB", (1024, 1024), color="green")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    mock_response.json.return_value = {
        "created": 1234567890,
        "data": [{"b64_json": image_b64, "revised_prompt": "Enhanced test prompt"}],
    }

    return mock_response


@pytest.fixture
def temp_image_storage(tmpdir):
    """Create temporary image storage directory"""
    from pathlib import Path

    storage_path = Path(str(tmpdir)) / "instagram_images"
    storage_path.mkdir(parents=True, exist_ok=True)
    return storage_path


@pytest.fixture
def test_article(db_session):
    """Create test article with correct field names (idempotent)"""
    from database import Article
    from datetime import datetime

    # Create new test article with unique URL
    article = Article(
        link=f"https://example.com/article-{uuid.uuid4()}",
        title="Test Article",
        summary="Test summary",
        content="Test article content",
        published=datetime(2025, 1, 1, 0, 0, 0),
        source="Test Source",
    )
    db_session.add(article)
    db_session.commit()
    db_session.refresh(article)
    return article


@pytest.fixture
def test_post(db_session, test_user, test_article):
    """Create test post"""
    from database import Post

    post = Post(
        user_id=test_user.id,
        article_id=test_article.id,
        article_title=test_article.title,
        twitter_content="Test post content",
        instagram_caption="Test Instagram caption",
        platforms=["instagram"],
        status="draft",
    )
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)
    return post


@pytest.fixture
def test_post_with_image(db_session, test_user, test_article):
    """Create test post with existing Instagram image"""
    from database import Post
    from datetime import datetime

    post = Post(
        user_id=test_user.id,
        article_id=test_article.id,
        article_title=test_article.title,
        twitter_content="Test post with image",
        instagram_caption="Test caption",
        instagram_image_url="/static/instagram_images/test.jpg",
        platforms=["instagram"],
        status="draft",
    )
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)

    # Create image record if InstagramImage table exists
    try:
        from database import InstagramImage

        image = InstagramImage(
            post_id=post.id,
            user_id=test_user.id,
            article_id=test_article.id,
            prompt="Test prompt",
            image_url="/static/instagram_images/test.jpg",
            width=1024,
            height=1024,
            status="active",
        )
        db_session.add(image)
        db_session.commit()
    except:
        pass  # InstagramImage table might not exist yet

    return post


@pytest.fixture
def test_users(db_session):
    """Create multiple test users for concurrent testing"""
    from database import User
    from utils.auth import hash_password

    users = []
    for i in range(5):
        user = User(
            email=f"testuser{i}@example.com",
            password_hash=hash_password("testpassword123"),
            full_name=f"Test User {i}",
            is_active=True,
            is_verified=True,
            is_admin=False,
        )
        db_session.add(user)
        users.append(user)

    db_session.commit()

    # Add posts to each user
    from database import Post, Article
    from datetime import datetime

    article = Article(
        link=f"https://example.com/multi-user-article-{uuid.uuid4()}",
        title="Multi User Test Article",
        summary="Test summary",
        published=datetime.now(),
    )
    db_session.add(article)
    db_session.commit()

    for user in users:
        post = Post(
            user_id=user.id,
            article_id=article.id,
            article_title=article.title,
            twitter_content=f"Post for {user.email}",
            instagram_caption=f"Post for {user.email}",
            platforms=["instagram"],
            status="draft",
        )
        db_session.add(post)
        user.posts = [post]  # Add posts attribute

    db_session.commit()

    return users


# ============================================================================
# Helper fixture for patching SessionLocal in tests
# ============================================================================


@pytest.fixture
def patch_session_local(test_engine):
    """
    Context manager to patch database.SessionLocal to use test engine.
    This allows async services to use the same test database.
    """
    import database
    from sqlalchemy.orm import sessionmaker
    from contextlib import contextmanager

    @contextmanager
    def _patch():
        original_session_local = database.SessionLocal
        TestSessionLocal = sessionmaker(bind=test_engine)
        database.SessionLocal = TestSessionLocal
        try:
            yield
        finally:
            database.SessionLocal = original_session_local

    return _patch


# ============================================================================
# Instagram OAuth & Publishing fixtures
# ============================================================================


@pytest.fixture
def test_user_with_instagram(db_session, test_user):
    """Test user with Instagram connected via OAuth"""
    from database_social_media import SocialMediaConnection
    from utils.encryption import encrypt_value
    from datetime import datetime, timedelta

    connection = SocialMediaConnection(
        user_id=test_user.id,
        platform="instagram",
        platform_user_id="ig_17841234567890",
        platform_username="testinstagram",
        access_token=encrypt_value("test_page_access_token_long_lived"),
        refresh_token=None,  # Instagram uses long-lived tokens
        token_expires_at=datetime.utcnow() + timedelta(days=60),
        is_active=True,
        scopes="instagram_basic,instagram_content_publish",
    )
    db_session.add(connection)
    db_session.commit()

    return test_user


@pytest.fixture
def test_post_with_instagram_image(db_session, test_user, test_article):
    """Post with Instagram image and caption ready for publishing"""
    from database import Post

    post = Post(
        user_id=test_user.id,
        article_id=test_article.id,
        article_title=test_article.title,
        twitter_content="Short tweet version",
        instagram_caption="Amazing AI breakthrough! 🚀 #AI #Technology #Innovation #MachineLearning",
        instagram_image_url="https://example.com/static/instagram_images/test-image.jpg",
        instagram_image_prompt="Modern AI technology visualization with vibrant colors",
        platforms=["instagram"],
        status="draft",
    )
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)

    return post


@pytest.fixture
def other_user(db_session):
    """Create another test user for authorization tests"""
    from database import User
    from utils.auth import hash_password

    user = User(
        email="other@example.com",
        password_hash=hash_password("otherpassword123"),
        full_name="Other User",
        is_active=True,
        is_verified=True,
        is_admin=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


@pytest.fixture
def other_user_headers(other_user, db_session):
    """Generate auth headers for other user using session token"""
    from utils.auth import generate_session_token
    from database import UserSession
    from datetime import datetime, timedelta

    # Create session token
    token = generate_session_token()
    session = UserSession(
        user_id=other_user.id, token=token, expires_at=datetime.utcnow() + timedelta(days=1)
    )
    db_session.add(session)
    db_session.commit()

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers(test_user, db_session):
    """Generate auth headers for test user using session token"""
    from utils.auth import generate_session_token
    from database import UserSession
    from datetime import datetime, timedelta

    # Create session token
    token = generate_session_token()
    session = UserSession(
        user_id=test_user.id, token=token, expires_at=datetime.utcnow() + timedelta(days=1)
    )
    db_session.add(session)
    db_session.commit()

    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# NEW FIXTURES FOR TEST COVERAGE ENHANCEMENT
# ============================================================================


@pytest.fixture
async def mock_linkedin_publisher():
    """Mock LinkedIn publisher for testing"""
    from unittest.mock import AsyncMock

    publisher = AsyncMock()
    publisher.publish.return_value = {
        "success": True,
        "platform_post_id": "urn:li:share:123456",
        "platform_url": "https://www.linkedin.com/feed/update/urn:li:share:123456",
        "published_at": "2025-10-26T12:00:00",
    }
    return publisher


@pytest.fixture
async def mock_instagram_publisher():
    """Mock Instagram publisher for testing"""
    from unittest.mock import AsyncMock

    publisher = AsyncMock()
    publisher.publish.return_value = {
        "success": True,
        "platform_post_id": "instagram_123456",
        "platform_url": "https://www.instagram.com/p/instagram_123456",
        "published_at": "2025-10-26T12:00:00",
    }
    return publisher


@pytest.fixture
async def mock_twitter_publisher():
    """Mock Twitter publisher for testing"""
    from unittest.mock import AsyncMock

    publisher = AsyncMock()
    publisher.publish.return_value = {
        "success": True,
        "platform_post_id": "1234567890",
        "platform_url": "https://twitter.com/user/status/1234567890",
        "published_at": "2025-10-26T12:00:00",
    }
    return publisher


@pytest.fixture
async def mock_threads_publisher():
    """Mock Threads publisher for testing"""
    from unittest.mock import AsyncMock

    publisher = AsyncMock()
    publisher.publish.return_value = {
        "success": True,
        "platform_post_id": "threads_123456",
        "platform_url": "https://www.threads.net/@user/post/threads_123456",
        "published_at": "2025-10-26T12:00:00",
    }
    return publisher


@pytest.fixture
def test_oauth_connection(db_session, test_user):
    """Create test OAuth connection for LinkedIn"""
    from database_social_media import SocialMediaConnection
    from utils.encryption import encrypt_value
    from datetime import datetime, timedelta

    connection = SocialMediaConnection(
        user_id=test_user.id,
        platform="linkedin",
        platform_user_id="test_user_123",
        platform_username="testuser",
        encrypted_access_token=encrypt_value("test_access_token"),
        encrypted_refresh_token=encrypt_value("test_refresh_token"),
        token_type="Bearer",
        expires_at=datetime.utcnow() + timedelta(days=60),
        is_active=True,
        scope="r_liteprofile,w_member_social",
    )
    db_session.add(connection)
    db_session.commit()
    db_session.refresh(connection)
    return connection


@pytest.fixture
def test_oauth_connection_twitter(db_session, test_user):
    """Create test OAuth connection for Twitter"""
    from database_social_media import SocialMediaConnection
    from utils.encryption import encrypt_value
    from datetime import datetime, timedelta

    connection = SocialMediaConnection(
        user_id=test_user.id,
        platform="twitter",
        platform_user_id="twitter_user_123",
        platform_username="twitteruser",
        encrypted_access_token=encrypt_value("test_twitter_access_token"),
        encrypted_refresh_token=encrypt_value("test_twitter_access_secret"),  # Twitter uses refresh token for secret
        token_type="Bearer",
        expires_at=datetime.utcnow() + timedelta(days=365),
        is_active=True,
        scope="tweet.read,tweet.write,users.read",
    )
    db_session.add(connection)
    db_session.commit()
    db_session.refresh(connection)
    return connection


@pytest.fixture
def test_oauth_connection_threads(db_session, test_user):
    """Create test OAuth connection for Threads"""
    from database_social_media import SocialMediaConnection
    from utils.encryption import encrypt_value
    from datetime import datetime, timedelta

    connection = SocialMediaConnection(
        user_id=test_user.id,
        platform="threads",
        platform_user_id="threads_user_123",
        platform_username="threadsuser",
        encrypted_access_token=encrypt_value("test_threads_access_token"),
        token_type="Bearer",
        expires_at=datetime.utcnow() + timedelta(days=60),
        is_active=True,
        scope="threads_basic,threads_content_publish",
    )
    db_session.add(connection)
    db_session.commit()
    db_session.refresh(connection)
    return connection


@pytest.fixture
def test_post_ready_for_publishing(db_session, test_user, test_article):
    """Create a test post with content ready for all platforms"""
    from database import Post

    post = Post(
        user_id=test_user.id,
        article_id=test_article.id,
        article_title=test_article.title,
        twitter_content="Test tweet content #AI",
        linkedin_content="Test LinkedIn content with more details about AI advancements.",
        threads_content="Test Threads content for discussion",
        instagram_caption="Test Instagram caption with hashtags #AI #Tech",
        platforms=["twitter", "linkedin", "threads", "instagram"],
        status="ready",
        ai_summary="AI-generated summary of the article",
    )
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)
    return post


@pytest.fixture
def test_admin_user(db_session):
    """Create an admin user for testing admin endpoints (idempotent)"""
    from database import User
    from utils.auth import hash_password

    # Check if admin user already exists (for session-scoped database)
    user = db_session.query(User).filter(User.email == "admin@example.com").first()
    if user:
        return user

    # Create new admin user
    user = User(
        email="admin@example.com",
        password_hash=hash_password("adminpassword123"),
        full_name="Admin User",
        is_active=True,
        is_verified=True,
        is_admin=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_headers(test_admin_user, db_session):
    """Generate auth headers for admin user"""
    from utils.auth import generate_session_token
    from database import UserSession
    from datetime import datetime, timedelta

    # Create session token
    token = generate_session_token()
    session = UserSession(
        user_id=test_admin_user.id, token=token, expires_at=datetime.utcnow() + timedelta(days=1)
    )
    db_session.add(session)
    db_session.commit()

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_api_key(db_session, test_user):
    """Create test API key for user"""
    from database import UserApiKey
    from utils.encryption import encrypt_api_key

    api_key = UserApiKey(
        user_id=test_user.id, provider="openai", encrypted_key=encrypt_api_key("sk-test-key-12345")
    )
    db_session.add(api_key)
    db_session.commit()
    db_session.refresh(api_key)
    return api_key


@pytest.fixture
def multiple_articles(db_session):
    """Create multiple test articles for batch testing (idempotent)"""
    from database import Article
    from datetime import datetime, timedelta

    articles = []
    for i in range(5):
        # Create new article with unique URL
        article = Article(
            link=f"https://example.com/article-{uuid.uuid4()}",
            title=f"Test Article {i}",
            summary=f"Summary for test article {i}",
            content=f"Content for test article {i}",
            published=datetime.utcnow() - timedelta(hours=i),
            source=f"Source {i % 2}",
        )
        db_session.add(article)
        articles.append(article)

    db_session.commit()
    for article in articles:
        db_session.refresh(article)

    return articles


# ============================================================================
# Async Test Fixtures (for async endpoint testing)
# ============================================================================


@pytest.fixture
def test_user_token(db_session, test_user):
    """Create a valid session token for test user"""
    from utils.auth import generate_session_token
    from database import UserSession
    from datetime import datetime, timedelta

    token = generate_session_token()
    session = UserSession(
        user_id=test_user.id, token=token, expires_at=datetime.utcnow() + timedelta(days=1)
    )
    db_session.add(session)
    db_session.commit()

    return token


@pytest.fixture
def async_client(test_engine):
    """Create async HTTP client with database override

    Note: This is a sync fixture that returns an async context manager.
    Use in tests like: async with async_client as client:
    """
    from httpx import AsyncClient
    from main import app
    from database import get_db
    import database
    from sqlalchemy.orm import sessionmaker

    TestSessionLocal = sessionmaker(bind=test_engine)

    # Patch SessionLocal globally
    original_session_local = database.SessionLocal
    database.SessionLocal = TestSessionLocal

    def override_get_db():
        session = TestSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db

    # Create a context manager class
    class AsyncClientContextManager:
        async def __aenter__(self):
            self.client = AsyncClient(app=app, base_url="http://test")
            return await self.client.__aenter__()

        async def __aexit__(self, *args):
            result = await self.client.__aexit__(*args)
            app.dependency_overrides.clear()
            database.SessionLocal = original_session_local
            return result

    return AsyncClientContextManager()


@pytest.fixture
def test_db(db_session):
    """Alias for db_session to support legacy test code"""
    return db_session
