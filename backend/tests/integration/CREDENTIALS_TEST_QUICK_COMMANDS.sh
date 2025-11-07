#!/bin/bash

# Quick Commands for Testing OAuth Credentials Endpoint
# After backend-architect fixes the GET credentials bug

set -e

API_BASE="http://localhost:8000/api"
COOKIES="/tmp/quick_test_cookies_$$.txt"

# Cleanup on exit
trap "rm -f $COOKIES" EXIT

echo "=========================================="
echo "OAuth Credentials Test - Quick Commands"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# 1. Setup: Get CSRF and login
echo -e "${BLUE}1. Setting up authentication${NC}"
CSRF=$(curl -s -c $COOKIES -b $COOKIES "$API_BASE/csrf-token" | jq -r '.csrf_token')
echo "CSRF Token: ${CSRF:0:20}..."

# Try to login with existing test user, or register
TOKEN=$(curl -s -c $COOKIES -b $COOKIES -X POST "$API_BASE/auth/login" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -d '{"email":"test@example.com","password":"testpassword123"}' 2>/dev/null | jq -r '.token // empty')

if [ -z "$TOKEN" ]; then
    echo "Creating new test user..."
    curl -s -c $COOKIES -b $COOKIES -X POST "$API_BASE/auth/register" \
      -H "Content-Type: application/json" \
      -H "X-CSRF-Token: $CSRF" \
      -d '{"email":"test@example.com","password":"testpassword123","full_name":"Test User"}' > /dev/null

    CSRF=$(curl -s -c $COOKIES -b $COOKIES "$API_BASE/csrf-token" | jq -r '.csrf_token')
    TOKEN=$(curl -s -c $COOKIES -b $COOKIES -X POST "$API_BASE/auth/login" \
      -H "Content-Type: application/json" \
      -H "X-CSRF-Token: $CSRF" \
      -d '{"email":"test@example.com","password":"testpassword123"}' | jq -r '.token')
fi

echo "Auth Token: ${TOKEN:0:20}..."
echo ""

# 2. Test unauthenticated access
echo -e "${BLUE}2. Test unauthenticated access (should fail)${NC}"
echo "Command:"
echo "  curl -X POST \"$API_BASE/oauth-setup/twitter/test\""
echo ""
curl -s -X POST "$API_BASE/oauth-setup/twitter/test" | jq '.'
echo ""

# 3. Check credential status (no credentials)
echo -e "${BLUE}3. Check credential status (should show not configured)${NC}"
echo "Command:"
echo "  curl -X GET \"$API_BASE/oauth-setup/twitter/credentials\" -H \"Authorization: Bearer \$TOKEN\""
echo ""
curl -s -X GET "$API_BASE/oauth-setup/twitter/credentials" \
  -H "Authorization: Bearer $TOKEN" | jq '.' 2>&1 || echo "⚠ Bug: Returns 500 instead of {configured: false}"
echo ""

# 4. Test without credentials
echo -e "${BLUE}4. Test credentials without saving (should fail with clear message)${NC}"
echo "Command:"
echo "  curl -X POST \"$API_BASE/oauth-setup/twitter/test\" -H \"Authorization: Bearer \$TOKEN\""
echo ""
curl -s -X POST "$API_BASE/oauth-setup/twitter/test" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
echo ""

# 5. Save credentials
echo -e "${BLUE}5. Save test credentials${NC}"
CSRF=$(curl -s -c $COOKIES -b $COOKIES "$API_BASE/csrf-token" | jq -r '.csrf_token')
echo "Command:"
echo "  curl -X POST \"$API_BASE/oauth-setup/twitter/credentials\" \\"
echo "    -H \"Authorization: Bearer \$TOKEN\" \\"
echo "    -H \"X-CSRF-Token: \$CSRF\" \\"
echo "    -d '{\"api_key\":\"test_key\",\"api_secret\":\"test_secret\",\"callback_url\":\"...\"}'"
echo ""
SAVE_RESPONSE=$(curl -s -c $COOKIES -b $COOKIES \
  -X POST "$API_BASE/oauth-setup/twitter/credentials" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "X-CSRF-Token: $CSRF" \
  -d '{"api_key":"test_api_key_12345","api_secret":"test_api_secret_67890","callback_url":"http://localhost:8000/api/oauth-setup/twitter/callback"}')
echo "$SAVE_RESPONSE" | jq '.'
echo ""

# 6. Test saved credentials
echo -e "${BLUE}6. Test saved credentials (should succeed)${NC}"
echo "Command:"
echo "  curl -X POST \"$API_BASE/oauth-setup/twitter/test\" -H \"Authorization: Bearer \$TOKEN\""
echo ""
TEST_RESPONSE=$(curl -s -X POST "$API_BASE/oauth-setup/twitter/test" \
  -H "Authorization: Bearer $TOKEN")
echo "$TEST_RESPONSE" | jq '.'
echo ""

# Verify key fields
SUCCESS=$(echo "$TEST_RESPONSE" | jq -r '.success // false')
MESSAGE=$(echo "$TEST_RESPONSE" | jq -r '.message // ""')
PLATFORM=$(echo "$TEST_RESPONSE" | jq -r '.platform // ""')
TESTED_AT=$(echo "$TEST_RESPONSE" | jq -r '.tested_at // ""')

echo -e "${GREEN}Verification:${NC}"
echo "  - success: $SUCCESS (expected: true)"
echo "  - message: $MESSAGE"
echo "  - platform: $PLATFORM (expected: twitter)"
echo "  - tested_at: $TESTED_AT (should be ISO 8601)"
echo ""

# 7. Verify credentials persisted
echo -e "${BLUE}7. Verify credentials persisted with masking${NC}"
echo "Command:"
echo "  curl -X GET \"$API_BASE/oauth-setup/twitter/credentials\" -H \"Authorization: Bearer \$TOKEN\""
echo ""
VERIFY_RESPONSE=$(curl -s -X GET "$API_BASE/oauth-setup/twitter/credentials" \
  -H "Authorization: Bearer $TOKEN")
echo "$VERIFY_RESPONSE" | jq '.'
echo ""

CONFIGURED=$(echo "$VERIFY_RESPONSE" | jq -r '.configured // false')
MASKED_KEY=$(echo "$VERIFY_RESPONSE" | jq -r '.masked_credentials.api_key // ""')

echo -e "${GREEN}Verification:${NC}"
echo "  - configured: $CONFIGURED (expected: true)"
echo "  - masked_api_key: $MASKED_KEY (should contain ••)"
echo ""

# 8. Test invalid platform
echo -e "${BLUE}8. Test invalid platform (should return clear error)${NC}"
echo "Command:"
echo "  curl -X POST \"$API_BASE/oauth-setup/invalidplatform/test\" -H \"Authorization: Bearer \$TOKEN\""
echo ""
curl -s -X POST "$API_BASE/oauth-setup/invalidplatform/test" \
  -H "Authorization: Bearer $TOKEN" | jq '.'
echo ""

echo "=========================================="
echo "Test Complete"
echo "=========================================="
echo ""
echo "IMPORTANT: If step 3 returns 500 error instead of {configured: false},"
echo "the backend-architect needs to fix the GET credentials endpoint bug."
echo ""
echo "See full report: CREDENTIALS_TEST_ENDPOINT_VERIFICATION_REPORT.md"
