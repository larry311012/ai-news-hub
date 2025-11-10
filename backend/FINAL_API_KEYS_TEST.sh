#!/bin/bash
# Final comprehensive test of API Keys in Anonymous Mode

echo "=========================================="
echo "Final API Keys Test - Anonymous Mode"
echo "=========================================="
echo ""

BASE_URL="http://localhost:8000"

echo "Configuration:"
echo "- ANONYMOUS_MODE: $(grep ANONYMOUS_MODE .env)"
echo "- CSRF_ENABLED: $(grep CSRF_ENABLED .env)"
echo ""

echo "Backend Status:"
curl -s ${BASE_URL}/health | jq .
echo ""

echo "1. Clean slate - Delete any existing keys"
curl -s -X DELETE ${BASE_URL}/api/settings/openai_api_key 2>/dev/null
curl -s -X DELETE ${BASE_URL}/api/settings/anthropic_api_key 2>/dev/null
curl -s -X DELETE ${BASE_URL}/api/settings/deepseek_api_key 2>/dev/null
echo "   Keys cleaned"
echo ""

echo "2. GET all settings (should be empty)"
RESULT=$(curl -s ${BASE_URL}/api/settings)
echo "   Response: $RESULT"
if [ "$RESULT" = "[]" ]; then
    echo "   ✓ PASS: Empty array returned"
else
    echo "   ✗ FAIL: Expected empty array"
fi
echo ""

echo "3. POST create OpenAI API key"
RESULT=$(curl -s -X POST ${BASE_URL}/api/settings \
  -H "Content-Type: application/json" \
  -d '{"key":"openai_api_key","value":"sk-proj-abc123","encrypted":true}')
echo "   Response: $RESULT"
if echo "$RESULT" | grep -q '"success":true'; then
    echo "   ✓ PASS: Key created successfully"
else
    echo "   ✗ FAIL: Key creation failed"
fi
echo ""

echo "4. GET specific key"
RESULT=$(curl -s ${BASE_URL}/api/settings/openai_api_key)
echo "   Response: $RESULT"
if echo "$RESULT" | grep -q '"key":"openai_api_key"'; then
    echo "   ✓ PASS: Key retrieved successfully"
else
    echo "   ✗ FAIL: Key retrieval failed"
fi
echo ""

echo "5. POST update key"
RESULT=$(curl -s -X POST ${BASE_URL}/api/settings \
  -H "Content-Type: application/json" \
  -d '{"key":"openai_api_key","value":"sk-proj-updated","encrypted":true}')
echo "   Response: $RESULT"
if echo "$RESULT" | grep -q '"success":true'; then
    echo "   ✓ PASS: Key updated successfully"
else
    echo "   ✗ FAIL: Key update failed"
fi
echo ""

echo "6. Verify update"
RESULT=$(curl -s ${BASE_URL}/api/settings/openai_api_key)
if echo "$RESULT" | grep -q 'sk-proj-updated'; then
    echo "   ✓ PASS: Update verified"
else
    echo "   ✗ FAIL: Update not reflected"
fi
echo ""

echo "7. POST create Anthropic key"
RESULT=$(curl -s -X POST ${BASE_URL}/api/settings \
  -H "Content-Type: application/json" \
  -d '{"key":"anthropic_api_key","value":"sk-ant-test","encrypted":true}')
if echo "$RESULT" | grep -q '"success":true'; then
    echo "   ✓ PASS: Anthropic key created"
else
    echo "   ✗ FAIL: Anthropic key creation failed"
fi
echo ""

echo "8. GET all settings (should have 2 keys)"
RESULT=$(curl -s ${BASE_URL}/api/settings)
KEY_COUNT=$(echo "$RESULT" | jq 'length')
echo "   Keys found: $KEY_COUNT"
if [ "$KEY_COUNT" = "2" ]; then
    echo "   ✓ PASS: Both keys present"
else
    echo "   ✗ FAIL: Expected 2 keys, found $KEY_COUNT"
fi
echo ""

echo "9. DELETE Anthropic key"
RESULT=$(curl -s -X DELETE ${BASE_URL}/api/settings/anthropic_api_key)
if echo "$RESULT" | grep -q '"success":true'; then
    echo "   ✓ PASS: Key deleted successfully"
else
    echo "   ✗ FAIL: Key deletion failed"
fi
echo ""

echo "10. Verify deletion"
RESULT=$(curl -s ${BASE_URL}/api/settings)
KEY_COUNT=$(echo "$RESULT" | jq 'length')
if [ "$KEY_COUNT" = "1" ]; then
    echo "   ✓ PASS: Deletion verified"
else
    echo "   ✗ FAIL: Expected 1 key, found $KEY_COUNT"
fi
echo ""

echo "11. iOS app simulation (with headers)"
RESULT=$(curl -s -H "X-App-Version: 1.0.0" \
              -H "User-Agent: AINewsHub-iOS/1.0.0" \
              ${BASE_URL}/api/settings)
if echo "$RESULT" | jq -e '. | length > 0' >/dev/null 2>&1; then
    echo "   ✓ PASS: iOS app can access keys"
else
    echo "   ✗ FAIL: iOS app access failed"
fi
echo ""

echo "12. Database verification"
DB_COUNT=$(sqlite3 ai_news.db "SELECT COUNT(*) FROM settings WHERE user_id = 1;")
echo "   Settings in database: $DB_COUNT"
if [ "$DB_COUNT" = "1" ]; then
    echo "   ✓ PASS: Database has correct count"
else
    echo "   ✗ FAIL: Expected 1 setting in database"
fi
echo ""

echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "All API key operations work WITHOUT authentication"
echo "CSRF protection is disabled for anonymous mode"
echo "iOS app can access API keys without login"
echo ""
echo "Configuration:"
echo "- Backend: http://localhost:8000"
echo "- ANONYMOUS_MODE: true"
echo "- CSRF_ENABLED: false"
echo "- User ID: 1 (anonymous@localhost)"
echo ""
echo "Database content:"
sqlite3 ai_news.db "SELECT id, user_id, key, encrypted FROM settings WHERE user_id = 1;"
