#!/bin/bash

# Comprehensive API Testing Script for Post Generation Debugging
# This script tests the entire post generation flow end-to-end

set -e

BASE_URL="http://localhost:8000"
API_URL="${BASE_URL}/api"
DB_PATH="/Users/ranhui/ai_post/web/backend/ai_news.db"

echo "========================================="
echo "COMPREHENSIVE API TEST FOR POST GENERATION"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo -e "${YELLOW}[TEST 1] Health Check${NC}"
HEALTH=$(curl -s ${BASE_URL}/health)
if echo $HEALTH | grep -q "healthy"; then
    echo -e "${GREEN}✓ Backend is healthy${NC}"
    echo "Response: $HEALTH"
else
    echo -e "${RED}✗ Backend health check failed${NC}"
    echo "Response: $HEALTH"
    exit 1
fi
echo ""

# Test 2: Get User Session Token
echo -e "${YELLOW}[TEST 2] Get User Session Token (User ID: 6)${NC}"
TOKEN=$(sqlite3 ${DB_PATH} "SELECT token FROM sessions WHERE user_id = 6 ORDER BY created_at DESC LIMIT 1")
if [ -z "$TOKEN" ]; then
    echo -e "${RED}✗ No session token found for user 6${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Token found: ${TOKEN:0:20}...${NC}"
fi
echo ""

# Test 3: Check Token Expiry
echo -e "${YELLOW}[TEST 3] Check Token Expiry${NC}"
EXPIRES=$(sqlite3 ${DB_PATH} "SELECT expires_at FROM sessions WHERE token = '${TOKEN}'")
echo "Token expires at: $EXPIRES"
CURRENT_TIME=$(date -u '+%Y-%m-%d %H:%M:%S')
echo "Current time: $CURRENT_TIME"
echo ""

# Test 4: Check User API Keys
echo -e "${YELLOW}[TEST 4] Check User API Keys${NC}"
API_KEYS=$(sqlite3 ${DB_PATH} "SELECT provider FROM user_api_keys WHERE user_id = 6")
if [ -z "$API_KEYS" ]; then
    echo -e "${RED}✗ No API keys found for user 6${NC}"
    echo "This will cause generation to fail!"
else
    echo -e "${GREEN}✓ API keys found:${NC}"
    echo "$API_KEYS"
fi
echo ""

# Test 5: Test Auth with Token
echo -e "${YELLOW}[TEST 5] Test Authentication${NC}"
AUTH_TEST=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer ${TOKEN}" ${API_URL}/posts)
HTTP_CODE=$(echo "$AUTH_TEST" | tail -1)
RESPONSE=$(echo "$AUTH_TEST" | head -n -1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Authentication successful (HTTP $HTTP_CODE)${NC}"
else
    echo -e "${RED}✗ Authentication failed (HTTP $HTTP_CODE)${NC}"
    echo "Response: $RESPONSE"
fi
echo ""

# Test 6: Get Available Articles
echo -e "${YELLOW}[TEST 6] Get Available Articles${NC}"
ARTICLES=$(sqlite3 ${DB_PATH} "SELECT id, title FROM articles LIMIT 3")
if [ -z "$ARTICLES" ]; then
    echo -e "${RED}✗ No articles found in database${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Articles found:${NC}"
    echo "$ARTICLES" | head -5
fi
ARTICLE_ID=$(echo "$ARTICLES" | head -1 | cut -d'|' -f1)
echo "Will use article ID: $ARTICLE_ID"
echo ""

# Test 7: Start Post Generation
echo -e "${YELLOW}[TEST 7] Start Post Generation${NC}"
GEN_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST ${API_URL}/posts/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${TOKEN}" \
  -d "{\"article_ids\": [${ARTICLE_ID}], \"platforms\": [\"twitter\"]}")

GEN_HTTP_CODE=$(echo "$GEN_RESPONSE" | tail -1)
GEN_BODY=$(echo "$GEN_RESPONSE" | head -n -1)

if [ "$GEN_HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Generation started successfully (HTTP $GEN_HTTP_CODE)${NC}"
    echo "Response: $GEN_BODY"
    POST_ID=$(echo "$GEN_BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('post_id', ''))" 2>/dev/null || echo "")

    if [ -z "$POST_ID" ]; then
        echo -e "${RED}✗ Could not extract post_id from response${NC}"
        exit 1
    fi

    echo "Post ID: $POST_ID"
else
    echo -e "${RED}✗ Generation failed (HTTP $GEN_HTTP_CODE)${NC}"
    echo "Response: $GEN_BODY"

    # Check specific error
    if echo "$GEN_BODY" | grep -q "API key"; then
        echo -e "${RED}ERROR: API key issue detected${NC}"
        echo "Checking API key decryption..."

        # Try to get more details
        ENCRYPTED_KEY=$(sqlite3 ${DB_PATH} "SELECT encrypted_key FROM user_api_keys WHERE user_id = 6 AND provider = 'openai' LIMIT 1")
        if [ -z "$ENCRYPTED_KEY" ]; then
            echo "No OpenAI key in database"
        else
            echo "Encrypted key exists (length: ${#ENCRYPTED_KEY})"
        fi
    fi

    exit 1
fi
echo ""

# Test 8: Poll Generation Status
echo -e "${YELLOW}[TEST 8] Poll Generation Status${NC}"
for i in {1..10}; do
    echo "Poll attempt $i..."
    STATUS_RESPONSE=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer ${TOKEN}" \
      ${API_URL}/posts/generation/${POST_ID}/status)

    STATUS_HTTP_CODE=$(echo "$STATUS_RESPONSE" | tail -1)
    STATUS_BODY=$(echo "$STATUS_RESPONSE" | head -n -1)

    if [ "$STATUS_HTTP_CODE" != "200" ]; then
        echo -e "${RED}✗ Status check failed (HTTP $STATUS_HTTP_CODE)${NC}"
        echo "Response: $STATUS_BODY"
        break
    fi

    echo "$STATUS_BODY" | python3 -m json.tool 2>/dev/null || echo "$STATUS_BODY"

    STATUS=$(echo "$STATUS_BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))" 2>/dev/null || echo "")
    PROGRESS=$(echo "$STATUS_BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('progress', 0))" 2>/dev/null || echo "0")

    echo "Status: $STATUS, Progress: $PROGRESS%"

    if [ "$STATUS" = "completed" ]; then
        echo -e "${GREEN}✓ Generation completed!${NC}"
        break
    elif [ "$STATUS" = "failed" ]; then
        echo -e "${RED}✗ Generation failed${NC}"
        ERROR=$(echo "$STATUS_BODY" | python3 -c "import sys, json; print(json.load(sys.stdin).get('error', 'Unknown error'))" 2>/dev/null || echo "Unknown error")
        echo "Error: $ERROR"
        break
    fi

    sleep 1
done
echo ""

# Test 9: Check Final Database State
echo -e "${YELLOW}[TEST 9] Check Final Database State${NC}"
echo "Post record:"
sqlite3 ${DB_PATH} "SELECT id, status, twitter_content IS NOT NULL as has_twitter, error_message FROM posts WHERE id = ${POST_ID}"
echo ""
echo "Generated content preview:"
sqlite3 ${DB_PATH} "SELECT SUBSTR(twitter_content, 1, 100) FROM posts WHERE id = ${POST_ID}"
echo ""

echo "========================================="
echo "TEST COMPLETE"
echo "========================================="
