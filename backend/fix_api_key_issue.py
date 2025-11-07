#!/usr/bin/env python3
"""
Fix API Key Storage Issue

This script addresses the issue where posts show empty content due to:
1. Missing API keys in UserApiKey table
2. Corrupted/invalid API key in Settings table

Usage:
    python fix_api_key_issue.py --user-email test@example.com --api-key sk-your-openai-key-here
"""

import argparse
import sys
from dotenv import load_dotenv
load_dotenv()

from database import SessionLocal, User, UserApiKey, Settings
from utils.encryption import encrypt_api_key, decrypt_api_key
from datetime import datetime

def fix_settings_table():
    """Remove corrupted api_key from Settings table"""
    db = SessionLocal()
    try:
        # Delete the corrupted api_key setting
        corrupted = db.query(Settings).filter(Settings.key == 'api_key').first()
        if corrupted:
            print(f"Found corrupted api_key in Settings table: '{corrupted.value}'")
            db.delete(corrupted)
            db.commit()
            print("✓ Removed corrupted api_key from Settings table")
        else:
            print("No corrupted api_key found in Settings table")
    finally:
        db.close()

def add_api_key_for_user(email: str, api_key: str, provider: str = "openai"):
    """Add API key for a specific user"""
    db = SessionLocal()
    try:
        # Find user
        user = db.query(User).filter(User.email == email.lower()).first()
        if not user:
            print(f"✗ Error: User '{email}' not found")
            return False

        print(f"Found user: {user.full_name} (ID: {user.id})")

        # Validate API key format
        if not api_key or len(api_key) < 10:
            print("✗ Error: Invalid API key format")
            return False

        # Encrypt API key
        try:
            encrypted_key = encrypt_api_key(api_key)
            print(f"✓ API key encrypted successfully")
        except Exception as e:
            print(f"✗ Error encrypting API key: {str(e)}")
            return False

        # Check if API key already exists
        existing_key = db.query(UserApiKey).filter(
            UserApiKey.user_id == user.id,
            UserApiKey.provider == provider
        ).first()

        if existing_key:
            # Update existing key
            existing_key.encrypted_key = encrypted_key
            existing_key.updated_at = datetime.utcnow()
            existing_key.is_active = True
            print(f"✓ Updated existing {provider} API key")
        else:
            # Create new key
            new_key = UserApiKey(
                user_id=user.id,
                provider=provider,
                encrypted_key=encrypted_key,
                name=f"{provider.title()} API Key",
                is_active=True
            )
            db.add(new_key)
            print(f"✓ Created new {provider} API key")

        db.commit()

        # Verify the key can be decrypted
        saved_key = db.query(UserApiKey).filter(
            UserApiKey.user_id == user.id,
            UserApiKey.provider == provider
        ).first()

        if saved_key:
            decrypted = decrypt_api_key(saved_key.encrypted_key)
            if decrypted and decrypted == api_key:
                print(f"✓ Verification successful: API key can be decrypted correctly")
                print(f"\n✅ API key saved successfully for {email}")
                return True
            else:
                print(f"✗ Verification failed: API key cannot be decrypted correctly")
                return False

        return False

    except Exception as e:
        print(f"✗ Error: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()

def verify_user_api_keys(email: str):
    """Verify API keys for a user"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower()).first()
        if not user:
            print(f"✗ User '{email}' not found")
            return

        print(f"\n{'='*60}")
        print(f"API Keys for {user.full_name} ({email})")
        print(f"{'='*60}")

        api_keys = db.query(UserApiKey).filter(UserApiKey.user_id == user.id).all()

        if not api_keys:
            print("No API keys found")
            return

        for key in api_keys:
            print(f"\nProvider: {key.provider}")
            print(f"Active: {key.is_active}")
            print(f"Created: {key.created_at}")
            print(f"Updated: {key.updated_at}")

            # Try to decrypt
            try:
                decrypted = decrypt_api_key(key.encrypted_key)
                if decrypted:
                    print(f"Decryption: ✓ SUCCESS ({decrypted[:10]}...)")
                else:
                    print(f"Decryption: ✗ FAILED")
            except Exception as e:
                print(f"Decryption: ✗ ERROR - {str(e)}")

        print(f"\n{'='*60}")

    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(
        description="Fix API key storage issues and add API keys for users",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fix corrupted Settings table
  python fix_api_key_issue.py --fix-settings

  # Add API key for a user
  python fix_api_key_issue.py --user-email test@example.com --api-key sk-...

  # Verify user's API keys
  python fix_api_key_issue.py --verify test@example.com

  # Fix and add API key in one command
  python fix_api_key_issue.py --fix-settings --user-email test@example.com --api-key sk-...
        """
    )

    parser.add_argument(
        "--fix-settings",
        action="store_true",
        help="Remove corrupted api_key from Settings table"
    )

    parser.add_argument(
        "--user-email",
        type=str,
        help="User email address"
    )

    parser.add_argument(
        "--api-key",
        type=str,
        help="API key to save (OpenAI format: sk-...)"
    )

    parser.add_argument(
        "--provider",
        type=str,
        default="openai",
        choices=["openai", "anthropic"],
        help="API provider (default: openai)"
    )

    parser.add_argument(
        "--verify",
        type=str,
        metavar="EMAIL",
        help="Verify API keys for a user"
    )

    args = parser.parse_args()

    # Show help if no arguments
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    success = True

    # Fix settings table
    if args.fix_settings:
        print("\n=== Fixing Settings Table ===")
        fix_settings_table()

    # Add API key for user
    if args.user_email and args.api_key:
        print(f"\n=== Adding API Key for {args.user_email} ===")
        if not add_api_key_for_user(args.user_email, args.api_key, args.provider):
            success = False
    elif args.user_email and not args.api_key:
        print("✗ Error: --api-key is required when --user-email is specified")
        success = False
    elif args.api_key and not args.user_email:
        print("✗ Error: --user-email is required when --api-key is specified")
        success = False

    # Verify user API keys
    if args.verify:
        verify_user_api_keys(args.verify)

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
