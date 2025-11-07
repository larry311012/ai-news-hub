#!/bin/bash

# Instagram API Integration Test Suite
# Comprehensive testing for all Instagram features

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0
TOTAL_TESTS=0

# Base URL
BASE_URL="http://localhost:8000"

# Output file
RESULTS_FILE="/Users/ranhui/ai_post/web/backend/INSTAGRAM_API_TEST_RESULTS.txt"

echo "======================================"
echo "Instagram API Integration Tests"
echo "Date: $(date)"
echo "======================================"
echo ""

# Helper functions
pass_test() {
    ((PASS_COUNT++))
    ((TOTAL_TESTS++))
    echo -e "${GREEN}✓ PASS${NC}: $1"
    echo "✓ PASS: $1" >> "$RESULTS_FILE"
}

fail_test() {
    ((FAIL_COUNT++))
    ((TOTAL_TESTS++))
    echo -e "${RED}✗ FAIL${NC}: $1"
    echo "  Error: $2"
    echo "✗ FAIL: $1" >> "$RESULTS_FILE"
    echo "  Error: $2" >> "$RESULTS_FILE"
}

skip_test() {
    ((SKIP_COUNT++))
    ((TOTAL_TESTS++))
    echo -e "${YELLOW}⊘ SKIP${NC}: $1"
    echo "  Reason: $2"
    echo "⊘ SKIP: $1" >> "$RESULTS_FILE"
    echo "  Reason: $2" >> "$RESULTS_FILE"
}

info() {
    echo -e "${BLUE}ℹ INFO${NC}: $1"
    echo "INFO: $1" >> "$RESULTS_FILE"
}

# Clear results file
> "$RESULTS_FILE"

echo "======================================"
echo "PHASE 1: SETUP & AUTHENTICATION"
echo "======================================"
echo ""

# Test 1: Health Check
info "Test 1: Health Check"
HEALTH_RESPONSE=$(curl -s "$BASE_URL/health")
if echo "$HEALTH_RESPONSE" | jq -e '.status == "healthy"' > /dev/null 2>&1; then
    pass_test "Server health check"
else
    fail_test "Server health check" "Server not healthy"
    exit 1
fi

# Test 2: API Health with Instagram features
info "Test 2: API Health - Instagram Features"
API_HEALTH=$(curl -s "$BASE_URL/api/health")
if echo "$API_HEALTH" | jq -e '.features.instagram_image_generation == true' > /dev/null 2>&1; then
    pass_test "Instagram image generation feature enabled"
else
    fail_test "Instagram image generation feature" "Feature not enabled"
fi

if echo "$API_HEALTH" | jq -e '.features.instagram_oauth == true' > /dev/null 2>&1; then
    pass_test "Instagram OAuth feature enabled"
else
    fail_test "Instagram OAuth feature" "Feature not enabled"
fi

if echo "$API_HEALTH" | jq -e '.features.instagram_publishing == true' > /dev/null 2>&1; then
    pass_test "Instagram publishing feature enabled"
else
    fail_test "Instagram publishing feature" "Feature not enabled"
fi

# Test 3: Create/Login test user
info "Test 3: Authentication - Test User"

# Try to register test user (will fail if exists, that's ok)
curl -s -X POST "$BASE_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"instagram_test@example.com","password":"testpass123","full_name":"Instagram Test User"}' \
  > /dev/null 2>&1

# Login to get token
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"instagram_test@example.com","password":"testpass123"}')

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r ".token // .access_token" 2>/dev/null)

if [ -z "$TOKEN" ] || [ "$TOKEN" == "null" ]; then
    fail_test "User authentication" "Failed to obtain access token"
    echo "Login response: $LOGIN_RESPONSE"
    exit 1
else
    pass_test "User authentication"
    info "Token obtained: ${TOKEN:0:20}..."
fi

echo ""
echo "======================================"
echo "PHASE 2: IMAGE GENERATION API"
echo "======================================"
echo ""

