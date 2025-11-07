"""
Admin Setup Script - Configure Default AI API Keys for Guest Users

This script allows administrators to set up default API keys that will be used
for guest users who don't have their own API keys.

Usage:
    python setup_admin_defaults.py

Environment Variables Required:
    ADMIN_DEFAULT_API_KEY - The API key to use as default (OpenAI, Anthropic, or DeepSeek)
    ADMIN_DEFAULT_PROVIDER - Provider name (openai, anthropic, or deepseek)
    ENCRYPTION_KEY - Encryption key for secure storage
"""

import sys
import os
from pathlib import Path
from getpass import getpass

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from database import SessionLocal, AdminSettings
from cryptography.fernet import Fernet
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_encryption_key():
    """Get or generate encryption key"""
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

    if not ENCRYPTION_KEY:
        logger.warning("ENCRYPTION_KEY not found in environment. Generating a new one...")
        ENCRYPTION_KEY = Fernet.generate_key().decode()
        logger.info(f"Generated ENCRYPTION_KEY: {ENCRYPTION_KEY}")
        logger.info("IMPORTANT: Add this to your .env file as ENCRYPTION_KEY={key}")

        # Ask user if they want to continue
        response = input("Continue with this key? (y/n): ")
        if response.lower() != 'y':
            logger.info("Setup cancelled")
            sys.exit(0)

    return ENCRYPTION_KEY


def encrypt_api_key(api_key: str, encryption_key: str) -> str:
    """Encrypt API key using Fernet encryption"""
    cipher_suite = Fernet(encryption_key.encode())
    encrypted_key = cipher_suite.encrypt(api_key.encode()).decode()
    return encrypted_key


def setup_admin_api_key(interactive=True):
    """
    Setup admin default API key for guest users

    Args:
        interactive: If True, prompts for input. If False, uses environment variables.
    """
    logger.info("=" * 60)
    logger.info("Admin Default API Key Setup")
    logger.info("=" * 60)

    db = SessionLocal()

    try:
        # Get encryption key
        ENCRYPTION_KEY = get_encryption_key()

        # Get API key and provider
        if interactive:
            print("\nSupported AI Providers:")
            print("  1. OpenAI (GPT-4, GPT-3.5)")
            print("  2. Anthropic (Claude)")
            print("  3. DeepSeek (DeepSeek AI)")

            provider_choice = input("\nSelect provider (1-3): ").strip()
            provider_map = {
                "1": "openai",
                "2": "anthropic",
                "3": "deepseek"
            }

            provider = provider_map.get(provider_choice)
            if not provider:
                logger.error("Invalid provider choice")
                return False

            api_key = getpass(f"Enter {provider} API key (input will be hidden): ").strip()

            if not api_key:
                logger.error("API key cannot be empty")
                return False
        else:
            # Use environment variables
            api_key = os.getenv("ADMIN_DEFAULT_API_KEY")
            provider = os.getenv("ADMIN_DEFAULT_PROVIDER", "openai")

            if not api_key:
                logger.error("ADMIN_DEFAULT_API_KEY environment variable not set")
                return False

        # Encrypt the API key
        logger.info("Encrypting API key...")
        encrypted_key = encrypt_api_key(api_key, ENCRYPTION_KEY)

        # Store in database
        logger.info(f"Storing {provider} API key in database...")

        # Update or create admin_default_api_key setting
        api_key_setting = db.query(AdminSettings).filter(
            AdminSettings.key == "admin_default_api_key"
        ).first()

        if api_key_setting:
            api_key_setting.value = encrypted_key
            api_key_setting.encrypted = True
            api_key_setting.description = f"Default {provider} API key for guest users"
            logger.info("Updated existing admin default API key")
        else:
            api_key_setting = AdminSettings(
                key="admin_default_api_key",
                value=encrypted_key,
                encrypted=True,
                description=f"Default {provider} API key for guest users"
            )
            db.add(api_key_setting)
            logger.info("Created new admin default API key")

        # Update or create default_ai_provider setting
        provider_setting = db.query(AdminSettings).filter(
            AdminSettings.key == "default_ai_provider"
        ).first()

        if provider_setting:
            provider_setting.value = provider
            provider_setting.description = "Default AI provider for guest users"
        else:
            provider_setting = AdminSettings(
                key="default_ai_provider",
                value=provider,
                encrypted=False,
                description="Default AI provider for guest users"
            )
            db.add(provider_setting)

        db.commit()

        logger.info("=" * 60)
        logger.info("SUCCESS: Admin default API key configured!")
        logger.info("=" * 60)
        logger.info(f"Provider: {provider}")
        logger.info(f"Encrypted: Yes")
        logger.info(f"Guest users can now generate posts using this API key")
        logger.info("=" * 60)

        return True

    except Exception as e:
        db.rollback()
        logger.error(f"Error setting up admin API key: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()


def view_current_settings():
    """View current admin settings"""
    logger.info("\nCurrent Admin Settings:")
    logger.info("-" * 60)

    db = SessionLocal()
    try:
        settings = db.query(AdminSettings).all()

        if not settings:
            logger.info("No admin settings found")
            return

        for setting in settings:
            value = setting.value
            if setting.encrypted:
                value = "***ENCRYPTED***"

            logger.info(f"{setting.key}: {value}")
            if setting.description:
                logger.info(f"  Description: {setting.description}")
    finally:
        db.close()

    logger.info("-" * 60)


def delete_admin_api_key():
    """Delete admin default API key"""
    logger.info("\nDeleting admin default API key...")

    db = SessionLocal()
    try:
        # Delete admin_default_api_key
        api_key_setting = db.query(AdminSettings).filter(
            AdminSettings.key == "admin_default_api_key"
        ).first()

        if api_key_setting:
            db.delete(api_key_setting)
            db.commit()
            logger.info("Admin default API key deleted")
        else:
            logger.info("No admin default API key found")
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting admin API key: {e}")
    finally:
        db.close()


def main():
    """Main interactive menu"""
    while True:
        print("\n" + "=" * 60)
        print("Admin Default API Key Setup")
        print("=" * 60)
        print("1. Setup/Update Admin Default API Key")
        print("2. View Current Settings")
        print("3. Delete Admin Default API Key")
        print("4. Exit")
        print("=" * 60)

        choice = input("\nSelect option (1-4): ").strip()

        if choice == "1":
            setup_admin_api_key(interactive=True)
        elif choice == "2":
            view_current_settings()
        elif choice == "3":
            confirm = input("Are you sure you want to delete the admin API key? (yes/no): ")
            if confirm.lower() == "yes":
                delete_admin_api_key()
        elif choice == "4":
            logger.info("Exiting...")
            break
        else:
            logger.warning("Invalid choice. Please select 1-4.")


if __name__ == "__main__":
    # Check if running in non-interactive mode (environment variables set)
    if os.getenv("ADMIN_DEFAULT_API_KEY"):
        logger.info("Running in non-interactive mode (using environment variables)")
        success = setup_admin_api_key(interactive=False)
        sys.exit(0 if success else 1)
    else:
        # Interactive mode
        main()
