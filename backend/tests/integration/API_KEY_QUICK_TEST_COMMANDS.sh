#!/bin/bash

###############################################################################
# API Key Testing - Quick Reference Commands
# Copy and paste these commands for manual testing
###############################################################################

BASE_URL="http://localhost:8000"

echo "=========================================="
echo "API Key Testing - Quick Commands"
echo "=========================================="
echo ""
echo "Copy these commands to test API key functionality:"
echo ""

cat <<'EOF'
# ============================================
# STEP 1: Login and Get Token
# ============================================

curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpassword123"}' | jq

# Extract token from response and set:
TOKEN="your_token_here"

# ============================================
# STEP 2: Add OpenAI API Key
# ============================================

curl -s -X POST http://localhost:8000/api/auth/api-keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "provider": "openai",
    "api_key": "sk-your-actual-openai-key-here",
    "name": "My OpenAI Key"
  }' | jq

# Expected Response:
# {
#   "success": true,
#   "message": "API key for openai saved successfully"
# }

# ============================================
# STEP 3: List Your API Keys
# ============================================

curl -s -X GET http://localhost:8000/api/auth/api-keys \
  -H "Authorization: Bearer $TOKEN" | jq

# Expected Response:
# [
#   {
#     "provider": "openai",
#     "name": "My OpenAI Key",
#     "created_at": "2025-10-28T...",
#     "updated_at": "2025-10-28T..."
#   }
# ]
# Note: Full API key should NOT be visible

# ============================================
# STEP 4: Verify Database Storage
# ============================================

sqlite3 ai_news.db <<EOSQL
.mode column
.headers on
SELECT
    id,
    provider,
    name,
    LENGTH(encrypted_key) as encrypted_len,
    is_active,
    created_at
FROM user_api_keys
WHERE provider='openai'
ORDER BY created_at DESC
LIMIT 1;
EOSQL

# Expected Output:
# id  provider  name           encrypted_len  is_active  created_at
# --  --------  -------------  -------------  ---------  ----------
# 1   openai    My OpenAI Key  140            1          2025-10-28...

# ============================================
# STEP 5: Test API Key (Optional)
# ============================================

curl -s -X POST http://localhost:8000/api/auth/api-keys/openai/test \
  -H "Authorization: Bearer $TOKEN" | jq

# Expected Response (if valid key):
# {
#   "success": true,
#   "provider": "openai",
#   "message": "API key is valid and working"
# }

# ============================================
# STEP 6: Create Test Article
# ============================================

curl -s -X POST http://localhost:8000/api/articles/add \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "url": "https://techcrunch.com/2024/10/28/ai-testing-article",
    "title": "AI Testing Best Practices",
    "summary": "A comprehensive guide to testing AI-powered applications, covering API integration, performance testing, and quality assurance strategies.",
    "source": "TechCrunch"
  }' | jq

# Extract article_id from response:
ARTICLE_ID=1  # Replace with actual ID

# ============================================
# STEP 7: Generate Post with API Key
# ============================================

curl -s -X POST http://localhost:8000/api/posts/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{
    \"article_ids\": [$ARTICLE_ID],
    \"platforms\": [\"twitter\", \"linkedin\"]
  }" | jq

# Expected Response:
# {
#   "post_id": 123,
#   "status": "processing",
#   "message": "Post generation started"
# }

# Extract post_id:
POST_ID=123  # Replace with actual ID

# ============================================
# STEP 8: Monitor Post Generation Status
# ============================================

# Poll every 2 seconds:
for i in {1..30}; do
  echo "=== Attempt $i/30 ==="
  curl -s -X GET http://localhost:8000/api/posts/$POST_ID/status \
    -H "Authorization: Bearer $TOKEN" | jq '.status, .progress, .current_step'

  STATUS=$(curl -s -X GET http://localhost:8000/api/posts/$POST_ID/status \
    -H "Authorization: Bearer $TOKEN" | jq -r '.status')

  if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
    echo "=== Final Status ==="
    curl -s -X GET http://localhost:8000/api/posts/$POST_ID/status \
      -H "Authorization: Bearer $TOKEN" | jq
    break
  fi

  sleep 2
done

# ============================================
# STEP 9: Verify Content Generated
# ============================================

