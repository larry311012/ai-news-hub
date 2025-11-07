#!/bin/bash
#
# Instagram Image Generation Test Suite Runner
#
# Runs all tests for Instagram image generation feature including:
# - Unit tests (services, utils)
# - Integration tests (API endpoints)
# - End-to-end tests (full workflows)
# - Performance tests (load, concurrency)
#
# Usage:
#   ./run_instagram_tests.sh              # Run all tests
#   ./run_instagram_tests.sh unit         # Run only unit tests
#   ./run_instagram_tests.sh integration  # Run only integration tests
#   ./run_instagram_tests.sh coverage     # Run with coverage report
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test configuration
TEST_DIR="tests"
COVERAGE_MIN=80  # Minimum coverage percentage

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Instagram Test Suite Runner${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Parse command line arguments
TEST_TYPE="${1:-all}"

# Function to run tests with optional coverage
run_tests() {
    local test_file=$1
    local test_name=$2
    local coverage=${3:-false}

    echo -e "\n${GREEN}Running: ${test_name}${NC}"
    echo -e "${BLUE}----------------------------------------${NC}"

    if [ "$coverage" = true ]; then
        pytest "${test_file}" -v --cov=services --cov=utils --cov=api \
            --cov-report=term --cov-report=html \
            --tb=short
    else
        pytest "${test_file}" -v --tb=short
    fi

    echo ""
}

# Run unit tests
run_unit_tests() {
    echo -e "\n${YELLOW}=== UNIT TESTS ===${NC}"

    run_tests "${TEST_DIR}/test_image_generation_service.py" \
        "Image Generation Service Tests" $1

    run_tests "${TEST_DIR}/test_image_storage.py" \
        "Image Storage Tests" $1
}

# Run integration tests
run_integration_tests() {
    echo -e "\n${YELLOW}=== INTEGRATION TESTS ===${NC}"

    run_tests "${TEST_DIR}/test_instagram_api_endpoints.py" \
        "API Endpoint Tests" $1

    # Run existing Instagram image generation tests if they exist
    if [ -f "${TEST_DIR}/test_instagram_image_generation.py" ]; then
        run_tests "${TEST_DIR}/test_instagram_image_generation.py" \
            "Instagram Image Generation Tests" $1
    fi
}

# Run end-to-end tests
run_e2e_tests() {
    echo -e "\n${YELLOW}=== END-TO-END TESTS ===${NC}"

    run_tests "${TEST_DIR}/test_instagram_e2e.py" \
        "E2E Workflow Tests" $1
}

# Run performance tests
run_performance_tests() {
    echo -e "\n${YELLOW}=== PERFORMANCE TESTS ===${NC}"

    run_tests "${TEST_DIR}/test_instagram_performance.py" \
        "Performance Tests" $1
}

# Run all Instagram-related tests
run_all_tests() {
    local coverage=$1

    echo -e "${GREEN}Running complete Instagram test suite...${NC}\n"

    run_unit_tests $coverage
    run_integration_tests $coverage
    run_e2e_tests $coverage
    run_performance_tests $coverage
}

# Generate coverage report
generate_coverage_report() {
    echo -e "\n${YELLOW}=== COVERAGE REPORT ===${NC}"

    pytest ${TEST_DIR}/test_image_*.py ${TEST_DIR}/test_instagram_*.py \
        --cov=services --cov=utils --cov=api \
        --cov-report=term-missing \
        --cov-report=html:htmlcov/instagram \
        --cov-report=json:coverage_instagram.json \
        --tb=short

    echo -e "\n${GREEN}Coverage reports generated:${NC}"
    echo "  - Terminal: Above"
    echo "  - HTML: htmlcov/instagram/index.html"
    echo "  - JSON: coverage_instagram.json"

    # Check minimum coverage
    coverage=$(python3 -c "import json; print(json.load(open('coverage_instagram.json'))['totals']['percent_covered'])" 2>/dev/null || echo "0")

    if (( $(echo "$coverage >= $COVERAGE_MIN" | bc -l) )); then
        echo -e "\n${GREEN}✓ Coverage: ${coverage}% (>= ${COVERAGE_MIN}%)${NC}"
    else
        echo -e "\n${YELLOW}⚠ Coverage: ${coverage}% (< ${COVERAGE_MIN}%)${NC}"
    fi
}

# Main execution
case "$TEST_TYPE" in
    unit)
        run_unit_tests false
        ;;
    integration)
        run_integration_tests false
        ;;
    e2e)
        run_e2e_tests false
        ;;
    performance)
        run_performance_tests false
        ;;
    coverage)
        generate_coverage_report
        ;;
    all)
        run_all_tests false
        ;;
    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo "Usage: $0 {unit|integration|e2e|performance|coverage|all}"
        exit 1
        ;;
esac

# Summary
echo -e "\n${BLUE}========================================${NC}"
echo -e "${GREEN}Test Suite Complete!${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Show quick command reference
echo -e "${YELLOW}Quick Commands:${NC}"
echo "  Run all tests:         ./run_instagram_tests.sh"
echo "  Unit tests only:       ./run_instagram_tests.sh unit"
echo "  Integration tests:     ./run_instagram_tests.sh integration"
echo "  E2E tests:             ./run_instagram_tests.sh e2e"
echo "  Performance tests:     ./run_instagram_tests.sh performance"
echo "  Coverage report:       ./run_instagram_tests.sh coverage"
echo ""

exit 0
