#!/usr/bin/env python3
"""
Script to add improved error handling and API key validation
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from dotenv import load_dotenv
load_dotenv()

print("=" * 80)
print("API KEY VALIDATION AND FIX")
print("=" * 80)

from database import SessionLocal, UserApiKey
from utils.encryption import decrypt_api_key

db = SessionLocal()

print("\n1. Checking current API keys in database...")
user_api_keys = db.query(UserApiKey).all()

for key in user_api_keys:
    print(f"\nUser ID: {key.user_id}, Provider: {key.provider}")

    try:
        decrypted = decrypt_api_key(key.encrypted_key)
        if decrypted:
            print(f"   Decrypted: {decrypted[:20]}...")

            # Quick format check
            if "test" in decrypted.lower():
                print(f"   ⚠️  WARNING: This appears to be a TEST KEY")
                print(f"   ✗ This key will NOT work with the real OpenAI API")
                print(f"   → Action required: Replace with real API key from https://platform.openai.com/api-keys")
            elif key.provider == "openai" and not decrypted.startswith("sk-"):
                print(f"   ✗ INVALID FORMAT: OpenAI keys must start with 'sk-'")
            elif key.provider == "openai" and decrypted.startswith("sk-"):
                print(f"   ✓ Format looks valid")

                # Test the key
                print(f"   Testing API key...")
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=decrypted, timeout=10.0)
                    models = client.models.list()
                    print(f"   ✓ API KEY IS VALID! ({len(list(models.data))} models available)")
                except Exception as e:
                    error_str = str(e)
                    if "401" in error_str or "invalid_api_key" in error_str:
                        print(f"   ✗ API KEY IS INVALID")
                        print(f"   Error: {error_str[:100]}")
                        print(f"\n   → You need to replace this with a valid OpenAI API key")
                        print(f"   → Get one from: https://platform.openai.com/api-keys")
                    else:
                        print(f"   ✗ API test failed: {error_str[:100]}")

    except Exception as e:
        print(f"   ✗ Failed to decrypt: {e}")

db.close()

print("\n" + "=" * 80)
print("INSTRUCTIONS TO FIX")
print("=" * 80)

print("""
The AI content generation is failing because the API key is invalid.

STEP-BY-STEP FIX:

1. Get a valid OpenAI API key:
   → Go to: https://platform.openai.com/api-keys
   → Click "Create new secret key"
   → Copy the key (starts with "sk-proj-" or "sk-")
   → IMPORTANT: Copy it now, you won't see it again!

2. Update the API key in the UI:
   → Open your browser
   → Go to: http://localhost:8080 (or your app URL)
   → Log in if needed
   → Click "Settings" (or Profile icon)
   → Find "API Keys" section
   → Click "Add API Key" or "Update"
   → Select "OpenAI" as provider
   → Paste your new API key
   → Click "Save"

3. Test the generation:
   → Go to "Articles" tab
   → Select 1-2 articles
   → Click "Generate Post"
   → Select platforms (Twitter, LinkedIn, etc.)
   → Click "Generate"
   → Should now complete successfully!

ALTERNATIVE: Update via command line:
""")

print("""
   python << 'EOF'
from database import SessionLocal, UserApiKey
from utils.encryption import encrypt_api_key

db = SessionLocal()

# Find the user's OpenAI key
key = db.query(UserApiKey).filter(
    UserApiKey.user_id == 1,
    UserApiKey.provider == 'openai'
).first()

if key:
    # Replace with your REAL OpenAI API key
    new_api_key = "sk-proj-YOUR_REAL_KEY_HERE"
    key.encrypted_key = encrypt_api_key(new_api_key)
    db.commit()
    print("✓ API key updated successfully!")
else:
    print("✗ No OpenAI key found for user 1")

db.close()
EOF
""")

print("=" * 80)
