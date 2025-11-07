#!/bin/bash

echo "======================================"
echo "Instagram OAuth & Publishing Tests"
echo "======================================"
echo ""
echo "This test suite validates:"
echo "- InstagramPublisher class (unit tests)"
echo "- OAuth endpoints (integration tests)"
echo "- Publishing flow (integration tests)"
echo "- End-to-end workflow (E2E tests)"
echo ""
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track test results
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# Function to run tests and capture results
run_test_suite() {
    local suite_name=$1
    local test_file=$2

    echo -e "${YELLOW}[$suite_name]${NC}"
    echo "Running: $test_file"
    echo ""

    # Run tests with verbose output
    pytest "$test_file" -v --tb=short --color=yes

    local exit_code=$?

    # Capture test counts
    local result=$(pytest "$test_file" -v --tb=no -q 2>&1 | tail -1)

    echo ""
    echo "Result: $result"
    echo ""

    return $exit_code
}

# Change to backend directory
cd "$(dirname "$0")" || exit 1

# Ensure we're in the backend directory
if [ ! -f "pytest.ini" ]; then
    echo "Error: pytest.ini not found. Are you in the backend directory?"
    exit 1
fi

# 1. Unit tests - InstagramPublisher
echo "======================================"
echo "[1/4] InstagramPublisher Unit Tests"
echo "======================================"
echo ""
run_test_suite "Publisher Unit Tests" "tests/test_instagram_publisher.py"
TEST1_EXIT=$?
echo ""

# 2. OAuth endpoints integration tests
echo "======================================"
echo "[2/4] OAuth Endpoints Integration Tests"
echo "======================================"
echo ""
run_test_suite "OAuth Endpoints" "tests/test_instagram_oauth_endpoints.py"
TEST2_EXIT=$?
echo ""

# 3. Publishing flow integration tests
echo "======================================"
echo "[3/4] Publishing Flow Integration Tests"
echo "======================================"
echo ""
run_test_suite "Publishing Flow" "tests/test_instagram_publishing_flow.py"
TEST3_EXIT=$?
echo ""

# 4. End-to-end tests
echo "======================================"
echo "[4/4] End-to-End Tests"
echo "======================================"
echo ""
run_test_suite "E2E Tests" "tests/test_instagram_e2e_oauth_publish.py"
TEST4_EXIT=$?
echo ""

# Summary
echo ""
echo "======================================"
echo "Test Summary"
echo "======================================"
echo ""

# Run all tests together to get summary
pytest tests/test_instagram_publisher.py \
       tests/test_instagram_oauth_endpoints.py \
       tests/test_instagram_publishing_flow.py \
       tests/test_instagram_e2e_oauth_publish.py \
       --tb=no -q

echo ""
echo "======================================"
echo "Coverage Report"
echo "======================================"
echo ""

# Generate coverage report for Instagram-related code
pytest tests/test_instagram_publisher.py \
       tests/test_instagram_oauth_endpoints.py \
       tests/test_instagram_publishing_flow.py \
       tests/test_instagram_e2e_oauth_publish.py \
       --cov=src/publishers \
       --cov=api/social_media_instagram \
       --cov=utils/instagram_oauth \
       --cov-report=term-missing \
       --cov-report=html:htmlcov/instagram \
       --tb=no -q

echo ""
echo "======================================"
echo "Individual Test Suite Results"
echo "======================================"
echo ""

if [ $TEST1_EXIT -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Publisher unit tests: PASSED"
else
    echo -e "${RED}✗${NC} Publisher unit tests: FAILED"
fi

if [ $TEST2_EXIT -eq 0 ]; then
    echo -e "${GREEN}✓${NC} OAuth endpoint tests: PASSED"
else
    echo -e "${RED}✗${NC} OAuth endpoint tests: FAILED"
fi

if [ $TEST3_EXIT -eq 0 ]; then
    echo -e "${GREEN}✓${NC} Publishing flow tests: PASSED"
else
    echo -e "${RED}✗${NC} Publishing flow tests: FAILED"
fi

if [ $TEST4_EXIT -eq 0 ]; then
    echo -e "${GREEN}✓${NC} End-to-end tests: PASSED"
else
    echo -e "${RED}✗${NC} End-to-end tests: FAILED"
fi

echo ""
echo "======================================"
echo ""

# Calculate overall result
TOTAL_EXIT=$((TEST1_EXIT + TEST2_EXIT + TEST3_EXIT + TEST4_EXIT))

if [ $TOTAL_EXIT -eq 0 ]; then
    echo -e "${GREEN}All Instagram OAuth & Publishing tests passed!${NC}"
    echo ""
    echo "Coverage report saved to: htmlcov/instagram/index.html"
    exit 0
else
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    echo ""
    echo "To run individual test suites:"
    echo "  pytest tests/test_instagram_publisher.py -v"
    echo "  pytest tests/test_instagram_oauth_endpoints.py -v"
    echo "  pytest tests/test_instagram_publishing_flow.py -v"
    echo "  pytest tests/test_instagram_e2e_oauth_publish.py -v"
    exit 1
fi
