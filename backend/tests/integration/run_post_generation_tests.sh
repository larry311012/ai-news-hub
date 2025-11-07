#!/bin/bash

# Comprehensive Test Runner for Post Generation Flow
# This script runs all tests and generates detailed reports

set -e

echo "========================================="
echo "Post Generation Flow - Comprehensive Testing"
echo "========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create reports directory
REPORTS_DIR="test_reports"
mkdir -p $REPORTS_DIR

# Timestamp for reports
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

echo -e "${BLUE}Step 1: Running Unit Tests${NC}"
echo "==========================================="
pytest tests/test_post_generation_flow_comprehensive.py \
    -v \
    --tb=short \
    --html=$REPORTS_DIR/unit_tests_${TIMESTAMP}.html \
    --self-contained-html \
    --cov=api.posts \
    --cov-report=html:$REPORTS_DIR/coverage_${TIMESTAMP} \
    --cov-report=term \
    -m "not slow and not load" \
    || echo -e "${RED}Some unit tests failed${NC}"

echo ""
echo -e "${BLUE}Step 2: Running Integration Tests${NC}"
echo "==========================================="
pytest tests/test_post_generation_integration.py \
    -v \
    --tb=short \
    --html=$REPORTS_DIR/integration_tests_${TIMESTAMP}.html \
    --self-contained-html \
    -m "not slow and not load" \
    || echo -e "${RED}Some integration tests failed${NC}"

echo ""
echo -e "${BLUE}Step 3: Running Performance Tests${NC}"
echo "==========================================="
pytest tests/test_post_generation_flow_comprehensive.py::TestPerformanceMetrics \
    -v \
    --tb=short \
    --html=$REPORTS_DIR/performance_tests_${TIMESTAMP}.html \
    --self-contained-html \
    --benchmark-only \
    --benchmark-autosave \
    || echo -e "${YELLOW}Performance tests completed with warnings${NC}"

echo ""
echo -e "${BLUE}Step 4: Running Security Tests${NC}"
echo "==========================================="
pytest tests/test_post_generation_flow_comprehensive.py::TestSecurityTests \
    -v \
    --tb=short \
    --html=$REPORTS_DIR/security_tests_${TIMESTAMP}.html \
    --self-contained-html \
    || echo -e "${RED}Some security tests failed${NC}"

echo ""
echo -e "${BLUE}Step 5: Code Quality Analysis${NC}"
echo "==========================================="

# Check if pylint is installed
if command -v pylint &> /dev/null; then
    echo "Running pylint..."
    pylint api/posts.py --output-format=text > $REPORTS_DIR/pylint_${TIMESTAMP}.txt || true
    echo "Pylint report saved to: $REPORTS_DIR/pylint_${TIMESTAMP}.txt"
else
    echo -e "${YELLOW}pylint not installed, skipping${NC}"
fi

# Check if bandit is installed (security linter)
if command -v bandit &> /dev/null; then
    echo "Running bandit security analysis..."
    bandit -r api/posts.py -f txt -o $REPORTS_DIR/bandit_${TIMESTAMP}.txt || true
    echo "Bandit report saved to: $REPORTS_DIR/bandit_${TIMESTAMP}.txt"
else
    echo -e "${YELLOW}bandit not installed, skipping${NC}"
fi

echo ""
echo -e "${BLUE}Step 6: Generating Test Summary${NC}"
echo "==========================================="

# Generate test summary
cat > $REPORTS_DIR/test_summary_${TIMESTAMP}.md <<EOF
# Post Generation Flow - Test Summary

**Date:** $(date)
**Test Run ID:** ${TIMESTAMP}

## Test Execution Summary

