#!/bin/bash
# Security Audit Test Script for Phase 4
# Tests various security features and potential vulnerabilities

set -e  # Exit on error

BASE_URL="http://localhost:8001"
TEST_EMAIL="security_test_$(date +%s)@example.com"
TEST_PASSWORD="TestPass123!@#"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Helper functions
print_header() {
    echo ""
    echo "=========================================="
    echo "$1"
    echo "=========================================="
}

print_test() {
    echo ""
    echo "TEST: $1"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
}

print_pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    PASSED_TESTS=$((PASSED_TESTS + 1))
}

print_fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    FAILED_TESTS=$((FAILED_TESTS + 1))
}

print_warning() {
    echo -e "${YELLOW}⚠ WARNING${NC}: $1"
}

# Check if server is running
check_server() {
    print_header "Checking Server Status"
    if curl -s "$BASE_URL/health" > /dev/null; then
        print_pass "Server is running"
        return 0
    else
        print_fail "Server is not running at $BASE_URL"
        echo "Please start the server with: python main.py"
        exit 1
    fi
}

# Test 1: SQL Injection Attempts
test_sql_injection() {
    print_header "SQL Injection Tests"

    print_test "SQL injection in email field"
    RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$BASE_URL/api/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"email":"admin'\'' OR '\''1'\''='\''1","password":"test"}')

    if [ "$RESPONSE" = "422" ] || [ "$RESPONSE" = "401" ]; then
        print_pass "SQL injection blocked in email (status: $RESPONSE)"
    else
        print_fail "Unexpected response to SQL injection: $RESPONSE"
    fi

    print_test "SQL injection in password field"
    RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$BASE_URL/api/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"email":"test@example.com","password":"'\'' OR '\''1'\''='\''1"}')

    if [ "$RESPONSE" = "401" ]; then
        print_pass "SQL injection blocked in password (status: $RESPONSE)"
    else
        print_fail "Unexpected response to SQL injection: $RESPONSE"
    fi
}

# Test 2: Password Strength Enforcement
test_password_strength() {
    print_header "Password Strength Tests"

    print_test "Reject weak password"
    RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/register" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"weak_$TEST_EMAIL\",\"password\":\"weak\",\"full_name\":\"Test User\"}" \
        | grep -o '"success":[^,}]*')

    if echo "$RESPONSE" | grep -q "false"; then
        print_pass "Weak password rejected"
    else
        print_fail "Weak password accepted"
    fi

    print_test "Reject password without uppercase"
    RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/register" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"noupper_$TEST_EMAIL\",\"password\":\"lowercase123!\",\"full_name\":\"Test User\"}" \
        | grep -o '"success":[^,}]*')

    if echo "$RESPONSE" | grep -q "false"; then
        print_pass "Password without uppercase rejected"
    else
        print_fail "Password without uppercase accepted"
    fi

    print_test "Accept strong password"
    RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/register" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\",\"full_name\":\"Test User\"}" \
        | grep -o '"success":[^,}]*')

    if echo "$RESPONSE" | grep -q "true"; then
        print_pass "Strong password accepted"
    else
        print_fail "Strong password rejected"
    fi
}

# Test 3: Rate Limiting
test_rate_limiting() {
    print_header "Rate Limiting Tests"

    print_test "Login rate limiting"
    local failed_count=0
    local rate_limited=false

    for i in {1..7}; do
        RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$BASE_URL/api/auth/login" \
            -H "Content-Type: application/json" \
            -d '{"email":"ratelimit@example.com","password":"wrongpassword"}')

        if [ "$RESPONSE" = "429" ]; then
            rate_limited=true
            break
        elif [ "$RESPONSE" = "401" ]; then
            failed_count=$((failed_count + 1))
        fi
        sleep 0.5
    done

    if [ "$rate_limited" = true ]; then
        print_pass "Rate limiting triggered after $failed_count attempts"
    else
        print_fail "Rate limiting not triggered after 7 attempts"
    fi
}

