#!/bin/bash
#
# Comprehensive API Testing - Curl Commands
# Tests all endpoints related to post-edit.html infinite loading issue
#
# Usage: bash CURL_TEST_COMMANDS.sh
#

set -e

API_BASE="http://localhost:8000/api"
POST_ID=23

echo "================================================================================"
echo " Comprehensive API Testing - Post Edit Endpoints"
echo "================================================================================"
echo ""
echo "Target: http://localhost:8000/post-edit.html?post_id=$POST_ID"
echo "Issue: Infinite loading spinner"
echo "Date: $(date)"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test 1: Authentication
echo "================================================================================"
echo " Test 1: Authentication"
echo "================================================================================"
echo ""
echo "POST $API_BASE/auth/login"
echo ""

LOGIN_RESPONSE=$(curl -X POST "$API_BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"testuser@example.com","password":"testpass123"}' \
  -s -w "\n__STATUS__:%{http_code}\n__TIME__:%{time_total}")

STATUS=$(echo "$LOGIN_RESPONSE" | grep "__STATUS__:" | cut -d: -f2)
TIME=$(echo "$LOGIN_RESPONSE" | grep "__TIME__:" | cut -d: -f2)
BODY=$(echo "$LOGIN_RESPONSE" | grep -v "__STATUS__" | grep -v "__TIME__")

if [ "$STATUS" = "200" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Login successful"
else
    echo -e "${RED}❌ FAIL${NC} - Login failed with status $STATUS"
fi
echo "Response Time: ${TIME}s"
echo ""
echo "Response:"
echo "$BODY" | python3 -m json.tool || echo "$BODY"
echo ""

# Extract token
TOKEN=$(echo "$BODY" | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])" 2>/dev/null || echo "")

if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ CRITICAL ERROR${NC} - Could not extract token from login response"
    exit 1
fi

echo "Token: ${TOKEN:0:40}..."
echo ""

# Test 2: Get Post Data (Main endpoint)
echo "================================================================================"
echo " Test 2: Get Post Data (CRITICAL)"
echo "================================================================================"
echo ""
echo "GET $API_BASE/posts/$POST_ID/edit"
echo "Authorization: Bearer $TOKEN"
echo ""

POST_RESPONSE=$(curl -X GET "$API_BASE/posts/$POST_ID/edit" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -s -w "\n__STATUS__:%{http_code}\n__TIME__:%{time_total}")

STATUS=$(echo "$POST_RESPONSE" | grep "__STATUS__:" | cut -d: -f2)
TIME=$(echo "$POST_RESPONSE" | grep "__TIME__:" | cut -d: -f2)
BODY=$(echo "$POST_RESPONSE" | grep -v "__STATUS__" | grep -v "__TIME__")

if [ "$STATUS" = "200" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Post data retrieved successfully"
else
    echo -e "${RED}❌ FAIL${NC} - Failed with status $STATUS"
fi
echo "Response Time: ${TIME}s"
echo ""

# Validate response structure
if [ "$STATUS" = "200" ]; then
    echo "Validating response structure..."

    # Check for required fields
    HAS_ID=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print('id' in d)" 2>/dev/null || echo "False")
    HAS_TITLE=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print('article_title' in d)" 2>/dev/null || echo "False")
    HAS_STATUS=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print('status' in d)" 2>/dev/null || echo "False")
    HAS_TWITTER=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print('twitter_content' in d)" 2>/dev/null || echo "False")
    HAS_LINKEDIN=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print('linkedin_content' in d)" 2>/dev/null || echo "False")
    HAS_THREADS=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print('threads_content' in d)" 2>/dev/null || echo "False")
    HAS_PLATFORMS=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print('platform_statuses' in d)" 2>/dev/null || echo "False")
    IS_ARRAY=$(echo "$BODY" | python3 -c "import sys, json; d=json.load(sys.stdin); print(isinstance(d.get('platform_statuses', []), list))" 2>/dev/null || echo "False")

    echo ""
    [ "$HAS_ID" = "True" ] && echo -e "  ${GREEN}✅${NC} id" || echo -e "  ${RED}❌${NC} id"
    [ "$HAS_TITLE" = "True" ] && echo -e "  ${GREEN}✅${NC} article_title" || echo -e "  ${RED}❌${NC} article_title"
    [ "$HAS_STATUS" = "True" ] && echo -e "  ${GREEN}✅${NC} status" || echo -e "  ${RED}❌${NC} status"
    [ "$HAS_TWITTER" = "True" ] && echo -e "  ${GREEN}✅${NC} twitter_content" || echo -e "  ${RED}❌${NC} twitter_content"
    [ "$HAS_LINKEDIN" = "True" ] && echo -e "  ${GREEN}✅${NC} linkedin_content" || echo -e "  ${RED}❌${NC} linkedin_content"
    [ "$HAS_THREADS" = "True" ] && echo -e "  ${GREEN}✅${NC} threads_content" || echo -e "  ${RED}❌${NC} threads_content"
    [ "$HAS_PLATFORMS" = "True" ] && echo -e "  ${GREEN}✅${NC} platform_statuses (exists)" || echo -e "  ${RED}❌${NC} platform_statuses (exists)"
    [ "$IS_ARRAY" = "True" ] && echo -e "  ${GREEN}✅${NC} platform_statuses (is array)" || echo -e "  ${RED}❌${NC} platform_statuses (is array)"

    echo ""
    echo "Response sample (first 500 chars):"
    echo "$BODY" | head -c 500
    echo "..."
    echo ""
fi

# Test 3: Platform Status
echo "================================================================================"
echo " Test 3: Platform Status"
echo "================================================================================"
echo ""
echo "GET $API_BASE/posts/$POST_ID/platform-status"
echo ""

PLATFORM_RESPONSE=$(curl -X GET "$API_BASE/posts/$POST_ID/platform-status" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -s -w "\n__STATUS__:%{http_code}\n__TIME__:%{time_total}")

STATUS=$(echo "$PLATFORM_RESPONSE" | grep "__STATUS__:" | cut -d: -f2)
TIME=$(echo "$PLATFORM_RESPONSE" | grep "__TIME__:" | cut -d: -f2)
BODY=$(echo "$PLATFORM_RESPONSE" | grep -v "__STATUS__" | grep -v "__TIME__")

if [ "$STATUS" = "200" ]; then
    echo -e "${GREEN}✅ PASS${NC} - Platform status retrieved"
else
    echo -e "${RED}❌ FAIL${NC} - Failed with status $STATUS"
fi
echo "Response Time: ${TIME}s"
echo ""
echo "Response:"
echo "$BODY" | python3 -m json.tool || echo "$BODY"
echo ""

# Test 4: CORS Headers
echo "================================================================================"
echo " Test 4: CORS Headers"
echo "================================================================================"
echo ""
echo "Checking CORS headers on main endpoint..."
echo ""

HEADERS=$(curl -X GET "$API_BASE/posts/$POST_ID/edit" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Origin: http://localhost:8000" \
  -I -s)

CORS_ORIGIN=$(echo "$HEADERS" | grep -i "access-control-allow-origin" | cut -d: -f2 | tr -d '\r\n' | xargs)
CORS_CREDS=$(echo "$HEADERS" | grep -i "access-control-allow-credentials" | cut -d: -f2 | tr -d '\r\n' | xargs)

if [ ! -z "$CORS_ORIGIN" ]; then
    echo -e "${GREEN}✅ PASS${NC} - CORS headers present"
    echo "  Access-Control-Allow-Origin: $CORS_ORIGIN"
    echo "  Access-Control-Allow-Credentials: $CORS_CREDS"
else
    echo -e "${RED}❌ FAIL${NC} - CORS headers missing"
fi
echo ""

# Test 5: Performance Test
echo "================================================================================"
echo " Test 5: Performance Test (10 requests)"
echo "================================================================================"
echo ""
echo "Testing response time consistency..."
echo ""

TOTAL_TIME=0
MAX_TIME=0
MIN_TIME=999

for i in {1..10}; do
    RESPONSE=$(curl -X GET "$API_BASE/posts/$POST_ID/edit" \
      -H "Authorization: Bearer $TOKEN" \
      -s -w "\n__TIME__:%{time_total}\n__STATUS__:%{http_code}" \
      -o /dev/null)

    TIME=$(echo "$RESPONSE" | grep "__TIME__:" | cut -d: -f2)
    STATUS=$(echo "$RESPONSE" | grep "__STATUS__:" | cut -d: -f2)

    if [ "$STATUS" = "200" ]; then
        echo -e "  Request $i: ${GREEN}✅ $STATUS${NC} - ${TIME}s"
    else
        echo -e "  Request $i: ${RED}❌ $STATUS${NC} - ${TIME}s"
    fi

    # Calculate stats (requires bc)
    TOTAL_TIME=$(echo "$TOTAL_TIME + $TIME" | bc 2>/dev/null || echo "0")
    if (( $(echo "$TIME > $MAX_TIME" | bc -l 2>/dev/null || echo "0") )); then
        MAX_TIME=$TIME
    fi
    if (( $(echo "$TIME < $MIN_TIME" | bc -l 2>/dev/null || echo "1") )); then
        MIN_TIME=$TIME
    fi
done

AVG_TIME=$(echo "scale=4; $TOTAL_TIME / 10" | bc 2>/dev/null || echo "N/A")

echo ""
echo "Performance Summary:"
echo "  Average: ${AVG_TIME}s"
echo "  Min: ${MIN_TIME}s"
echo "  Max: ${MAX_TIME}s"
echo ""

# Test 6: Error Scenarios
echo "================================================================================"
echo " Test 6: Error Scenarios"
echo "================================================================================"
echo ""

# Test 6a: Invalid token
echo "Test 6a: Invalid Token"
RESPONSE=$(curl -X GET "$API_BASE/posts/$POST_ID/edit" \
  -H "Authorization: Bearer invalid_token_12345" \
  -s -w "\n__STATUS__:%{http_code}")

STATUS=$(echo "$RESPONSE" | grep "__STATUS__:" | cut -d: -f2)

if [ "$STATUS" = "401" ]; then
    echo -e "  ${GREEN}✅ PASS${NC} - Returns 401 Unauthorized (expected)"
else
    echo -e "  ${RED}❌ FAIL${NC} - Returns $STATUS (expected 401)"
fi
echo ""

# Test 6b: No token
echo "Test 6b: No Authorization Header"
RESPONSE=$(curl -X GET "$API_BASE/posts/$POST_ID/edit" \
  -s -w "\n__STATUS__:%{http_code}")

STATUS=$(echo "$RESPONSE" | grep "__STATUS__:" | cut -d: -f2)

if [ "$STATUS" = "401" ]; then
    echo -e "  ${GREEN}✅ PASS${NC} - Returns 401 Unauthorized (expected)"
else
    echo -e "  ${RED}❌ FAIL${NC} - Returns $STATUS (expected 401)"
fi
echo ""

# Test 6c: Invalid post ID
echo "Test 6c: Invalid Post ID (99999)"
RESPONSE=$(curl -X GET "$API_BASE/posts/99999/edit" \
  -H "Authorization: Bearer $TOKEN" \
  -s -w "\n__STATUS__:%{http_code}")

STATUS=$(echo "$RESPONSE" | grep "__STATUS__:" | cut -d: -f2)

if [ "$STATUS" = "404" ]; then
    echo -e "  ${GREEN}✅ PASS${NC} - Returns 404 Not Found (expected)"
else
    echo -e "  ${RED}❌ FAIL${NC} - Returns $STATUS (expected 404)"
fi
echo ""

# Final Summary
echo "================================================================================"
echo " FINAL SUMMARY"
echo "================================================================================"
echo ""
echo "Success Criteria Checklist:"
echo ""
echo "1. Does GET /api/posts/23/edit return 200 OK?"
echo "   Check Test 2 results above"
echo ""
echo "2. Is response time < 1 second?"
echo "   Check Test 2 and Test 5 results above"
echo ""
echo "3. Does response include all required fields?"
echo "   Check Test 2 validation results above"
echo ""
echo "4. Is platform_statuses an array?"
echo "   Check Test 2 validation results above"
echo ""
echo "5. Are CORS headers present?"
echo "   Check Test 4 results above"
echo ""
echo "6. Does authentication work?"
echo "   Check Test 1 results above"
echo ""
echo "================================================================================"
echo " DIAGNOSIS"
echo "================================================================================"
echo ""
echo "If all tests passed:"
echo "  ✅ API is working correctly"
echo "  ⚠️  Issue is in the FRONTEND"
echo ""
echo "Next steps:"
echo "  1. Open browser DevTools (F12)"
echo "  2. Open http://localhost:8000/post-edit.html?post_id=23"
echo "  3. Check Console tab for JavaScript errors"
echo "  4. Check Network tab to see if API request is made"
echo "  5. Verify Vue.js and Axios are loading from CDN"
echo ""
echo "Alternative test:"
echo "  Open http://localhost:8000/test-api-direct.html"
echo "  This simple test page proves API works in browser"
echo ""
echo "================================================================================"
echo " Test Complete"
echo "================================================================================"