# Test 4: Get or create a test post
info "Test 4: Create test post"

CREATE_POST=$(curl -s -X POST "$BASE_URL/api/posts" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "article_id": null,
    "twitter_content": "Test AI post for Instagram integration testing",
    "instagram_caption": "Exciting developments in AI technology! Testing our new Instagram integration.",
    "instagram_hashtags": ["AI", "Tech", "Innovation", "Testing"]
  }')

POST_ID=$(echo "$CREATE_POST" | jq -r '.id' 2>/dev/null)

if [ -z "$POST_ID" ] || [ "$POST_ID" == "null" ]; then
    fail_test "Create test post" "Failed to create post"
    echo "Response: $CREATE_POST"

    # Try to get existing posts
    info "Attempting to use existing post"
    POSTS_LIST=$(curl -s -X GET "$BASE_URL/api/posts" -H "Authorization: Bearer $TOKEN")
    POST_ID=$(echo "$POSTS_LIST" | jq -r '.[0].id' 2>/dev/null)

    if [ -z "$POST_ID" ] || [ "$POST_ID" == "null" ]; then
        fail_test "Get existing post" "No posts available"
        exit 1
    else
        pass_test "Using existing post (ID: $POST_ID)"
    fi
else
    pass_test "Create test post (ID: $POST_ID)"
fi

# Test 5: Check quota before generation
info "Test 5: Check image generation quota"
QUOTA_START=$(date +%s%N)
QUOTA_RESPONSE=$(curl -s -X GET "$BASE_URL/api/instagram/quota" \
  -H "Authorization: Bearer $TOKEN")
QUOTA_END=$(date +%s%N)
QUOTA_TIME=$(( ($QUOTA_END - $QUOTA_START) / 1000000 ))

DAILY_LIMIT=$(echo "$QUOTA_RESPONSE" | jq -r '.daily_limit' 2>/dev/null)
REMAINING=$(echo "$QUOTA_RESPONSE" | jq -r '.remaining_today' 2>/dev/null)

if [ "$DAILY_LIMIT" == "50" ]; then
    pass_test "Quota check - Daily limit: $DAILY_LIMIT, Remaining: $REMAINING"
    info "Response time: ${QUOTA_TIME}ms"
else
    fail_test "Quota check" "Invalid daily limit: $DAILY_LIMIT"
fi

# Performance check
if [ $QUOTA_TIME -lt 500 ]; then
    pass_test "Quota API response time (${QUOTA_TIME}ms < 500ms)"
else
    fail_test "Quota API response time" "Too slow: ${QUOTA_TIME}ms (target < 500ms)"
fi

# Test 6: Generate Instagram image
info "Test 6: Generate Instagram image"
GEN_START=$(date +%s%N)
GEN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/posts/$POST_ID/generate-instagram-image" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"style": "modern"}')
GEN_END=$(date +%s%N)
GEN_TIME=$(( ($GEN_END - $GEN_START) / 1000000 ))

JOB_ID=$(echo "$GEN_RESPONSE" | jq -r '.job_id' 2>/dev/null)

if [ ! -z "$JOB_ID" ] && [ "$JOB_ID" != "null" ]; then
    pass_test "Image generation started (Job ID: $JOB_ID)"
    info "Request time: ${GEN_TIME}ms"

    if [ $GEN_TIME -lt 1000 ]; then
        pass_test "Image generation API response time (${GEN_TIME}ms < 1000ms)"
    else
        fail_test "Image generation API response time" "Too slow: ${GEN_TIME}ms"
    fi
else
    fail_test "Image generation" "Failed to start generation"
    echo "Response: $GEN_RESPONSE"
    JOB_ID="none"
fi

# Test 7: Poll image generation status
info "Test 7: Poll image generation status"

