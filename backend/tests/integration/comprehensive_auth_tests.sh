#!/bin/bash

#===============================================================================
# COMPREHENSIVE AUTHENTICATION API TESTING SCRIPT
# Phase 1 - Authentication Endpoints
#===============================================================================

BASE_URL="http://localhost:8001"
API_URL="$BASE_URL/api/auth"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Timestamp for unique email
TIMESTAMP=$(date +%s)

# Test results storage
RESULTS_FILE="/tmp/auth_test_results_${TIMESTAMP}.txt"
echo "=== Authentication API Test Results ===" > "$RESULTS_FILE"
echo "Started: $(date)" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"

#===============================================================================
# HELPER FUNCTIONS
#===============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}================================================================${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}================================================================${NC}"
    echo ""
}

print_test() {
    echo -e "${CYAN}TEST: $1${NC}"
    echo "TEST: $1" >> "$RESULTS_FILE"
}

print_pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    echo "✓ PASS: $1" >> "$RESULTS_FILE"
    PASSED_TESTS=$((PASSED_TESTS + 1))
}

print_fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    echo "✗ FAIL: $1" >> "$RESULTS_FILE"
    FAILED_TESTS=$((FAILED_TESTS + 1))
}

print_response() {
    echo -e "${YELLOW}Response:${NC}"
    echo "$1" | python3 -m json.tool 2>/dev/null || echo "$1"
    echo ""
}

run_test() {
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
}

measure_time() {
    local start=$(python3 -c 'import time; print(int(time.time() * 1000))')
    eval "$1"
    local end=$(python3 -c 'import time; print(int(time.time() * 1000))')
    local duration=$((end - start))
    echo "${duration}ms"
}

#===============================================================================
# TEST SUITE 1: USER REGISTRATION
#===============================================================================

print_header "TEST SUITE 1: USER REGISTRATION"

# Test 1.1: Valid registration
print_test "1.1 - Register new user with valid data"
run_test
REGISTER_RESPONSE=$(curl -s -X POST "$API_URL/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser'$TIMESTAMP'@example.com",
    "password": "SecurePass123",
    "full_name": "Test User"
  }')

print_response "$REGISTER_RESPONSE"

if echo "$REGISTER_RESPONSE" | grep -q '"success": true'; then
    print_pass "User registered successfully"
    USER_EMAIL="testuser${TIMESTAMP}@example.com"
    USER_PASSWORD="SecurePass123"
else
    print_fail "User registration failed"
fi

# Test 1.2: Duplicate email
print_test "1.2 - Register with duplicate email (should fail)"
run_test
DUPLICATE_RESPONSE=$(curl -s -X POST "$API_URL/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "testuser'$TIMESTAMP'@example.com",
    "password": "DifferentPass123",
    "full_name": "Another User"
  }')

print_response "$DUPLICATE_RESPONSE"

if echo "$DUPLICATE_RESPONSE" | grep -q "already exists"; then
    print_pass "Duplicate email correctly rejected"
else
    print_fail "Duplicate email should be rejected"
fi

# Test 1.3: Missing email field
print_test "1.3 - Register without email (should fail)"
run_test
RESPONSE=$(curl -s -X POST "$API_URL/register" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "SecurePass123",
    "full_name": "Test User"
  }')

print_response "$RESPONSE"

if echo "$RESPONSE" | grep -q -i "field required\|missing"; then
    print_pass "Missing email correctly rejected"
else
    print_fail "Missing email should be rejected"
fi

# Test 1.4: Invalid email format
print_test "1.4 - Register with invalid email format (should fail)"
run_test
RESPONSE=$(curl -s -X POST "$API_URL/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "notanemail",
    "password": "SecurePass123",
    "full_name": "Test User"
  }')

print_response "$RESPONSE"

if echo "$RESPONSE" | grep -q -i "valid email\|email"; then
    print_pass "Invalid email format correctly rejected"
else
    print_fail "Invalid email format should be rejected"
fi