# Test 4: Authentication Bypass Attempts
test_auth_bypass() {
    print_header "Authentication Bypass Tests"

    print_test "Access protected endpoint without token"
    RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null -X GET "$BASE_URL/api/auth/me")

    if [ "$RESPONSE" = "401" ]; then
        print_pass "Unauthorized access blocked (status: $RESPONSE)"
    else
        print_fail "Unauthorized access not blocked properly (status: $RESPONSE)"
    fi

    print_test "Access with invalid token"
    RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null -X GET "$BASE_URL/api/auth/me" \
        -H "Authorization: Bearer invalid_token_12345")

    if [ "$RESPONSE" = "401" ]; then
        print_pass "Invalid token rejected (status: $RESPONSE)"
    else
        print_fail "Invalid token not rejected (status: $RESPONSE)"
    fi

    print_test "Access with malformed Authorization header"
    RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null -X GET "$BASE_URL/api/auth/me" \
        -H "Authorization: invalid_format")

    if [ "$RESPONSE" = "401" ]; then
        print_pass "Malformed header rejected (status: $RESPONSE)"
    else
        print_fail "Malformed header not rejected (status: $RESPONSE)"
    fi
}

# Test 5: Email Enumeration Prevention
test_email_enumeration() {
    print_header "Email Enumeration Tests"

    print_test "Password reset for existing email"
    RESPONSE1=$(curl -s -X POST "$BASE_URL/api/auth/forgot-password" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$TEST_EMAIL\"}")

    print_test "Password reset for non-existing email"
    RESPONSE2=$(curl -s -X POST "$BASE_URL/api/auth/forgot-password" \
        -H "Content-Type: application/json" \
        -d '{"email":"nonexistent@example.com"}')

    # Both should return similar success messages
    if [ "$RESPONSE1" = "$RESPONSE2" ]; then
        print_pass "Email enumeration prevented (identical responses)"
    else
        print_warning "Responses differ - potential email enumeration"
        echo "Response 1: $RESPONSE1"
        echo "Response 2: $RESPONSE2"
    fi
}

# Test 6: Session Security
test_session_security() {
    print_header "Session Security Tests"

    print_test "Login and get token"
    LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$TEST_EMAIL\",\"password\":\"$TEST_PASSWORD\"}")

    TOKEN=$(echo "$LOGIN_RESPONSE" | grep -o '"token":"[^"]*"' | cut -d'"' -f4)

    if [ -n "$TOKEN" ]; then
        print_pass "Login successful, token obtained"

        print_test "Access protected resource with valid token"
        RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null -X GET "$BASE_URL/api/auth/me" \
            -H "Authorization: Bearer $TOKEN")

        if [ "$RESPONSE" = "200" ]; then
            print_pass "Protected resource accessible with valid token"
        else
            print_fail "Cannot access protected resource with valid token (status: $RESPONSE)"
        fi

        print_test "Session appears in sessions list"
        SESSIONS=$(curl -s -X GET "$BASE_URL/api/auth/security/sessions" \
            -H "Authorization: Bearer $TOKEN")

        if echo "$SESSIONS" | grep -q "is_current"; then
            print_pass "Session tracking working"
        else
            print_fail "Session not tracked properly"
        fi
    else
        print_fail "Login failed, cannot test session security"
    fi
}

# Test 7: Input Validation
test_input_validation() {
    print_header "Input Validation Tests"

    print_test "Invalid email format"
    RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$BASE_URL/api/auth/register" \
        -H "Content-Type: application/json" \
        -d '{"email":"notanemail","password":"TestPass123!","full_name":"Test"}')

    if [ "$RESPONSE" = "422" ]; then
        print_pass "Invalid email format rejected (status: $RESPONSE)"
    else
        print_fail "Invalid email format not rejected (status: $RESPONSE)"
    fi

    print_test "Empty full name"
    RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$BASE_URL/api/auth/register" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"test@example.com\",\"password\":\"TestPass123!\",\"full_name\":\"\"}")

    if [ "$RESPONSE" = "422" ] || [ "$RESPONSE" = "400" ]; then
        print_pass "Empty full name rejected (status: $RESPONSE)"
    else
        print_fail "Empty full name not rejected (status: $RESPONSE)"
    fi

    print_test "Very long input (DoS attempt)"
    LONG_STRING=$(python3 -c "print('A' * 10000)")
    RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$BASE_URL/api/auth/register" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"test@example.com\",\"password\":\"TestPass123!\",\"full_name\":\"$LONG_STRING\"}")

    if [ "$RESPONSE" = "422" ] || [ "$RESPONSE" = "400" ] || [ "$RESPONSE" = "413" ]; then
        print_pass "Very long input rejected (status: $RESPONSE)"
    else
        print_warning "Very long input not rejected (status: $RESPONSE) - may cause issues"
    fi
}