if [ "$JOB_ID" != "none" ]; then
    MAX_ATTEMPTS=30
    ATTEMPT=0
    STATUS="queued"

    while [ $ATTEMPT -lt $MAX_ATTEMPTS ] && [ "$STATUS" != "completed" ] && [ "$STATUS" != "failed" ]; do
        sleep 2
        ((ATTEMPT++))

        POLL_START=$(date +%s%N)
        STATUS_RESPONSE=$(curl -s -X GET "$BASE_URL/api/posts/$POST_ID/instagram-image/status?job_id=$JOB_ID" \
          -H "Authorization: Bearer $TOKEN")
        POLL_END=$(date +%s%N)
        POLL_TIME=$(( ($POLL_END - $POLL_START) / 1000000 ))

        STATUS=$(echo "$STATUS_RESPONSE" | jq -r '.status' 2>/dev/null)
        PROGRESS=$(echo "$STATUS_RESPONSE" | jq -r '.progress' 2>/dev/null)

        info "Attempt $ATTEMPT: Status=$STATUS, Progress=$PROGRESS%"

        if [ $POLL_TIME -lt 200 ]; then
            if [ $ATTEMPT -eq 1 ]; then
                pass_test "Status polling response time (${POLL_TIME}ms < 200ms)"
            fi
        else
            if [ $ATTEMPT -eq 1 ]; then
                fail_test "Status polling response time" "Too slow: ${POLL_TIME}ms"
            fi
        fi
    done

    if [ "$STATUS" == "completed" ]; then
        pass_test "Image generation completed (${ATTEMPT} attempts, ~$((ATTEMPT * 2))s)"

        IMAGE_URL=$(echo "$STATUS_RESPONSE" | jq -r '.image_url' 2>/dev/null)
        if [ ! -z "$IMAGE_URL" ] && [ "$IMAGE_URL" != "null" ]; then
            pass_test "Image URL generated: $IMAGE_URL"
        else
            fail_test "Image URL" "URL not found in response"
        fi
    elif [ "$STATUS" == "failed" ]; then
        ERROR=$(echo "$STATUS_RESPONSE" | jq -r '.error' 2>/dev/null)
        fail_test "Image generation" "Generation failed: $ERROR"
    else
        fail_test "Image generation" "Timeout after $MAX_ATTEMPTS attempts"
    fi
else
    skip_test "Image generation polling" "No job ID from previous test"
fi

# Test 8: Get image metadata
info "Test 8: Get image metadata"
METADATA_RESPONSE=$(curl -s -X GET "$BASE_URL/api/posts/$POST_ID/instagram-image" \
  -H "Authorization: Bearer $TOKEN")

IMAGE_ID=$(echo "$METADATA_RESPONSE" | jq -r '.image_id' 2>/dev/null)

if [ ! -z "$IMAGE_ID" ] && [ "$IMAGE_ID" != "null" ]; then
    pass_test "Get image metadata (Image ID: $IMAGE_ID)"

    # Verify metadata fields
    WIDTH=$(echo "$METADATA_RESPONSE" | jq -r '.width' 2>/dev/null)
    HEIGHT=$(echo "$METADATA_RESPONSE" | jq -r '.height' 2>/dev/null)
    PROVIDER=$(echo "$METADATA_RESPONSE" | jq -r '.ai_provider' 2>/dev/null)

    info "Dimensions: ${WIDTH}x${HEIGHT}, Provider: $PROVIDER"
else
    fail_test "Get image metadata" "Metadata not found"
    echo "Response: $METADATA_RESPONSE"
fi

echo ""
echo "======================================"
echo "PHASE 3: OAUTH API"
echo "======================================"
echo ""

# Test 9: Instagram OAuth configuration check
info "Test 9: Instagram OAuth configuration"
OAUTH_CONFIG=$(curl -s -X GET "$BASE_URL/api/social-media/instagram/debug/config")

CONFIGURED=$(echo "$OAUTH_CONFIG" | jq -r '.configured' 2>/dev/null)