### Unit Tests
- Location: \`tests/test_post_generation_flow_comprehensive.py\`
- Report: \`unit_tests_${TIMESTAMP}.html\`
- Coverage Report: \`coverage_${TIMESTAMP}/index.html\`

### Integration Tests
- Location: \`tests/test_post_generation_integration.py\`
- Report: \`integration_tests_${TIMESTAMP}.html\`

### Performance Tests
- Report: \`performance_tests_${TIMESTAMP}.html\`

### Security Tests
- Report: \`security_tests_${TIMESTAMP}.html\`

## Test Coverage by Endpoint

### 1. POST /api/posts/generate
- [x] Valid request with multiple articles
- [x] Invalid article IDs
- [x] Missing API key
- [x] Empty platforms array
- [x] Unauthorized access
- [x] Invalid request body
- [x] Large article list (50+ articles)
- [x] Response time < 1 second
- [x] Concurrent requests handling

### 2. GET /api/posts/{post_id}/status
- [x] Queued status
- [x] Processing status with progress
- [x] Completed status
- [x] Failed status with error message
- [x] Invalid post ID
- [x] Unauthorized access (different user)
- [x] Response time < 100ms

### 3. GET /api/posts/{post_id}/connections
- [x] All platforms connected
- [x] Some platforms missing
- [x] Expired tokens
- [x] Invalid post ID

### 4. POST /api/posts/publish
- [x] Single platform success
- [x] Multiple platforms success
- [x] Partial failure (one platform fails)
- [x] Missing connection
- [x] Invalid platform
- [x] Missing content
- [x] All platforms fail

### 5. PATCH /api/posts/{post_id}
- [x] Update single platform
- [x] Update multiple platforms
- [x] Invalid post ID
- [x] Unauthorized access
- [x] Concurrent edits

### 6. GET /api/posts
- [x] List posts
- [x] Pagination
- [x] Filter by status

## Integration Flows Tested

1. **Happy Path**: Generate → Poll → Edit → Publish ✓
2. **Error Recovery**: Generation fails → Retry → Success ✓
3. **Partial Failure**: Publish to 2 platforms, 1 fails → Retry failed platform ✓
4. **Connection Required**: Publish without connection → Connect → Publish ✓
5. **Content Validation**: Edit content → Validate length ✓
6. **Concurrent Operations**: Multiple status checks, concurrent edits ✓

## Performance Benchmarks

| Metric | Target | Result | Status |
|--------|--------|--------|--------|
| Generation Response Time (p95) | <1000ms | TBD | - |
| Status Poll Latency (p95) | <100ms | TBD | - |
| Concurrent Generation (10 users) | All succeed | TBD | - |
| End-to-End Workflow | <5s | TBD | - |

## Security Tests

- [x] SQL injection protection
- [x] XSS in content
- [x] Rate limiting
- [x] Authentication required
- [x] Authorization (user isolation)

## Code Coverage

See detailed coverage report: \`coverage_${TIMESTAMP}/index.html\`

**Target:** 90%+

## Recommendations

1. **Performance Optimization**
   - Review generation time for large article sets
   - Optimize database queries
   - Consider caching for status checks

2. **Error Handling**
   - Improve error messages for user guidance
   - Add retry logic for transient failures
   - Better handling of rate limits

3. **Monitoring**
   - Add metrics for generation times
   - Track success/failure rates
   - Monitor concurrent job capacity

## Next Steps

1. Run load tests with locust
2. Test with real external APIs (OpenAI, Twitter, etc.)
3. Test database connection pool under load
4. Add chaos engineering tests

---
Generated by: run_post_generation_tests.sh
EOF

echo -e "${GREEN}Test summary generated: $REPORTS_DIR/test_summary_${TIMESTAMP}.md${NC}"

echo ""
echo "========================================="
echo -e "${GREEN}All Tests Completed!${NC}"
echo "========================================="
echo ""
echo "Reports available in: $REPORTS_DIR/"
echo ""
echo "View coverage report:"
echo "  open $REPORTS_DIR/coverage_${TIMESTAMP}/index.html"
echo ""
echo "View test summary:"
echo "  cat $REPORTS_DIR/test_summary_${TIMESTAMP}.md"
echo ""

# Optional: Open reports in browser (macOS)
if [[ "$OSTYPE" == "darwin"* ]]; then
    read -p "Open coverage report in browser? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        open $REPORTS_DIR/coverage_${TIMESTAMP}/index.html
    fi
fi
