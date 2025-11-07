#!/usr/bin/env python3
"""
Helper script to re-encrypt API keys with current ENCRYPTION_KEY

This script helps recover from ENCRYPTION_KEY changes by allowing you to:
1. Input your API key
2. Re-encrypt it with the current ENCRYPTION_KEY
3. Update the database
"""

import sys
import getpass
from database import SessionLocal
from utils.encryption import encrypt_value
import sqlite3


def main():
    print("=" * 60)
    print("API Key Re-encryption Helper")
    print("=" * 60)
    print()
    print("This script will help you re-add your API key with the current")
    print("ENCRYPTION_KEY setting.")
    print()

    # Get user ID
    user_id = input("Enter your user ID (default: 6): ").strip()
    if not user_id:
        user_id = "6"

    try:
        user_id = int(user_id)
    except ValueError:
        print("Error: User ID must be a number")
        sys.exit(1)

    # Get provider
    provider = input("Enter AI provider (openai/anthropic) [default: openai]: ").strip().lower()
    if not provider:
        provider = "openai"

    if provider not in ['openai', 'anthropic']:
        print("Error: Provider must be 'openai' or 'anthropic'")
        sys.exit(1)

    # Get API key (hidden input)
    print()
    print(f"Enter your {provider.upper()} API key:")
    if provider == 'openai':
        print("  (Format: sk-...)")
    else:
        print("  (Format: sk-ant-...)")

    api_key = getpass.getpass("API Key: ").strip()

    if not api_key:
        print("Error: API key cannot be empty")
        sys.exit(1)

    # Validate format
    if provider == 'openai' and not api_key.startswith('sk-'):
        print("Warning: OpenAI keys usually start with 'sk-'")
        confirm = input("Continue anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            sys.exit(0)
    elif provider == 'anthropic' and not api_key.startswith('sk-ant-'):
        print("Warning: Anthropic keys usually start with 'sk-ant-'")
        confirm = input("Continue anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            sys.exit(0)

    # Encrypt the key
    print()
    print("Encrypting API key with current ENCRYPTION_KEY...")
    try:
        encrypted_key = encrypt_value(api_key)
        print(f"✓ Successfully encrypted (length: {len(encrypted_key)})")
    except Exception as e:
        print(f"✗ Encryption failed: {e}")
        sys.exit(1)

    # Update database
    print()
    print("Updating database...")

    conn = sqlite3.connect('ai_news.db')
    cursor = conn.cursor()

    try:
        # Check if user has existing API key
        cursor.execute(
            'SELECT id FROM user_api_keys WHERE user_id = ? AND provider = ?',
            (user_id, provider)
        )
        existing = cursor.fetchone()

        if existing:
            # Update existing
            cursor.execute(
                '''UPDATE user_api_keys
                   SET encrypted_key = ?, updated_at = datetime('now')
                   WHERE user_id = ? AND provider = ?''',
                (encrypted_key, user_id, provider)
            )
            print(f"✓ Updated existing {provider} API key for user {user_id}")
        else:
            # Insert new
            cursor.execute(
                '''INSERT INTO user_api_keys (user_id, provider, encrypted_key, created_at, updated_at)
                   VALUES (?, ?, ?, datetime('now'), datetime('now'))''',
                (user_id, provider, encrypted_key)
            )
            print(f"✓ Added new {provider} API key for user {user_id}")

        conn.commit()
        print("✓ Database updated successfully")

        # Verify decryption works
        print()
        print("Verifying decryption...")
        from utils.encryption import decrypt_value

        cursor.execute(
            'SELECT encrypted_key FROM user_api_keys WHERE user_id = ? AND provider = ?',
            (user_id, provider)
        )
        row = cursor.fetchone()

        if row:
            decrypted = decrypt_value(row[0])
            if decrypted == api_key:
                print("✓ Verification successful - decryption works correctly")
            else:
                print("✗ Verification failed - decrypted value doesn't match")

    except Exception as e:
        conn.rollback()
        print(f"✗ Database update failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()

    print()
    print("=" * 60)
    print("SUCCESS!")
    print("=" * 60)
    print()
    print("Your API key has been re-encrypted and stored in the database.")
    print("You can now use the post generation feature.")
    print()


if __name__ == "__main__":
    main()