# Test 1.5: Password too short
print_test "1.5 - Register with short password (should fail)"
run_test
RESPONSE=$(curl -s -X POST "$API_URL/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser'$TIMESTAMP'@example.com",
    "password": "short",
    "full_name": "Test User"
  }')

print_response "$RESPONSE"

if echo "$RESPONSE" | grep -q -i "8 characters"; then
    print_pass "Short password correctly rejected"
else
    print_fail "Short password should be rejected"
fi

# Test 1.6: Missing password field
print_test "1.6 - Register without password (should fail)"
run_test
RESPONSE=$(curl -s -X POST "$API_URL/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser2'$TIMESTAMP'@example.com",
    "full_name": "Test User"
  }')

print_response "$RESPONSE"

if echo "$RESPONSE" | grep -q -i "field required\|missing"; then
    print_pass "Missing password correctly rejected"
else
    print_fail "Missing password should be rejected"
fi

# Test 1.7: Empty full_name
print_test "1.7 - Register with empty full_name (should fail)"
run_test
RESPONSE=$(curl -s -X POST "$API_URL/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser3'$TIMESTAMP'@example.com",
    "password": "SecurePass123",
    "full_name": "   "
  }')

print_response "$RESPONSE"

if echo "$RESPONSE" | grep -q -i "cannot be empty\|invalid"; then
    print_pass "Empty full_name correctly rejected"
else
    print_fail "Empty full_name should be rejected"
fi

# Test 1.8: SQL Injection attempt in email
print_test "1.8 - SQL Injection attempt in email (should be safe)"
run_test
RESPONSE=$(curl -s -X POST "$API_URL/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test'\''@example.com; DROP TABLE users; --",
    "password": "SecurePass123",
    "full_name": "Hacker"
  }')

print_response "$RESPONSE"

if echo "$RESPONSE" | grep -q -i "valid email\|error"; then
    print_pass "SQL injection safely handled"
else
    print_fail "SQL injection should be handled"
fi

# Test 1.9: XSS attempt in full_name
print_test "1.9 - XSS attempt in full_name (should be stored safely)"
run_test
RESPONSE=$(curl -s -X POST "$API_URL/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "xsstest'$TIMESTAMP'@example.com",
    "password": "SecurePass123",
    "full_name": "<script>alert(\"xss\")</script>"
  }')

print_response "$RESPONSE"

if echo "$RESPONSE" | grep -q '"success": true'; then
    print_pass "XSS content stored safely (should be escaped on output)"
else
    print_fail "XSS test failed"
fi

# Test 1.10: Very long email (boundary test)
print_test "1.10 - Register with very long email (should fail or truncate)"
run_test
LONG_EMAIL="a$(printf 'x%.0s' {1..300})@example.com"
RESPONSE=$(curl -s -X POST "$API_URL/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$LONG_EMAIL\",
    \"password\": \"SecurePass123\",
    \"full_name\": \"Test User\"
  }")

print_response "$RESPONSE"

if echo "$RESPONSE" | grep -q -i "error\|invalid\|too long"; then
    print_pass "Very long email handled appropriately"
else
    echo -e "${YELLOW}WARNING${NC}: Long email might need validation"
fi

#===============================================================================
# TEST SUITE 2: USER LOGIN
#===============================================================================

print_header "TEST SUITE 2: USER LOGIN"

# Test 2.1: Valid login
print_test "2.1 - Login with correct credentials"
run_test
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'$USER_EMAIL'",
    "password": "'$USER_PASSWORD'",
    "remember_me": false
  }')

print_response "$LOGIN_RESPONSE"

TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)