# Get full post details:
curl -s -X GET http://localhost:8000/api/posts/$POST_ID/status \
  -H "Authorization: Bearer $TOKEN" | jq '.content'

# Check if content is empty:
TWITTER_CONTENT=$(curl -s -X GET http://localhost:8000/api/posts/$POST_ID/status \
  -H "Authorization: Bearer $TOKEN" | jq -r '.content.twitter // empty')

if [ -z "$TWITTER_CONTENT" ]; then
  echo "⚠️  WARNING: Content is EMPTY - API key issue detected!"
else
  echo "✓ Content generated successfully"
  echo "Twitter: ${#TWITTER_CONTENT} characters"
fi

# ============================================
# DIAGNOSTIC: Check Backend Logs
# ============================================

# If content is empty, check logs for:
# - "Failed to decrypt"
# - "API key"
# - "OpenAI"
# - Any exceptions

# Find backend process:
ps aux | grep uvicorn

# If running in terminal, check terminal output for errors

# ============================================
# DIAGNOSTIC: Test Encryption Directly
# ============================================

python3 <<PYTHON_EOF
import sys
sys.path.insert(0, '.')

from utils.encryption import encrypt_api_key, decrypt_api_key
from database import SessionLocal, UserApiKey

# Test encryption round-trip
test_key = "sk-test-encryption-verification"
encrypted = encrypt_api_key(test_key)
decrypted = decrypt_api_key(encrypted)

print(f"\n=== Encryption Test ===")
print(f"Original:  {test_key}")
print(f"Encrypted: {encrypted[:50]}... (length: {len(encrypted)})")
print(f"Decrypted: {decrypted}")
print(f"Match: {test_key == decrypted}")

# Test with database
db = SessionLocal()
db_key = db.query(UserApiKey).filter(UserApiKey.provider == "openai").first()

if db_key:
    db_decrypted = decrypt_api_key(db_key.encrypted_key)
    print(f"\n=== Database Key Test ===")
    print(f"Encrypted length: {len(db_key.encrypted_key)}")
    print(f"Decrypted: {db_decrypted[:10] if db_decrypted else 'None'}... (length: {len(db_decrypted) if db_decrypted else 0})")
    print(f"Decryption successful: {db_decrypted is not None}")
else:
    print("\nNo OpenAI key found in database")

db.close()
PYTHON_EOF

# ============================================
# DIAGNOSTIC: Check Environment Variables
# ============================================

echo ""
echo "=== Environment Check ==="
echo "ENCRYPTION_KEY set: $(grep -q ENCRYPTION_KEY .env && echo 'Yes' || echo 'No')"
echo "OPENAI_API_KEY set: $(env | grep -q OPENAI_API_KEY && echo 'Yes' || echo 'No')"
echo ""

# ============================================
# ERROR SCENARIOS
# ============================================

# Test 1: Generate post without API key
echo "=== Testing Error: No API Key ==="
curl -s -X DELETE http://localhost:8000/api/auth/api-keys/openai \
  -H "Authorization: Bearer $TOKEN" | jq

curl -s -X POST http://localhost:8000/api/posts/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"article_ids\": [$ARTICLE_ID], \"platforms\": [\"twitter\"]}" | jq

# Expected: Error about missing API key

# Test 2: Invalid provider
echo "=== Testing Error: Invalid Provider ==="
curl -s -X POST http://localhost:8000/api/auth/api-keys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"provider":"invalid","api_key":"test"}' | jq

# Expected: Validation error

# ============================================
# CLEANUP (Optional)
# ============================================

# Delete test API key:
# curl -X DELETE http://localhost:8000/api/auth/api-keys/openai \
#   -H "Authorization: Bearer $TOKEN"

# Delete test article:
# curl -X DELETE http://localhost:8000/api/articles/$ARTICLE_ID \
#   -H "Authorization: Bearer $TOKEN"

# Delete test post:
# curl -X DELETE http://localhost:8000/api/posts/$POST_ID \
#   -H "Authorization: Bearer $TOKEN"

EOF

echo ""
echo "=========================================="
echo "Copy the commands above and replace:"
echo "  - TOKEN with your actual token"
echo "  - ARTICLE_ID with actual article ID"
echo "  - POST_ID with actual post ID"
echo "  - API key with your real OpenAI key"
echo "=========================================="