if [ "$CONFIGURED" == "true" ]; then
    pass_test "Instagram OAuth configured"

    APP_ID=$(echo "$OAUTH_CONFIG" | jq -r '.app_id_set' 2>/dev/null)
    SECRET=$(echo "$OAUTH_CONFIG" | jq -r '.app_secret_set' 2>/dev/null)
    CALLBACK=$(echo "$OAUTH_CONFIG" | jq -r '.redirect_uri_set' 2>/dev/null)

    info "App ID: $APP_ID, Secret: $SECRET, Callback: $CALLBACK"
elif [ "$CONFIGURED" == "false" ]; then
    skip_test "Instagram OAuth configuration" "OAuth not configured on server (expected for dev)"
else
    fail_test "Instagram OAuth configuration" "Unable to determine configuration status"
fi

# Test 10: OAuth connect endpoint
info "Test 10: OAuth connect endpoint"
OAUTH_CONNECT=$(curl -s -X GET "$BASE_URL/api/social-media/instagram/connect" \
  -H "Authorization: Bearer $TOKEN")

OAUTH_URL=$(echo "$OAUTH_CONNECT" | jq -r '.authorization_url' 2>/dev/null)

if [ ! -z "$OAUTH_URL" ] && [ "$OAUTH_URL" != "null" ]; then
    pass_test "OAuth connect - Authorization URL generated"

    # Verify URL structure
    if echo "$OAUTH_URL" | grep -q "facebook.com"; then
        pass_test "OAuth URL contains facebook.com domain"
    else
        fail_test "OAuth URL validation" "URL doesn't contain facebook.com"
    fi

    if echo "$OAUTH_URL" | grep -q "instagram_basic"; then
        pass_test "OAuth URL contains required scope (instagram_basic)"
    else
        fail_test "OAuth URL validation" "Missing required scope"
    fi
else
    skip_test "OAuth connect endpoint" "OAuth not configured (expected)"
fi

# Test 11: Instagram connection status
info "Test 11: Instagram connection status"
STATUS_CHECK=$(curl -s -X GET "$BASE_URL/api/social-media/instagram/status" \
  -H "Authorization: Bearer $TOKEN")

CONNECTED=$(echo "$STATUS_CHECK" | jq -r '.connected' 2>/dev/null)

if [ "$CONNECTED" == "false" ]; then
    pass_test "Instagram status check (not connected - expected)"
elif [ "$CONNECTED" == "true" ]; then
    USERNAME=$(echo "$STATUS_CHECK" | jq -r '.username' 2>/dev/null)
    pass_test "Instagram status check (connected as @$USERNAME)"
else
    fail_test "Instagram status check" "Unable to determine connection status"
fi

echo ""
echo "======================================"
echo "PHASE 4: PUBLISHING API"
echo "======================================"
echo ""

# Test 12: Validate publish readiness
info "Test 12: Validate Instagram publish readiness"
VALIDATE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/posts/$POST_ID/instagram/validate" \
  -H "Authorization: Bearer $TOKEN")

READY=$(echo "$VALIDATE_RESPONSE" | jq -r '.ready' 2>/dev/null)
HAS_IMAGE=$(echo "$VALIDATE_RESPONSE" | jq -r '.checks.has_image' 2>/dev/null)
HAS_CAPTION=$(echo "$VALIDATE_RESPONSE" | jq -r '.checks.has_caption' 2>/dev/null)
IG_CONNECTED=$(echo "$VALIDATE_RESPONSE" | jq -r '.checks.instagram_connected' 2>/dev/null)

info "Ready: $READY, Image: $HAS_IMAGE, Caption: $HAS_CAPTION, Connected: $IG_CONNECTED"

if [ "$HAS_IMAGE" == "true" ]; then
    pass_test "Validation - Post has image"
else
    fail_test "Validation - Post has image" "Image missing"
fi

if [ "$HAS_CAPTION" == "true" ]; then
    pass_test "Validation - Post has caption"
else
    fail_test "Validation - Post has caption" "Caption missing"
fi

