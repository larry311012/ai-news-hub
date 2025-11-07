#!/bin/bash

# Twitter Publishing Comprehensive Test Suite Runner
# This script runs all tests related to Twitter publishing functionality
# and generates a detailed report

set -e

echo "========================================="
echo "Twitter Publishing Test Suite"
echo "========================================="
echo ""
echo "Testing Twitter publishing functionality including:"
echo "  - OAuth 2.0 vs OAuth 1.0a credential handling"
echo "  - Publisher class selection"
echo "  - 403/401/429 error handling"
echo "  - Database state consistency"
echo "  - End-to-end publishing flow"
echo ""
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Set working directory
cd /Users/ranhui/ai_post/web/backend

# Create test results directory
mkdir -p test_results
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="test_results/twitter_publishing_test_report_${TIMESTAMP}.txt"

echo "Report will be saved to: $REPORT_FILE"
echo ""

# Run comprehensive test suite
echo "========================================="
echo "Running Twitter Publishing Tests"
echo "========================================="

pytest tests/test_twitter_publishing_comprehensive.py \
    -v \
    --tb=short \
    --color=yes \
    --maxfail=5 \
    --junit-xml=test_results/twitter_publishing_junit_${TIMESTAMP}.xml \
    --html=test_results/twitter_publishing_report_${TIMESTAMP}.html \
    --self-contained-html \
    2>&1 | tee "$REPORT_FILE"

TEST_EXIT_CODE=${PIPESTATUS[0]}

echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="

# Parse test results
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
else
    echo -e "${RED}✗ Some tests failed${NC}"
fi

# Count test results
PASSED=$(grep -c "PASSED" "$REPORT_FILE" || true)
FAILED=$(grep -c "FAILED" "$REPORT_FILE" || true)
SKIPPED=$(grep -c "SKIPPED" "$REPORT_FILE" || true)

echo ""
echo "Test Results:"
echo "  Passed:  $PASSED"
echo "  Failed:  $FAILED"
echo "  Skipped: $SKIPPED"
echo ""

# Show critical failures
if [ $FAILED -gt 0 ]; then
    echo "========================================="
    echo "Critical Failures:"
    echo "========================================="
    grep "FAILED.*test_" "$REPORT_FILE" | sed 's/.*FAILED /  - /' || echo "  (No failures found in parse)"
    echo ""
fi

echo "========================================="
echo "Reports Generated:"
echo "========================================="
echo "  Text Report:  $REPORT_FILE"
echo "  JUnit XML:    test_results/twitter_publishing_junit_${TIMESTAMP}.xml"
echo "  HTML Report:  test_results/twitter_publishing_report_${TIMESTAMP}.html"
echo ""

# Run additional diagnostic tests if failures detected
if [ $FAILED -gt 0 ]; then
    echo "========================================="
    echo "Running Diagnostics"
    echo "========================================="
    echo ""

    # Check if Twitter connections exist
    echo "Checking Twitter connections in database..."
    python3 -c "
from database import SessionLocal
from database_social_media import SocialMediaConnection

db = SessionLocal()
connections = db.query(SocialMediaConnection).filter(
    SocialMediaConnection.platform == 'twitter'
).all()

print(f'Found {len(connections)} Twitter connection(s)')
for conn in connections:
    print(f'  - User {conn.user_id}: {conn.platform_username} (Type: {conn.token_type}, Active: {conn.is_active})')
    if conn.expires_at:
        from datetime import datetime
        if conn.expires_at < datetime.utcnow():
            print(f'    WARNING: Token expired at {conn.expires_at}')
        else:
            print(f'    Token expires at {conn.expires_at}')
    else:
        print(f'    Token does not expire (OAuth 1.0a)')

db.close()
"
    echo ""

    # Check for failed publishes
    echo "Checking recent failed publishes..."
    python3 -c "
from database import SessionLocal, Post
from database_social_media import SocialMediaPost

db = SessionLocal()
failed_posts = db.query(SocialMediaPost).filter(
    SocialMediaPost.status == 'failed',
    SocialMediaPost.platform == 'twitter'
).order_by(SocialMediaPost.created_at.desc()).limit(5).all()

print(f'Found {len(failed_posts)} recent failed Twitter publish(es)')
for post in failed_posts:
    print(f'  - Post {post.post_id}: {post.error_message}')

db.close()
"
    echo ""
fi

echo "========================================="
echo "Next Steps"
echo "========================================="

if [ $FAILED -gt 0 ]; then
    echo ""
    echo "Issues detected. Recommended actions:"
    echo ""
    echo "1. OAuth Configuration Issues:"
    echo "   - Check if Twitter app has write permissions enabled"
    echo "   - Verify OAuth credentials are correct in .env file"
    echo "   - Ensure user has valid Twitter connection"
    echo ""
    echo "2. Publisher Selection Issues:"
    echo "   - Verify posts_v2.py uses correct publisher for credential type"
    echo "   - Check if OAuth 1.0a credentials are properly stored"
    echo "   - Confirm refresh_token field is used for access_token_secret"
    echo ""
    echo "3. Error Handling Issues:"
    echo "   - Review posts_v2.py publish endpoint error handling"
    echo "   - Ensure exceptions are caught and recorded in database"
    echo "   - Verify success=false is returned on failures"
    echo ""
    echo "4. Database Consistency Issues:"
    echo "   - Check SocialMediaPost records match Post status"
    echo "   - Verify error_message field is populated on failures"
    echo "   - Ensure status is 'failed' not 'published' for failed posts"
    echo ""
else
    echo ""
    echo "All tests passed! Twitter publishing is working correctly."
    echo ""
    echo "Verified functionality:"
    echo "  ✓ OAuth 2.0 and OAuth 1.0a credential detection"
    echo "  ✓ Correct publisher class selection"
    echo "  ✓ Proper error handling for 403/401/429 errors"
    echo "  ✓ Database state consistency"
    echo "  ✓ Error message propagation to frontend"
    echo ""
fi

exit $TEST_EXIT_CODE