# Test 8: Password Reset Token Security
test_password_reset_tokens() {
    print_header "Password Reset Token Tests"

    print_test "Invalid reset token"
    RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null -X GET "$BASE_URL/api/auth/validate-reset-token/invalid_token_12345")

    if [ "$RESPONSE" = "200" ]; then
        TOKEN_VALID=$(curl -s -X GET "$BASE_URL/api/auth/validate-reset-token/invalid_token_12345" | grep -o '"valid":[^,}]*')
        if echo "$TOKEN_VALID" | grep -q "false"; then
            print_pass "Invalid token correctly identified as invalid"
        else
            print_fail "Invalid token marked as valid"
        fi
    else
        print_fail "Unexpected response for invalid token (status: $RESPONSE)"
    fi

    print_test "Attempt reset with invalid token"
    RESPONSE=$(curl -s -w "%{http_code}" -o /dev/null -X POST "$BASE_URL/api/auth/reset-password" \
        -H "Content-Type: application/json" \
        -d '{"token":"invalid_token","new_password":"NewPass123!"}')

    if [ "$RESPONSE" = "400" ]; then
        print_pass "Password reset blocked with invalid token (status: $RESPONSE)"
    else
        print_fail "Password reset not properly blocked (status: $RESPONSE)"
    fi
}

# Test 9: CORS Configuration
test_cors() {
    print_header "CORS Configuration Tests"

    print_test "CORS headers present"
    RESPONSE=$(curl -s -I -X OPTIONS "$BASE_URL/api/auth/me" \
        -H "Origin: http://localhost:8080")

    if echo "$RESPONSE" | grep -qi "access-control-allow-origin"; then
        print_pass "CORS headers present"
    else
        print_fail "CORS headers missing"
    fi
}

# Test 10: Security Headers
test_security_headers() {
    print_header "Security Headers Tests"

    print_test "Security headers check"
    HEADERS=$(curl -s -I "$BASE_URL/")

    # Check for recommended security headers
    MISSING_HEADERS=()

    if ! echo "$HEADERS" | grep -qi "X-Content-Type-Options"; then
        MISSING_HEADERS+=("X-Content-Type-Options")
    fi

    if ! echo "$HEADERS" | grep -qi "X-Frame-Options"; then
        MISSING_HEADERS+=("X-Frame-Options")
    fi

    if ! echo "$HEADERS" | grep -qi "Strict-Transport-Security"; then
        MISSING_HEADERS+=("Strict-Transport-Security (HSTS)")
    fi

    if [ ${#MISSING_HEADERS[@]} -eq 0 ]; then
        print_pass "All security headers present"
    else
        print_warning "Missing security headers: ${MISSING_HEADERS[*]}"
        print_warning "Consider adding security headers middleware"
    fi
}

# Main execution
main() {
    echo "================================================"
    echo "Security Audit Test Script - Phase 4"
    echo "================================================"
    echo "Base URL: $BASE_URL"
    echo "Test Email: $TEST_EMAIL"
    echo "Started: $(date)"
    echo ""

    check_server
    test_sql_injection
    test_password_strength
    test_rate_limiting
    test_auth_bypass
    test_email_enumeration
    test_session_security
    test_input_validation
    test_password_reset_tokens
    test_cors
    test_security_headers

    # Summary
    echo ""
    echo "================================================"
    echo "SECURITY AUDIT SUMMARY"
    echo "================================================"
    echo "Total Tests: $TOTAL_TESTS"
    echo -e "${GREEN}Passed: $PASSED_TESTS${NC}"
    echo -e "${RED}Failed: $FAILED_TESTS${NC}"

    PASS_RATE=$((PASSED_TESTS * 100 / TOTAL_TESTS))
    echo "Pass Rate: $PASS_RATE%"

    echo ""
    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "${GREEN}✓ ALL SECURITY TESTS PASSED${NC}"
        exit 0
    else
        echo -e "${RED}✗ SOME SECURITY TESTS FAILED${NC}"
        echo "Please review failed tests and fix issues before production deployment"
        exit 1
    fi
}

# Run main function
main