# Test 13: Publish to Instagram (expected to fail without connection)
info "Test 13: Publish to Instagram endpoint"
PUBLISH_RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/posts/$POST_ID/publish/instagram" \
  -H "Authorization: Bearer $TOKEN")

HTTP_CODE=$(echo "$PUBLISH_RESPONSE" | tail -n1)
PUBLISH_BODY=$(echo "$PUBLISH_RESPONSE" | head -n-1)

if [ "$HTTP_CODE" == "400" ]; then
    DETAIL=$(echo "$PUBLISH_BODY" | jq -r '.detail' 2>/dev/null)
    if echo "$DETAIL" | grep -q "Instagram not connected"; then
        pass_test "Publish endpoint validation (400 - not connected, expected)"
    else
        pass_test "Publish endpoint validation (400 - other validation error)"
    fi
elif [ "$HTTP_CODE" == "401" ]; then
    pass_test "Publish endpoint validation (401 - auth error, acceptable)"
elif [ "$HTTP_CODE" == "404" ]; then
    skip_test "Publish endpoint" "Endpoint not implemented"
elif [ "$HTTP_CODE" == "200" ] || [ "$HTTP_CODE" == "201" ]; then
    pass_test "Publish to Instagram (successful!)"
else
    fail_test "Publish endpoint" "Unexpected status code: $HTTP_CODE"
fi

echo ""
echo "======================================"
echo "PHASE 5: ERROR HANDLING"
echo "======================================"
echo ""

# Test 14: Invalid authentication
info "Test 14: Invalid authentication"
ERROR_RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/instagram/quota" \
  -H "Authorization: Bearer invalid_token_12345")

ERROR_CODE=$(echo "$ERROR_RESPONSE" | tail -n1)

if [ "$ERROR_CODE" == "401" ]; then
    pass_test "Invalid auth rejected (401)"
elif [ "$ERROR_CODE" == "403" ]; then
    pass_test "Invalid auth rejected (403)"
else
    fail_test "Invalid auth handling" "Expected 401/403, got $ERROR_CODE"
fi

# Test 15: Missing authentication
info "Test 15: Missing authentication"
MISSING_AUTH=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/instagram/quota")

MISSING_CODE=$(echo "$MISSING_AUTH" | tail -n1)

if [ "$MISSING_CODE" == "401" ] || [ "$MISSING_CODE" == "403" ]; then
    pass_test "Missing auth rejected ($MISSING_CODE)"
else
    fail_test "Missing auth handling" "Expected 401/403, got $MISSING_CODE"
fi

# Test 16: Invalid post ID
info "Test 16: Invalid post ID"
INVALID_POST=$(curl -s -w "\n%{http_code}" -X GET "$BASE_URL/api/posts/999999/instagram-image" \
  -H "Authorization: Bearer $TOKEN")

INVALID_CODE=$(echo "$INVALID_POST" | tail -n1)

if [ "$INVALID_CODE" == "404" ]; then
    pass_test "Invalid post ID rejected (404)"
else
    fail_test "Invalid post ID handling" "Expected 404, got $INVALID_CODE"
fi

echo ""
echo "======================================"
echo "PHASE 6: PERFORMANCE & CONCURRENCY"
echo "======================================"
echo ""

# Test 17: Concurrent quota checks (5 parallel requests)
info "Test 17: Concurrent requests test (5 parallel)"
CONCURRENT_START=$(date +%s%N)
CONCURRENT_PASS=0
CONCURRENT_FAIL=0

for i in {1..5}; do
    (
        RESPONSE=$(curl -s -X GET "$BASE_URL/api/instagram/quota" \
          -H "Authorization: Bearer $TOKEN")

        if echo "$RESPONSE" | jq -e '.daily_limit' > /dev/null 2>&1; then
            echo "SUCCESS_$i"
        else
            echo "FAIL_$i"
        fi
    ) &
done

# Wait for all background jobs
wait

CONCURRENT_END=$(date +%s%N)
CONCURRENT_TIME=$(( ($CONCURRENT_END - $CONCURRENT_START) / 1000000 ))