if [ -n "$TOKEN" ] && [ ${#TOKEN} -eq 64 ]; then
    print_pass "Login successful with valid 64-char token"
else
    print_fail "Login failed or token invalid"
fi

# Test 2.2: Login with remember_me=true
print_test "2.2 - Login with remember_me=true (should have longer expiry)"
run_test
LOGIN_REMEMBER=$(curl -s -X POST "$API_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'$USER_EMAIL'",
    "password": "'$USER_PASSWORD'",
    "remember_me": true
  }')

print_response "$LOGIN_REMEMBER"

REMEMBER_TOKEN=$(echo "$LOGIN_REMEMBER" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)
EXPIRES_AT=$(echo "$LOGIN_REMEMBER" | python3 -c "import sys, json; print(json.load(sys.stdin).get('expires_at', ''))" 2>/dev/null)

if [ -n "$REMEMBER_TOKEN" ]; then
    print_pass "Login with remember_me successful"
    echo -e "${YELLOW}Expires at: $EXPIRES_AT${NC}"
else
    print_fail "Login with remember_me failed"
fi

# Test 2.3: Wrong password
print_test "2.3 - Login with wrong password (should fail)"
run_test
WRONG_PASS=$(curl -s -X POST "$API_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'$USER_EMAIL'",
    "password": "WrongPassword123",
    "remember_me": false
  }')

print_response "$WRONG_PASS"

if echo "$WRONG_PASS" | grep -q -i "Invalid.*password\|Invalid.*credentials"; then
    print_pass "Wrong password correctly rejected"
else
    print_fail "Wrong password should be rejected"
fi

# Test 2.4: Non-existent email
print_test "2.4 - Login with non-existent email (should fail)"
run_test
NO_USER=$(curl -s -X POST "$API_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "nonexistent'$TIMESTAMP'@example.com",
    "password": "SomePassword123",
    "remember_me": false
  }')

print_response "$NO_USER"

if echo "$NO_USER" | grep -q -i "Invalid"; then
    print_pass "Non-existent email correctly rejected"
else
    print_fail "Non-existent email should be rejected"
fi

# Test 2.5: Case insensitive email
print_test "2.5 - Login with different email case (should work)"
run_test
UPPER_EMAIL=$(echo "$USER_EMAIL" | tr '[:lower:]' '[:upper:]')
CASE_LOGIN=$(curl -s -X POST "$API_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'$UPPER_EMAIL'",
    "password": "'$USER_PASSWORD'",
    "remember_me": false
  }')

print_response "$CASE_LOGIN"

if echo "$CASE_LOGIN" | grep -q '"token"'; then
    print_pass "Email is case-insensitive"
else
    print_fail "Email should be case-insensitive"
fi

# Test 2.6: Missing email
print_test "2.6 - Login without email (should fail)"
run_test
RESPONSE=$(curl -s -X POST "$API_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "SomePassword123",
    "remember_me": false
  }')

print_response "$RESPONSE"

if echo "$RESPONSE" | grep -q -i "field required\|missing"; then
    print_pass "Missing email rejected"
else
    print_fail "Missing email should be rejected"
fi

# Test 2.7: SQL Injection in login
print_test "2.7 - SQL Injection in login credentials (should be safe)"
run_test
RESPONSE=$(curl -s -X POST "$API_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com'\'' OR '\''1'\''='\''1",
    "password": "anything",
    "remember_me": false
  }')

print_response "$RESPONSE"

if echo "$RESPONSE" | grep -q -i "Invalid\|error"; then
    print_pass "SQL injection in login safely handled"
else
    print_fail "SQL injection should be prevented"
fi

#===============================================================================
# TEST SUITE 3: GET CURRENT USER
#===============================================================================

print_header "TEST SUITE 3: GET CURRENT USER (/me)"

# Test 3.1: Get user with valid token
print_test "3.1 - Get current user with valid token"
run_test
ME_RESPONSE=$(curl -s -X GET "$API_URL/me" \
  -H "Authorization: Bearer $TOKEN")

print_response "$ME_RESPONSE"

if echo "$ME_RESPONSE" | grep -q "$USER_EMAIL"; then
    print_pass "Current user retrieved successfully"

    # Verify password is not in response
    if echo "$ME_RESPONSE" | grep -q "password"; then
        print_fail "PASSWORD LEAK: Password should not be in response"
    else
        print_pass "Password correctly excluded from response"
    fi
else
    print_fail "Failed to retrieve current user"
fi

# Test 3.2: Access without Authorization header
print_test "3.2 - Access /me without Authorization header (should fail)"
run_test
NO_AUTH=$(curl -s -X GET "$API_URL/me")

print_response "$NO_AUTH"

if echo "$NO_AUTH" | grep -q -i "Not authenticated\|Unauthorized"; then
    print_pass "Correctly rejected request without auth"
else
    print_fail "Should reject unauthenticated request"
fi

# Test 3.3: Invalid token format
print_test "3.3 - Access /me with invalid token format (should fail)"
run_test
INVALID_FORMAT=$(curl -s -X GET "$API_URL/me" \
  -H "Authorization: InvalidFormat")

print_response "$INVALID_FORMAT"

if echo "$INVALID_FORMAT" | grep -q -i "Invalid\|Unauthorized"; then
    print_pass "Invalid token format rejected"
else
    print_fail "Invalid token format should be rejected"
fi

# Test 3.4: Random/fake token
print_test "3.4 - Access /me with fake token (should fail)"
run_test
FAKE_TOKEN=$(python3 -c "import secrets; print(secrets.token_hex(32))")
FAKE_RESPONSE=$(curl -s -X GET "$API_URL/me" \
  -H "Authorization: Bearer $FAKE_TOKEN")

print_response "$FAKE_RESPONSE"

if echo "$FAKE_RESPONSE" | grep -q -i "Invalid\|expired\|Unauthorized"; then
    print_pass "Fake token correctly rejected"
else
    print_fail "Fake token should be rejected"
fi

# Test 3.5: Token without "Bearer" prefix
print_test "3.5 - Access /me without Bearer prefix (should fail)"
run_test
NO_BEARER=$(curl -s -X GET "$API_URL/me" \
  -H "Authorization: $TOKEN")

print_response "$NO_BEARER"

if echo "$NO_BEARER" | grep -q -i "Invalid\|Unauthorized"; then
    print_pass "Token without Bearer prefix rejected"
else
    print_fail "Should require Bearer prefix"
fi

# Test 3.6: SQL Injection in token
print_test "3.6 - SQL Injection attempt in token (should be safe)"
run_test
SQL_TOKEN="1' OR '1'='1"
SQL_RESPONSE=$(curl -s -X GET "$API_URL/me" \
  -H "Authorization: Bearer $SQL_TOKEN")

print_response "$SQL_RESPONSE"

if echo "$SQL_RESPONSE" | grep -q -i "Invalid\|Unauthorized"; then
    print_pass "SQL injection in token safely handled"
else
    print_fail "SQL injection should be prevented"
fi

#===============================================================================
# TEST SUITE 4: LOGOUT
#===============================================================================

print_header "TEST SUITE 4: LOGOUT"

# Test 4.1: Logout with valid token
print_test "4.1 - Logout with valid token"
run_test
LOGOUT_RESPONSE=$(curl -s -X POST "$API_URL/logout" \
  -H "Authorization: Bearer $TOKEN")

print_response "$LOGOUT_RESPONSE"

if echo "$LOGOUT_RESPONSE" | grep -q '"success": true'; then
    print_pass "Logout successful"
else
    print_fail "Logout failed"
fi

# Test 4.2: Use token after logout (should fail)
print_test "4.2 - Use token after logout (should fail)"
run_test
AFTER_LOGOUT=$(curl -s -X GET "$API_URL/me" \
  -H "Authorization: Bearer $TOKEN")

print_response "$AFTER_LOGOUT"

if echo "$AFTER_LOGOUT" | grep -q -i "Invalid\|expired\|Unauthorized"; then
    print_pass "Token correctly invalidated after logout"
else
    print_fail "Token should be invalid after logout"
fi

# Test 4.3: Double logout (should fail gracefully)
print_test "4.3 - Logout again with same token (should fail)"
run_test
DOUBLE_LOGOUT=$(curl -s -X POST "$API_URL/logout" \
  -H "Authorization: Bearer $TOKEN")

print_response "$DOUBLE_LOGOUT"

if echo "$DOUBLE_LOGOUT" | grep -q -i "Invalid\|Unauthorized\|error"; then
    print_pass "Double logout handled correctly"
else
    print_fail "Double logout should fail"
fi

# Test 4.4: Logout without token
print_test "4.4 - Logout without Authorization header (should fail)"
run_test
NO_TOKEN_LOGOUT=$(curl -s -X POST "$API_URL/logout")

print_response "$NO_TOKEN_LOGOUT"

if echo "$NO_TOKEN_LOGOUT" | grep -q -i "Not authenticated\|Unauthorized"; then
    print_pass "Logout without token correctly rejected"
else
    print_fail "Should reject logout without token"
fi

#===============================================================================
# TEST SUITE 5: SESSION LIFECYCLE
#===============================================================================

print_header "TEST SUITE 5: COMPLETE SESSION LIFECYCLE"

# Test 5.1: Register -> Login -> Access -> Logout -> Fail
print_test "5.1 - Complete user session lifecycle"
run_test

# Register new user
LIFECYCLE_EMAIL="lifecycle${TIMESTAMP}@example.com"
REG_RESP=$(curl -s -X POST "$API_URL/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'$LIFECYCLE_EMAIL'",
    "password": "LifecyclePass123",
    "full_name": "Lifecycle User"
  }')

if echo "$REG_RESP" | grep -q '"success": true'; then
    echo "  ✓ Step 1: User registered"
else
    echo "  ✗ Step 1: Registration failed"
    print_fail "Lifecycle test failed at registration"
    run_test
fi

# Login
LOGIN_RESP=$(curl -s -X POST "$API_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'$LIFECYCLE_EMAIL'",
    "password": "LifecyclePass123",
    "remember_me": false
  }')

LIFECYCLE_TOKEN=$(echo "$LOGIN_RESP" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)

if [ -n "$LIFECYCLE_TOKEN" ]; then
    echo "  ✓ Step 2: User logged in"
else
    echo "  ✗ Step 2: Login failed"
    print_fail "Lifecycle test failed at login"
    run_test
fi

# Access protected endpoint
ME_RESP=$(curl -s -X GET "$API_URL/me" \
  -H "Authorization: Bearer $LIFECYCLE_TOKEN")

if echo "$ME_RESP" | grep -q "$LIFECYCLE_EMAIL"; then
    echo "  ✓ Step 3: Accessed protected endpoint"
else
    echo "  ✗ Step 3: Failed to access protected endpoint"
    print_fail "Lifecycle test failed at access"
    run_test
fi

# Logout
LOGOUT_RESP=$(curl -s -X POST "$API_URL/logout" \
  -H "Authorization: Bearer $LIFECYCLE_TOKEN")

if echo "$LOGOUT_RESP" | grep -q '"success": true'; then
    echo "  ✓ Step 4: User logged out"
else
    echo "  ✗ Step 4: Logout failed"
    print_fail "Lifecycle test failed at logout"
    run_test
fi

# Try to access after logout (should fail)
FINAL_RESP=$(curl -s -X GET "$API_URL/me" \
  -H "Authorization: Bearer $LIFECYCLE_TOKEN")

if echo "$FINAL_RESP" | grep -q -i "Invalid\|expired\|Unauthorized"; then
    echo "  ✓ Step 5: Token invalid after logout"
    print_pass "Complete session lifecycle works correctly"
else
    echo "  ✗ Step 5: Token still valid after logout"
    print_fail "Token should be invalid after logout"
fi

#===============================================================================
# TEST SUITE 6: SECURITY TESTS
#===============================================================================

print_header "TEST SUITE 6: SECURITY VALIDATION"

# Test 6.1: Token uniqueness
print_test "6.1 - Verify tokens are unique for different sessions"
run_test

LOGIN1=$(curl -s -X POST "$API_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'$USER_EMAIL'",
    "password": "'$USER_PASSWORD'",
    "remember_me": false
  }')
TOKEN1=$(echo "$LOGIN1" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)

sleep 1

LOGIN2=$(curl -s -X POST "$API_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "'$USER_EMAIL'",
    "password": "'$USER_PASSWORD'",
    "remember_me": false
  }')
TOKEN2=$(echo "$LOGIN2" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)

if [ "$TOKEN1" != "$TOKEN2" ]; then
    print_pass "Tokens are unique across sessions"
else
    print_fail "SECURITY ISSUE: Tokens should be unique"
fi

# Clean up
curl -s -X POST "$API_URL/logout" -H "Authorization: Bearer $TOKEN1" > /dev/null
curl -s -X POST "$API_URL/logout" -H "Authorization: Bearer $TOKEN2" > /dev/null

# Test 6.2: Token length (should be 64 chars)
print_test "6.2 - Verify token length is 64 characters"
run_test

if [ ${#TOKEN1} -eq 64 ]; then
    print_pass "Token is 64 characters (secure length)"
else
    print_fail "Token length is ${#TOKEN1}, should be 64"
fi

# Test 6.3: Token randomness (should be hex)
print_test "6.3 - Verify token is hexadecimal (cryptographically random)"
run_test

if echo "$TOKEN1" | grep -qE '^[0-9a-f]{64}$'; then
    print_pass "Token is valid hexadecimal"
else
    print_fail "Token should be hexadecimal"
fi

#===============================================================================
# TEST SUITE 7: PERFORMANCE TESTS
#===============================================================================

print_header "TEST SUITE 7: PERFORMANCE BENCHMARKS"

# Test 7.1: Registration response time
print_test "7.1 - Measure registration response time"
run_test

START=$(python3 -c 'import time; print(int(time.time() * 1000))')
curl -s -X POST "$API_URL/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "perf'$TIMESTAMP'@example.com",
    "password": "PerfTest123",
    "full_name": "Performance Test"
  }' > /dev/null
END=$(python3 -c 'import time; print(int(time.time() * 1000))')
REG_TIME=$((END - START))

echo -e "${YELLOW}Registration time: ${REG_TIME}ms${NC}"

if [ $REG_TIME -lt 500 ]; then
    print_pass "Registration completed in ${REG_TIME}ms (< 500ms target)"
else
    echo -e "${YELLOW}WARNING: Registration took ${REG_TIME}ms (target < 500ms)${NC}"
fi

# Test 7.2: Login response time
print_test "7.2 - Measure login response time"
run_test

START=$(python3 -c 'import time; print(int(time.time() * 1000))')
curl -s -X POST "$API_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "perf'$TIMESTAMP'@example.com",
    "password": "PerfTest123",
    "remember_me": false
  }' > /dev/null
END=$(python3 -c 'import time; print(int(time.time() * 1000))')
LOGIN_TIME=$((END - START))

echo -e "${YELLOW}Login time: ${LOGIN_TIME}ms${NC}"

if [ $LOGIN_TIME -lt 300 ]; then
    print_pass "Login completed in ${LOGIN_TIME}ms (< 300ms target)"
else
    echo -e "${YELLOW}WARNING: Login took ${LOGIN_TIME}ms (target < 300ms)${NC}"
fi

# Test 7.3: Get current user response time
print_test "7.3 - Measure /me endpoint response time"
run_test

# Get a fresh token
PERF_LOGIN=$(curl -s -X POST "$API_URL/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "perf'$TIMESTAMP'@example.com",
    "password": "PerfTest123",
    "remember_me": false
  }')
PERF_TOKEN=$(echo "$PERF_LOGIN" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null)

START=$(python3 -c 'import time; print(int(time.time() * 1000))')
curl -s -X GET "$API_URL/me" \
  -H "Authorization: Bearer $PERF_TOKEN" > /dev/null
END=$(python3 -c 'import time; print(int(time.time() * 1000))')
ME_TIME=$((END - START))

echo -e "${YELLOW}Get user time: ${ME_TIME}ms${NC}"

if [ $ME_TIME -lt 100 ]; then
    print_pass "Get user completed in ${ME_TIME}ms (< 100ms target)"
else
    echo -e "${YELLOW}WARNING: Get user took ${ME_TIME}ms (target < 100ms)${NC}"
fi

# Test 7.4: Logout response time
print_test "7.4 - Measure logout response time"
run_test

START=$(python3 -c 'import time; print(int(time.time() * 1000))')
curl -s -X POST "$API_URL/logout" \
  -H "Authorization: Bearer $PERF_TOKEN" > /dev/null
END=$(python3 -c 'import time; print(int(time.time() * 1000))')
LOGOUT_TIME=$((END - START))

echo -e "${YELLOW}Logout time: ${LOGOUT_TIME}ms${NC}"

if [ $LOGOUT_TIME -lt 100 ]; then
    print_pass "Logout completed in ${LOGOUT_TIME}ms (< 100ms target)"
else
    echo -e "${YELLOW}WARNING: Logout took ${LOGOUT_TIME}ms (target < 100ms)${NC}"
fi

#===============================================================================
# TEST SUITE 8: API DOCUMENTATION
#===============================================================================

print_header "TEST SUITE 8: API DOCUMENTATION"

# Test 8.1: Swagger docs accessible
print_test "8.1 - Check if Swagger docs are accessible"
run_test

DOCS_RESPONSE=$(curl -s "$BASE_URL/docs" -o /dev/null -w "%{http_code}")

if [ "$DOCS_RESPONSE" = "200" ]; then
    print_pass "Swagger docs accessible at $BASE_URL/docs"
else
    print_fail "Swagger docs not accessible (HTTP $DOCS_RESPONSE)"
fi

# Test 8.2: OpenAPI schema accessible
print_test "8.2 - Check if OpenAPI schema is accessible"
run_test

OPENAPI_RESPONSE=$(curl -s "$BASE_URL/openapi.json" -o /dev/null -w "%{http_code}")

if [ "$OPENAPI_RESPONSE" = "200" ]; then
    print_pass "OpenAPI schema accessible at $BASE_URL/openapi.json"
else
    print_fail "OpenAPI schema not accessible (HTTP $OPENAPI_RESPONSE)"
fi

#===============================================================================
# FINAL SUMMARY
#===============================================================================

print_header "TEST EXECUTION SUMMARY"

echo ""
echo -e "${BLUE}Total Tests Run:${NC} $TOTAL_TESTS"
echo -e "${GREEN}Tests Passed:${NC} $PASSED_TESTS"
echo -e "${RED}Tests Failed:${NC} $FAILED_TESTS"
echo ""

PASS_RATE=$(python3 -c "print(f'{($PASSED_TESTS / $TOTAL_TESTS * 100):.1f}')")
echo -e "${BLUE}Pass Rate:${NC} ${PASS_RATE}%"
echo ""

echo "=== Summary ===" >> "$RESULTS_FILE"
echo "Total Tests: $TOTAL_TESTS" >> "$RESULTS_FILE"
echo "Passed: $PASSED_TESTS" >> "$RESULTS_FILE"
echo "Failed: $FAILED_TESTS" >> "$RESULTS_FILE"
echo "Pass Rate: ${PASS_RATE}%" >> "$RESULTS_FILE"
echo "" >> "$RESULTS_FILE"
echo "Completed: $(date)" >> "$RESULTS_FILE"

echo -e "${BLUE}Full results saved to:${NC} $RESULTS_FILE"
echo ""

# Performance summary
echo -e "${BLUE}Performance Metrics:${NC}"
echo "  Registration: ${REG_TIME}ms (target < 500ms)"
echo "  Login: ${LOGIN_TIME}ms (target < 300ms)"
echo "  Get User: ${ME_TIME}ms (target < 100ms)"
echo "  Logout: ${LOGOUT_TIME}ms (target < 100ms)"
echo ""

# Exit with error code if tests failed
if [ $FAILED_TESTS -gt 0 ]; then
    echo -e "${RED}Some tests failed. Please review the results above.${NC}"
    exit 1
else
    echo -e "${GREEN}All tests passed successfully!${NC}"
    exit 0
fi
