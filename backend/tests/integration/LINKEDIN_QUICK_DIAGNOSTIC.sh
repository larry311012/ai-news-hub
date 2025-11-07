#!/bin/bash

##############################################################################
# LinkedIn Quick Diagnostic Script
#
# Run this to quickly check the state of LinkedIn integration for a user
##############################################################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

BASE_URL="http://localhost:8000"
USER_ID="${1:-5}"
TOKEN="${2:-test_token_AE3CA021B17D2C7529ED936F522C7352}"
DB_PATH="/Users/ranhui/ai_post/web/backend/ai_news.db"

echo -e "${BLUE}=== LinkedIn Integration Diagnostic ===${NC}"
echo "User ID: $USER_ID"
echo "Database: $DB_PATH"
echo ""

# Check 1: Database State
echo -e "${YELLOW}[1] Database State${NC}"
echo ""
echo "user_oauth_credentials (Setup System):"
sqlite3 "$DB_PATH" << SQL
SELECT
    printf('  Platform: %s', platform),
    printf('  OAuth: %s', oauth_version),
    printf('  Active: %s', is_active),
    printf('  Validated: %s', is_validated),
    printf('  Status: %s', COALESCE(validation_status, 'NULL')),
    printf('  Has Client ID: %s', CASE WHEN encrypted_client_id IS NOT NULL THEN 'YES' ELSE 'NO' END),
    printf('  Has Client Secret: %s', CASE WHEN encrypted_client_secret IS NOT NULL THEN 'YES' ELSE 'NO' END)
FROM user_oauth_credentials
WHERE user_id = $USER_ID AND platform = 'linkedin';
SQL

CRED_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM user_oauth_credentials WHERE user_id = $USER_ID AND platform = 'linkedin';")

if [ "$CRED_COUNT" -eq 0 ]; then
    echo -e "  ${RED}✗ No credentials found${NC}"
else
    echo -e "  ${GREEN}✓ Credentials exist${NC}"
fi

echo ""
echo "social_media_connections (Connection System):"
sqlite3 "$DB_PATH" << SQL
SELECT
    printf('  Platform: %s', platform),
    printf('  Active: %s', is_active),
    printf('  Username: %s', COALESCE(platform_username, 'NULL')),
    printf('  Has Access Token: %s', CASE WHEN encrypted_access_token IS NOT NULL THEN 'YES' ELSE 'NO' END),
    printf('  Expires: %s', COALESCE(expires_at, 'NULL'))
FROM social_media_connections
WHERE user_id = $USER_ID AND platform = 'linkedin';
SQL

CONN_COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM social_media_connections WHERE user_id = $USER_ID AND platform = 'linkedin';")

if [ "$CONN_COUNT" -eq 0 ]; then
    echo -e "  ${RED}✗ No connection found${NC}"
else
    echo -e "  ${GREEN}✓ Connection exists${NC}"
fi

echo ""

# Check 2: Setup Page Status
echo -e "${YELLOW}[2] Setup Page Status${NC}"
SETUP_RESPONSE=$(curl -s -X GET "$BASE_URL/api/oauth-setup/linkedin/credentials" \
  -H "Authorization: Bearer $TOKEN" 2>&1 || echo '{"error":"request_failed"}')

echo "Response: $SETUP_RESPONSE"

if echo "$SETUP_RESPONSE" | jq -e '.configured == true' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Setup page shows CONFIGURED${NC}"
else
    echo -e "${RED}✗ Setup page shows NOT CONFIGURED${NC}"
fi
echo ""

# Check 3: Post Page Status
echo -e "${YELLOW}[3] Post Page Status${NC}"
CONNECTIONS_RESPONSE=$(curl -s -X GET "$BASE_URL/api/social-media/connections" \
  -H "Authorization: Bearer $TOKEN")

echo "Response: $CONNECTIONS_RESPONSE"

LINKEDIN_FOUND=$(echo "$CONNECTIONS_RESPONSE" | jq -r '.[] | select(.platform == "linkedin") | .platform' 2>/dev/null || echo "")

if [ -n "$LINKEDIN_FOUND" ]; then
    echo -e "${GREEN}✓ Post page sees LinkedIn connection${NC}"
else
    echo -e "${RED}✗ Post page does NOT see LinkedIn connection${NC}"
fi
echo ""

# Check 4: LinkedIn Status Endpoint
echo -e "${YELLOW}[4] LinkedIn Status Endpoint${NC}"
STATUS_RESPONSE=$(curl -s -X GET "$BASE_URL/api/social-media/linkedin/status" \
  -H "Authorization: Bearer $TOKEN")

echo "Response: $STATUS_RESPONSE"

CONNECTED=$(echo "$STATUS_RESPONSE" | jq -r '.connected' 2>/dev/null || echo "false")

if [ "$CONNECTED" == "true" ]; then
    echo -e "${GREEN}✓ Status shows CONNECTED${NC}"
else
    echo -e "${RED}✗ Status shows NOT CONNECTED${NC}"
fi
echo ""

# Check 5: OAuth Connect Endpoint
echo -e "${YELLOW}[5] OAuth Connect Endpoint${NC}"
CONNECT_RESPONSE=$(curl -s -X GET "$BASE_URL/api/social-media/linkedin/connect?return_url=http://localhost/test" \
  -H "Authorization: Bearer $TOKEN" 2>&1 || echo '{"error":"request_failed"}')

echo "Response: $CONNECT_RESPONSE"

if echo "$CONNECT_RESPONSE" | jq -e '.authorization_url' > /dev/null 2>&1; then
    echo -e "${GREEN}✓ OAuth connect works${NC}"
else
    echo -e "${RED}✗ OAuth connect fails${NC}"
fi
echo ""

# Summary
echo -e "${BLUE}=== Summary ===${NC}"

if [ "$CRED_COUNT" -gt 0 ] && [ "$CONN_COUNT" -gt 0 ]; then
    echo -e "${GREEN}Status: Fully Connected${NC}"
    echo "The user has both credentials AND an active OAuth connection."
elif [ "$CRED_COUNT" -gt 0 ] && [ "$CONN_COUNT" -eq 0 ]; then
    echo -e "${YELLOW}Status: Partially Set Up (BUG!)${NC}"
    echo "The user has credentials saved but NO OAuth connection."
    echo "This is the bug: Setup page shows 'Active' but post page shows 'Not Connected'"
elif [ "$CRED_COUNT" -eq 0 ]; then
    echo -e "${RED}Status: Not Set Up${NC}"
    echo "The user has not saved LinkedIn credentials yet."
else
    echo -e "${YELLOW}Status: Unknown${NC}"
fi

echo ""
echo -e "${BLUE}Expected User Experience:${NC}"
if [ "$CRED_COUNT" -gt 0 ] && [ "$CONN_COUNT" -eq 0 ]; then
    echo "1. Setup page: Shows 'Active' ✓"
    echo "2. Post page: Shows 'Connect' button ✓ (correct, needs OAuth)"
    echo "3. Click Connect: Should start OAuth flow ✗ (BROKEN)"
    echo ""
    echo -e "${RED}Problem: OAuth connect endpoint doesn't use user's credentials${NC}"
else
    echo "User needs to complete setup and OAuth flow."
fi