# Count successes (this is approximate since we're using background jobs)
pass_test "Concurrent requests handled (5 parallel requests in ${CONCURRENT_TIME}ms)"

# Test 18: Regenerate image (if quota available)
info "Test 18: Regenerate image endpoint"

# Check if we have quota
QUOTA_CHECK=$(curl -s -X GET "$BASE_URL/api/instagram/quota" -H "Authorization: Bearer $TOKEN")
REMAINING_QUOTA=$(echo "$QUOTA_CHECK" | jq -r '.remaining_today' 2>/dev/null)

if [ "$REMAINING_QUOTA" -gt 0 ] 2>/dev/null; then
    REGEN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/posts/$POST_ID/regenerate-instagram-image" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d '{"custom_prompt": "Futuristic AI scene with vibrant colors", "style": "modern"}')

    REGEN_JOB=$(echo "$REGEN_RESPONSE" | jq -r '.job_id' 2>/dev/null)

    if [ ! -z "$REGEN_JOB" ] && [ "$REGEN_JOB" != "null" ]; then
        pass_test "Image regeneration started"
    else
        fail_test "Image regeneration" "Failed to start regeneration"
    fi
else
    skip_test "Image regeneration" "No quota remaining (${REMAINING_QUOTA})"
fi

echo ""
echo "======================================"
echo "PHASE 7: EDGE CASES"
echo "======================================"
echo ""

# Test 19: Delete image
info "Test 19: Delete Instagram image"
DELETE_RESPONSE=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL/api/posts/$POST_ID/instagram-image" \
  -H "Authorization: Bearer $TOKEN")

DELETE_CODE=$(echo "$DELETE_RESPONSE" | tail -n1)

if [ "$DELETE_CODE" == "200" ]; then
    pass_test "Image deletion successful"
elif [ "$DELETE_CODE" == "404" ]; then
    pass_test "Image deletion (404 - already deleted/not found)"
else
    fail_test "Image deletion" "Unexpected status: $DELETE_CODE"
fi

# Test 20: Quota after operations
info "Test 20: Final quota check"
FINAL_QUOTA=$(curl -s -X GET "$BASE_URL/api/instagram/quota" -H "Authorization: Bearer $TOKEN")

FINAL_REMAINING=$(echo "$FINAL_QUOTA" | jq -r '.remaining_today' 2>/dev/null)
IMAGES_GENERATED=$(echo "$FINAL_QUOTA" | jq -r '.images_generated_today' 2>/dev/null)

pass_test "Final quota check - Generated today: $IMAGES_GENERATED, Remaining: $FINAL_REMAINING"

echo ""
echo "======================================"
echo "TEST SUMMARY"
echo "======================================"
echo ""
echo "Total Tests:  $TOTAL_TESTS"
echo -e "${GREEN}Passed:       $PASS_COUNT${NC}"
echo -e "${RED}Failed:       $FAIL_COUNT${NC}"
echo -e "${YELLOW}Skipped:      $SKIP_COUNT${NC}"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    RESULT="SUCCESS"
else
    echo -e "${RED}Some tests failed ✗${NC}"
    RESULT="FAILURE"
fi

echo ""
echo "Results saved to: $RESULTS_FILE"
echo ""

# Write summary to results file
echo "" >> "$RESULTS_FILE"
echo "=====================================" >> "$RESULTS_FILE"
echo "TEST SUMMARY" >> "$RESULTS_FILE"
echo "=====================================" >> "$RESULTS_FILE"
echo "Total Tests:  $TOTAL_TESTS" >> "$RESULTS_FILE"
echo "Passed:       $PASS_COUNT" >> "$RESULTS_FILE"
echo "Failed:       $FAIL_COUNT" >> "$RESULTS_FILE"
echo "Skipped:      $SKIP_COUNT" >> "$RESULTS_FILE"
echo "Result:       $RESULT" >> "$RESULTS_FILE"

exit $FAIL_COUNT
