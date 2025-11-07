#!/usr/bin/env python3
"""Verify all imports work correctly"""
import sys


def check_section(name, checks):
    """Check a section of imports"""
    print(f"\n{name}")
    all_ok = True
    for check_name, check_fn in checks:
        try:
            check_fn()
            print(f"  OK {check_name}")
        except ImportError as e:
            print(f"  FAIL {check_name}: {e}")
            all_ok = False
        except Exception as e:
            print(f"  ERROR {check_name}: {e}")
            all_ok = False
    return all_ok


def main():
    """Run all verification checks"""
    all_sections_ok = True

    # Core Dependencies
    def check_core():
        from fastapi import FastAPI
        from uvicorn import run
        from sqlalchemy import create_engine
        from pydantic import BaseModel, EmailStr
        from dotenv import load_dotenv

    core_checks = [
        ("fastapi", lambda: __import__("fastapi")),
        ("uvicorn", lambda: __import__("uvicorn")),
        ("sqlalchemy", lambda: __import__("sqlalchemy")),
        ("pydantic", lambda: __import__("pydantic")),
        ("pydantic EmailStr", lambda: __import__("pydantic").EmailStr),
        ("python-dotenv", lambda: __import__("dotenv")),
        ("python-multipart", lambda: __import__("multipart")),
    ]
    all_sections_ok &= check_section("Core Dependencies", core_checks)

    # Database
    db_checks = [
        ("alembic", lambda: __import__("alembic")),
    ]
    all_sections_ok &= check_section("Database", db_checks)

    # Authentication & Security
    auth_checks = [
        ("bcrypt", lambda: __import__("bcrypt")),
        ("cryptography", lambda: __import__("cryptography")),
        ("cryptography.fernet", lambda: __import__("cryptography.fernet").fernet.Fernet),
        ("passlib", lambda: __import__("passlib")),
        ("passlib.hash", lambda: __import__("passlib.hash")),
        ("python-jose", lambda: __import__("jose")),
        ("jose.jwt", lambda: __import__("jose.jwt")),
    ]
    all_sections_ok &= check_section("Authentication & Security", auth_checks)

    # Phase 3: OAuth & Email
    phase3_checks = [
        ("authlib", lambda: __import__("authlib")),
        (
            "authlib OAuth",
            lambda: __import__(
                "authlib.integrations.starlette_client"
            ).integrations.starlette_client.OAuth,
        ),
        ("httpx", lambda: __import__("httpx")),
        ("sendgrid", lambda: __import__("sendgrid")),
        ("sendgrid.SendGridAPIClient", lambda: __import__("sendgrid").SendGridAPIClient),
        ("jinja2", lambda: __import__("jinja2")),
        ("jinja2.Template", lambda: __import__("jinja2").Template),
    ]
    all_sections_ok &= check_section("Phase 3: OAuth & Email", phase3_checks)

    # Phase 4: Security & Monitoring
    phase4_checks = [
        ("user_agents", lambda: __import__("user_agents")),
        ("user_agents.parse", lambda: __import__("user_agents").parse),
    ]
    all_sections_ok &= check_section("Phase 4: Security & Monitoring", phase4_checks)

    # Optional Production
    optional_checks = [
        ("redis", lambda: __import__("redis")),
        ("aiofiles", lambda: __import__("aiofiles")),
    ]
    check_section("Optional Production Dependencies", optional_checks)

    # Testing
    test_checks = [
        ("pytest", lambda: __import__("pytest")),
        ("pytest-asyncio", lambda: __import__("pytest_asyncio")),
    ]
    check_section("Testing Dependencies", test_checks)

    # Backend Modules
    print("\nBackend Modules")
    try:
        from database import User, UserSession, UserApiKey

        print("  OK database models")
    except ImportError as e:
        print(f"  FAIL database models: {e}")
        all_sections_ok = False

    try:
        from utils.auth import hash_password, verify_password

        print("  OK utils.auth")
    except ImportError as e:
        print(f"  FAIL utils.auth: {e}")
        all_sections_ok = False

    try:
        from utils.encryption import encrypt_api_key, decrypt_api_key

        print("  OK utils.encryption")
    except ImportError as e:
        print(f"  FAIL utils.encryption: {e}")
        all_sections_ok = False

    try:
        from utils.email import send_verification_email

        print("  OK utils.email")
    except ImportError as e:
        print(f"  FAIL utils.email: {e}")
        all_sections_ok = False

    try:
        from utils.oauth import get_google_auth_url, create_or_update_oauth_user

        print("  OK utils.oauth")
    except ImportError as e:
        print(f"  FAIL utils.oauth: {e}")
        all_sections_ok = False

    try:
        from utils.rate_limiter import RateLimiter

        print("  OK utils.rate_limiter")
    except ImportError as e:
        print(f"  FAIL utils.rate_limiter: {e}")
        all_sections_ok = False

    try:
        from utils.security_monitor import SecurityMonitor

        print("  OK utils.security_monitor")
    except ImportError as e:
        print(f"  FAIL utils.security_monitor: {e}")
        all_sections_ok = False

    try:
        from utils.password_validator import check_password_strength, validate_password_strength

        print("  OK utils.password_validator")
    except ImportError as e:
        print(f"  FAIL utils.password_validator: {e}")
        all_sections_ok = False

    try:
        from utils.audit_logger import AuditLogger

        print("  OK utils.audit_logger")
    except ImportError as e:
        print(f"  FAIL utils.audit_logger: {e}")
        all_sections_ok = False

    # Configuration
    try:
        from utils.config import Config

        print("  OK utils.config")
    except ImportError as e:
        print(f"  FAIL utils.config: {e}")
        all_sections_ok = False

    # API Endpoints
    print("\nAPI Endpoints")
    try:
        from api import auth

        print("  OK api.auth")
    except ImportError as e:
        print(f"  FAIL api.auth: {e}")

    try:
        from api import oauth

        print("  OK api.oauth")
    except ImportError as e:
        print(f"  FAIL api.oauth: {e}")

    try:
        from api import settings

        print("  OK api.settings")
    except ImportError as e:
        print(f"  FAIL api.settings: {e}")

    try:
        from api import profile

        print("  OK api.profile")
    except ImportError as e:
        print(f"  FAIL api.profile: {e}")

    try:
        from api import security

        print("  OK api.security")
    except ImportError as e:
        print(f"  FAIL api.security: {e}")

    try:
        from api import guest

        print("  OK api.guest")
    except ImportError as e:
        print(f"  FAIL api.guest: {e}")

    # Summary
    print("\n" + "=" * 60)
    if all_sections_ok:
        print("SUCCESS: All required imports working correctly")
        return 0
    else:
        print("WARNING: Some imports failed (check above)")
        print("Note: Optional dependencies and API modules are not critical")
        return 1


if __name__ == "__main__":
    sys.exit(main())
