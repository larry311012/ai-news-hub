#!/bin/bash
# Comprehensive Twitter OAuth API Tests
# Version: 2.1.0

BASE_URL="http://localhost:8000"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'
BLUE='\033[0;34m'

PASSED=0
FAILED=0
TOTAL=0

print_header() {
    echo -e "\n${BLUE}========================================================================${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}========================================================================${NC}"
}

test_endpoint() {
    local NAME="$1"
    local METHOD="$2"
    local ENDPOINT="$3"
    local TOKEN="$4"
    local DATA="$5"
    local EXPECTED_CODE="$6"

    ((TOTAL++))

    if [ -n "$TOKEN" ]; then
        if [ -n "$DATA" ]; then
            RESPONSE=$(curl -s -w "\n%{http_code}" -X "$METHOD" "${BASE_URL}${ENDPOINT}" \
                -H "Authorization: Bearer $TOKEN" \
                -H "Content-Type: application/json" \
                -d "$DATA" 2>&1)
        else
            RESPONSE=$(curl -s -w "\n%{http_code}" -X "$METHOD" "${BASE_URL}${ENDPOINT}" \
                -H "Authorization: Bearer $TOKEN" 2>&1)
        fi
    else
        if [ -n "$DATA" ]; then
            RESPONSE=$(curl -s -w "\n%{http_code}" -X "$METHOD" "${BASE_URL}${ENDPOINT}" \
                -H "Content-Type: application/json" \
                -d "$DATA" 2>&1)
        else
            RESPONSE=$(curl -s -w "\n%{http_code}" -X "$METHOD" "${BASE_URL}${ENDPOINT}" 2>&1)
        fi
    fi

    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | sed '$d')

    if [ "$HTTP_CODE" = "$EXPECTED_CODE" ]; then
        echo -e "  ${GREEN}✓ PASS${NC} [$HTTP_CODE] $METHOD $ENDPOINT - $NAME"
        ((PASSED++))
    else
        echo -e "  ${RED}✗ FAIL${NC} [$HTTP_CODE] $METHOD $ENDPOINT - $NAME"
        echo -e "     Expected: $EXPECTED_CODE, Got: $HTTP_CODE"
        echo -e "     Response: $(echo "$BODY" | head -c 100)"
        ((FAILED++))
    fi
}

# Main execution
print_header "TWITTER OAUTH API TESTING - Version 2.1.0"
echo "  Base URL: $BASE_URL"
echo "  Date: $(date '+%Y-%m-%d %H:%M:%S')"

# Health check
echo -e "\n  Checking server health..."
HEALTH=$(curl -s "${BASE_URL}/health")
if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "  ${GREEN}✓ Server is healthy${NC}"
else
    echo -e "  ${RED}✗ Server is not responding${NC}"
    exit 1
fi

# Get test user token
echo -e "\n  Setting up test user..."
LOGIN_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"TestPass123!"}')

USER_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token // empty')

if [ -z "$USER_TOKEN" ]; then
    echo -e "  ${YELLOW}⚠ Login failed, trying registration...${NC}"
    REG_RESPONSE=$(curl -s -X POST "${BASE_URL}/api/auth/register" \
        -H "Content-Type: application/json" \
        -d '{"email":"test@example.com","password":"TestPass123!"}')
    USER_TOKEN=$(echo "$REG_RESPONSE" | jq -r '.access_token // empty')
fi

if [ -z "$USER_TOKEN" ]; then
    echo -e "  ${RED}✗ Failed to get user token${NC}"
    exit 1
fi

echo -e "  ${GREEN}✓ Test user authenticated${NC}"

# Run tests
print_header "TEST 1: OAuth Setup Endpoints (New in v2.1.0)"

test_endpoint \
    "Get callback URL (no auth)" \
    "GET" "/api/oauth-setup/twitter/callback-url" \
    "" "" "200"

test_endpoint \
    "Save credentials (no auth - should fail)" \
    "POST" "/api/oauth-setup/twitter/credentials" \
    "" '{"api_key":"test","api_secret":"test"}' "401"

test_endpoint \
    "Save credentials (with auth)" \
    "POST" "/api/oauth-setup/twitter/credentials" \
    "$USER_TOKEN" '{"api_key":"test_key_abc","api_secret":"test_secret_xyz","callback_url":"http://localhost:8000/callback"}' "200"

test_endpoint \
    "Get credential status" \
    "GET" "/api/oauth-setup/twitter/credentials" \
    "$USER_TOKEN" "" "200"

test_endpoint \
    "Invalid platform (should fail)" \
    "POST" "/api/oauth-setup/invalid/credentials" \
    "$USER_TOKEN" '{"api_key":"test"}' "400"

test_endpoint \
    "Empty credentials (should fail)" \
    "POST" "/api/oauth-setup/twitter/credentials" \
    "$USER_TOKEN" '{"api_key":"","api_secret":""}' "400"

test_endpoint \
    "Test credentials" \
    "POST" "/api/oauth-setup/twitter/test" \
    "$USER_TOKEN" "" "200"

test_endpoint \
    "Delete credentials" \
    "DELETE" "/api/oauth-setup/twitter/credentials" \
    "$USER_TOKEN" "" "200"

print_header "TEST 2: Per-User Twitter OAuth Endpoints"

# Delete credentials first
curl -s -X DELETE "${BASE_URL}/api/oauth-setup/twitter/credentials" \
    -H "Authorization: Bearer $USER_TOKEN" > /dev/null

