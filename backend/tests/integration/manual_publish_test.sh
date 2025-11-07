#!/bin/bash
#
# Manual Publishing Test Script
#
# This script tests the complete publishing flow to verify:
# 1. Posts can be created
# 2. Database commits work correctly
# 3. Post status updates properly
# 4. Error messages persist to database
#
# Usage: ./manual_publish_test.sh [BASE_URL] [AUTH_TOKEN]
#

set -e

BASE_URL="${1:-http://localhost:8000}"
AUTH_TOKEN="${2:-}"

if [ -z "$AUTH_TOKEN" ]; then
    echo "ERROR: Auth token required"
    echo "Usage: $0 [BASE_URL] AUTH_TOKEN"
    echo ""
    echo "To get auth token:"
    echo "  1. Login via frontend or API"
    echo "  2. Get token from localStorage or /api/auth/login response"
    exit 1
fi

echo "========================================="
echo "Publishing Flow Manual Test"
echo "========================================="
echo "Base URL: $BASE_URL"
echo ""

# Helper function to make authenticated requests
api_call() {
    local method=$1
    local endpoint=$2
    local data=$3

    if [ -n "$data" ]; then
        curl -s -X "$method" "$BASE_URL$endpoint" \
            -H "Authorization: Bearer $AUTH_TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -s -X "$method" "$BASE_URL$endpoint" \
            -H "Authorization: Bearer $AUTH_TOKEN"
    fi
}

# Step 1: Create a test article
echo "Step 1: Creating test article..."
ARTICLE_RESPONSE=$(api_call POST "/api/articles" '{
    "title": "Test Article for Publishing",
    "link": "https://example.com/test",
    "summary": "This is a test article to verify publishing works",
    "source": "Manual Test",
    "published": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'"
}')

ARTICLE_ID=$(echo "$ARTICLE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")

if [ -z "$ARTICLE_ID" ]; then
    echo "ERROR: Failed to create article"
    echo "Response: $ARTICLE_RESPONSE"
    exit 1
fi

echo "✓ Article created: ID=$ARTICLE_ID"
echo ""

# Step 2: Generate post (with API key check)
echo "Step 2: Generating post content..."
GENERATE_RESPONSE=$(api_call POST "/api/posts/generate" "{
    \"article_ids\": [$ARTICLE_ID],
    \"platforms\": [\"twitter\"]
}" 2>&1)

# Check if API key error
if echo "$GENERATE_RESPONSE" | grep -q "API key"; then
    echo "⚠ No API key configured - skipping generation"
    echo "Creating post manually instead..."

    # Create post directly
    POST_RESPONSE=$(api_call POST "/api/posts" '{
        "article_title": "Test Article for Publishing",
        "twitter_content": "This is a test tweet to verify publishing works! #testing",
        "platforms": ["twitter"],
        "status": "ready"
    }')

    POST_ID=$(echo "$POST_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['id'])" 2>/dev/null || echo "")
else
    POST_ID=$(echo "$GENERATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['post_id'])" 2>/dev/null || echo "")

    if [ -n "$POST_ID" ]; then
        echo "✓ Post generation started: ID=$POST_ID"
        echo "Waiting for generation to complete..."
        sleep 3
    fi
fi

if [ -z "$POST_ID" ]; then
    echo "ERROR: Failed to create post"
    echo "Response: $GENERATE_RESPONSE"
    exit 1
fi

echo "✓ Post created: ID=$POST_ID"
echo ""

# Step 3: Get post status BEFORE publishing
echo "Step 3: Checking post status BEFORE publishing..."
PRE_PUBLISH_STATUS=$(api_call GET "/api/posts/$POST_ID")
PRE_STATUS=$(echo "$PRE_PUBLISH_STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "unknown")

echo "Pre-publish status: $PRE_STATUS"
echo ""

# Step 4: Check platform connection status
echo "Step 4: Checking Twitter connection status..."
PLATFORM_STATUS=$(api_call GET "/api/posts/$POST_ID/platform-status")
echo "$PLATFORM_STATUS" | python3 -m json.tool 2>/dev/null || echo "$PLATFORM_STATUS"

TWITTER_CONNECTED=$(echo "$PLATFORM_STATUS" | python3 -c "import sys, json; data=json.load(sys.stdin); twitter=[p for p in data if p['platform']=='twitter']; print(twitter[0]['connected'] if twitter else False)" 2>/dev/null || echo "false")

if [ "$TWITTER_CONNECTED" != "True" ]; then
    echo ""
    echo "⚠ Twitter not connected - publishing will fail (expected for test)"
    echo "This is OK - we're testing the error handling flow"
fi
echo ""

# Step 5: Attempt to publish
echo "Step 5: Publishing post to Twitter..."
PUBLISH_RESPONSE=$(api_call POST "/api/posts/publish" "{
    \"post_id\": $POST_ID,
    \"platforms\": [\"twitter\"]
}")

echo "Publish response:"
echo "$PUBLISH_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$PUBLISH_RESPONSE"
echo ""

# Step 6: Get post status AFTER publishing
echo "Step 6: Checking post status AFTER publishing..."
sleep 1  # Give database a moment to commit
POST_PUBLISH_STATUS=$(api_call GET "/api/posts/$POST_ID")
POST_STATUS=$(echo "$POST_PUBLISH_STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "unknown")
ERROR_MSG=$(echo "$POST_PUBLISH_STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('error_message', 'None'))" 2>/dev/null || echo "")
PUBLISHED_AT=$(echo "$POST_PUBLISH_STATUS" | python3 -c "import sys, json; print(json.load(sys.stdin).get('published_at', 'None'))" 2>/dev/null || echo "")

echo "Post-publish status: $POST_STATUS"
echo "Error message: $ERROR_MSG"
echo "Published at: $PUBLISHED_AT"
echo ""

# Step 7: Verify database commit worked
echo "Step 7: Verifying database commit..."
echo "========================================="

if [ "$PRE_STATUS" = "$POST_STATUS" ]; then
    echo "❌ FAIL: Post status did NOT change"
    echo "   Before: $PRE_STATUS"
    echo "   After:  $POST_STATUS"
    echo ""
    echo "This indicates a database commit issue!"
    exit 1
fi

echo "✓ PASS: Post status changed"
echo "   Before: $PRE_STATUS"
echo "   After:  $POST_STATUS"
echo ""

if [ "$POST_STATUS" = "failed" ] && [ -n "$ERROR_MSG" ] && [ "$ERROR_MSG" != "None" ]; then
    echo "✓ PASS: Error message persisted to database"
    echo "   Message: $ERROR_MSG"
elif [ "$POST_STATUS" = "published" ]; then
    echo "✓ PASS: Post published successfully"
    if [ -n "$PUBLISHED_AT" ] && [ "$PUBLISHED_AT" != "None" ]; then
        echo "✓ PASS: Published timestamp set"
        echo "   Time: $PUBLISHED_AT"
    else
        echo "⚠ WARNING: Published timestamp not set"
    fi
else
    echo "⚠ Unexpected status: $POST_STATUS"
fi

echo ""
echo "========================================="
echo "TEST COMPLETE"
echo "========================================="
echo ""
echo "Summary:"
echo "  - Post ID: $POST_ID"
echo "  - Status changed: $PRE_STATUS → $POST_STATUS"
echo "  - Database commits: WORKING ✓"
echo ""
echo "If status changed, database commits are working correctly!"
echo ""
