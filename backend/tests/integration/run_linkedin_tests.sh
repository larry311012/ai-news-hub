#!/bin/bash

# LinkedIn Integration Test Runner
#
# This script runs comprehensive LinkedIn integration tests to expose bugs
# in the OAuth flow, connection persistence, and cross-platform isolation.

set -e  # Exit on error

echo "=========================================="
echo "LinkedIn Integration Test Suite"
echo "=========================================="
echo ""
echo "This test suite is designed to catch:"
echo "1. False positives in test connection"
echo "2. Credential persistence bugs"
echo "3. Cross-platform contamination"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to backend directory
cd "$(dirname "$0")"

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}ERROR: pytest not found${NC}"
    echo "Please install pytest: pip install pytest pytest-cov pytest-asyncio"
    exit 1
fi

echo "Step 1: Running LinkedIn OAuth Unit Tests"
echo "==========================================
"

# Run unit tests with verbose output
pytest tests/test_linkedin_oauth.py -v --tb=short --color=yes \
    -W ignore::DeprecationWarning \
    2>&1 | tee linkedin_oauth_test_results.txt

OAUTH_EXIT_CODE=$?

echo ""
echo "Step 2: Running LinkedIn Integration Tests"
echo "==========================================="
echo ""

# Run integration tests
pytest tests/test_linkedin_integration.py -v --tb=short --color=yes \
    -W ignore::DeprecationWarning \
    2>&1 | tee linkedin_integration_test_results.txt

INTEGRATION_EXIT_CODE=$?

echo ""
echo "Step 3: Running Combined Test Suite with Coverage"
echo "=================================================="
echo ""

# Run all LinkedIn tests with coverage
pytest tests/test_linkedin_oauth.py tests/test_linkedin_integration.py \
    --cov=api/social_media \
    --cov=utils/social_oauth \
    --cov=utils/social_connection_manager \
    --cov=database_social_media \
    --cov-report=term-missing \
    --cov-report=html:htmlcov/linkedin_coverage \
    --color=yes \
    -W ignore::DeprecationWarning \
    2>&1 | tee linkedin_coverage_report.txt

COVERAGE_EXIT_CODE=$?

echo ""
echo "=========================================="
echo "Test Results Summary"
echo "=========================================="
echo ""

# Count failures from each test run
OAUTH_FAILURES=$(grep -c "FAILED" linkedin_oauth_test_results.txt || echo "0")
INTEGRATION_FAILURES=$(grep -c "FAILED" linkedin_integration_test_results.txt || echo "0")

echo "OAuth Unit Tests:"
if [ $OAUTH_EXIT_CODE -eq 0 ]; then
    echo -e "  ${GREEN}✓ All tests passed${NC}"
else
    echo -e "  ${RED}✗ $OAUTH_FAILURES test(s) failed${NC}"
fi

echo ""
echo "Integration Tests:"
if [ $INTEGRATION_EXIT_CODE -eq 0 ]; then
    echo -e "  ${GREEN}✓ All tests passed${NC}"
else
    echo -e "  ${RED}✗ $INTEGRATION_FAILURES test(s) failed${NC}"
fi

echo ""
echo "Coverage Report:"
if [ $COVERAGE_EXIT_CODE -eq 0 ]; then
    echo -e "  ${GREEN}✓ Coverage report generated${NC}"
else
    echo -e "  ${YELLOW}⚠ Coverage report completed with errors${NC}"
fi

echo ""
echo "Test artifacts saved:"
echo "  - linkedin_oauth_test_results.txt"
echo "  - linkedin_integration_test_results.txt"
echo "  - linkedin_coverage_report.txt"
echo "  - htmlcov/linkedin_coverage/index.html (HTML coverage report)"

echo ""
echo "=========================================="
echo "Expected Failures (Before Bug Fixes)"
echo "=========================================="
echo ""
echo "The following tests are EXPECTED to FAIL before bugs are fixed:"
echo ""
echo "1. test_setup_and_post_pages_see_same_status"
echo "   - BUG: Setup and post pages see different statuses"
echo ""
echo "2. test_linkedin_status_ignores_instagram_connection"
echo "   - BUG: Cross-platform contamination"
echo ""
echo "3. test_validate_connection_makes_real_api_call"
echo "   - BUG: Test connection might not call actual API"
echo ""
echo "4. test_callback_creates_connection_record"
echo "   - BUG: OAuth callback might not create connection"
echo ""

# Create summary JSON for programmatic access
cat > linkedin_test_summary.json <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "oauth_tests": {
    "exit_code": $OAUTH_EXIT_CODE,
    "failures": $OAUTH_FAILURES,
    "passed": $([ $OAUTH_EXIT_CODE -eq 0 ] && echo "true" || echo "false")
  },
  "integration_tests": {
    "exit_code": $INTEGRATION_EXIT_CODE,
    "failures": $INTEGRATION_FAILURES,
    "passed": $([ $INTEGRATION_EXIT_CODE -eq 0 ] && echo "true" || echo "false")
  },
  "coverage": {
    "exit_code": $COVERAGE_EXIT_CODE,
    "report_path": "htmlcov/linkedin_coverage/index.html"
  }
}
EOF

echo ""
echo "Summary JSON saved to: linkedin_test_summary.json"
echo ""

# Exit with failure if any test suite failed
if [ $OAUTH_EXIT_CODE -ne 0 ] || [ $INTEGRATION_EXIT_CODE -ne 0 ]; then
    echo -e "${RED}Some tests failed. See above for details.${NC}"
    exit 1
else
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
fi