test_endpoint \
    "Status without credentials" \
    "GET" "/api/social-media/twitter/status" \
    "$USER_TOKEN" "" "200"

test_endpoint \
    "Connect without credentials (should fail 428)" \
    "GET" "/api/social-media/twitter/connect" \
    "$USER_TOKEN" "" "428"

# Save credentials
curl -s -X POST "${BASE_URL}/api/oauth-setup/twitter/credentials" \
    -H "Authorization: Bearer $USER_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"api_key":"test_key","api_secret":"test_secret","callback_url":"http://localhost:8000/callback"}' > /dev/null

test_endpoint \
    "Status with credentials" \
    "GET" "/api/social-media/twitter/status" \
    "$USER_TOKEN" "" "200"

print_header "TEST 3: Legacy OAuth Endpoints (Backward Compatibility)"

test_endpoint \
    "Legacy status endpoint" \
    "GET" "/api/social-media/twitter-oauth1/status" \
    "$USER_TOKEN" "" "200"

print_header "TEST 4: Security Validation"

# Save test credentials with known values
curl -s -X POST "${BASE_URL}/api/oauth-setup/twitter/credentials" \
    -H "Authorization: Bearer $USER_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"api_key":"FULL_SECRET_KEY_12345","api_secret":"FULL_SECRET_VALUE_67890","callback_url":"http://localhost:8000/callback"}' > /dev/null

# Check if credentials are masked
CRED_RESPONSE=$(curl -s -X GET "${BASE_URL}/api/oauth-setup/twitter/credentials" \
    -H "Authorization: Bearer $USER_TOKEN")

((TOTAL++))
if echo "$CRED_RESPONSE" | grep -q "FULL_SECRET_KEY_12345"; then
    echo -e "  ${RED}✗ FAIL${NC} Security - Full credentials exposed!"
    ((FAILED++))
elif echo "$CRED_RESPONSE" | grep -q "•"; then
    echo -e "  ${GREEN}✓ PASS${NC} Security - Credentials properly masked"
    ((PASSED++))
else
    echo -e "  ${YELLOW}⚠ WARN${NC} Security - Unable to verify masking"
    ((FAILED++))
fi

print_header "TEST 5: Performance Benchmarks"

echo -e "\n  Response Time Benchmarks (5 iterations each):\n"

run_perf_test() {
    local METHOD=$1
    local ENDPOINT=$2
    local TOKEN=$3

    local TOTAL_TIME=0
    local MAX_TIME=0
    local MIN_TIME=9999

    for i in {1..5}; do
        local START=$(date +%s.%N)
        if [ -n "$TOKEN" ]; then
            curl -s -X "$METHOD" "${BASE_URL}${ENDPOINT}" \
                -H "Authorization: Bearer $TOKEN" > /dev/null
        else
            curl -s -X "$METHOD" "${BASE_URL}${ENDPOINT}" > /dev/null
        fi
        local END=$(date +%s.%N)
        local ELAPSED=$(echo "$END - $START" | bc)

        TOTAL_TIME=$(echo "$TOTAL_TIME + $ELAPSED" | bc)

        if (( $(echo "$ELAPSED > $MAX_TIME" | bc -l) )); then
            MAX_TIME=$ELAPSED
        fi
        if (( $(echo "$ELAPSED < $MIN_TIME" | bc -l) )); then
            MIN_TIME=$ELAPSED
        fi
    done

    local AVG=$(echo "scale=3; $TOTAL_TIME / 5" | bc)
    local AVG_MS=$(echo "scale=1; $AVG * 1000" | bc)
    local MAX_MS=$(echo "scale=1; $MAX_TIME * 1000" | bc)

    local RATING="GOOD"
    if (( $(echo "$AVG_MS < 200" | bc -l) )); then
        RATING="${GREEN}EXCELLENT${NC}"
    elif (( $(echo "$AVG_MS > 500" | bc -l) )); then
        RATING="${RED}SLOW${NC}"
    fi

    printf "  %-6s %-50s %6.1fms avg, %6.1fms max [%b]\n" "$METHOD" "$ENDPOINT" "$AVG_MS" "$MAX_MS" "$RATING"
}

run_perf_test "GET" "/api/oauth-setup/twitter/callback-url" ""
run_perf_test "GET" "/api/oauth-setup/twitter/credentials" "$USER_TOKEN"
run_perf_test "GET" "/api/social-media/twitter/status" "$USER_TOKEN"
run_perf_test "GET" "/api/social-media/twitter-oauth1/status" "$USER_TOKEN"

print_header "SUMMARY"

echo -e "\n  Total Tests:  $TOTAL"
echo -e "  ${GREEN}Passed:       $PASSED${NC}"
echo -e "  ${RED}Failed:       $FAILED${NC}"

PASS_RATE=$(echo "scale=1; $PASSED * 100 / $TOTAL" | bc)
echo -e "  Pass Rate:    ${PASS_RATE}%"

echo -e "\n${BLUE}========================================================================${NC}"
if [ $FAILED -eq 0 ]; then
    echo -e "  ${GREEN}RESULT: ALL TESTS PASSED ✓${NC}"
else
    echo -e "  ${RED}RESULT: $FAILED TESTS FAILED ✗${NC}"
fi
echo -e "${BLUE}========================================================================${NC}\n"

exit $FAILED
