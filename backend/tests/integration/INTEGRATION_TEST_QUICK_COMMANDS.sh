#!/bin/bash
# Quick Reference: Integration Testing Commands
# Copy-paste these commands to test the Instagram image generation feature

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Instagram Integration Test Commands      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}\n"

# ============================================
# PRE-FLIGHT CHECKS
# ============================================

echo -e "${GREEN}1. PRE-FLIGHT CHECKS${NC}\n"

echo "Check if server is running:"
echo "  curl -s http://localhost:8000/api/health | jq"
echo ""

echo "Start server (if not running):"
echo "  cd /Users/ranhui/ai_post/web/backend"
echo "  python main.py"
echo ""

echo "Check database tables exist:"
echo "  sqlite3 ai_news.db \".tables\" | grep instagram"
echo ""

# ============================================
# QUICK INTEGRATION TEST
# ============================================

echo -e "${GREEN}2. QUICK INTEGRATION TEST (Shell Script)${NC}\n"

echo "Run complete frontend flow simulation:"
echo "  cd /Users/ranhui/ai_post/web/backend"
echo "  ./test_frontend_flow.sh"
echo ""

echo "Expected output:"
echo "  ${GREEN}✓ Server is running${NC}"
echo "  ${GREEN}✓ Authenticated successfully${NC}"
echo "  ${GREEN}✓ Using post ID: 30${NC}"
echo "  ${GREEN}✓ Quota status: 50/50 remaining${NC}"
echo "  ${GREEN}✓ Generation started${NC}"
echo "  ${GREEN}✓ Image generation completed!${NC}"
echo ""

# ============================================
# PERFORMANCE TESTS
# ============================================

echo -e "${GREEN}3. PERFORMANCE BENCHMARKS${NC}\n"

echo "Run all performance tests:"
echo "  cd /Users/ranhui/ai_post/web/backend"
echo "  python test_frontend_performance.py"
echo ""

echo "Expected results:"
echo "  Login: < 200ms"
echo "  Get Posts: < 300ms"
echo "  Check Quota: < 100ms"
echo "  Start Generation: < 500ms"
echo "  Status Check: < 100ms"
echo "  Get Image: < 200ms"
echo ""

# ============================================
# AUTOMATED TEST SUITE
# ============================================

echo -e "${GREEN}4. AUTOMATED TEST SUITE (Pytest)${NC}\n"

echo "Run all integration tests:"
echo "  cd /Users/ranhui/ai_post/web/backend"
echo "  pytest tests/test_frontend_integration_automated.py -v"
echo ""

echo "Run specific test:"
echo "  pytest tests/test_frontend_integration_automated.py::test_complete_frontend_flow -v"
echo ""

echo "Run with coverage:"
echo "  pytest tests/test_frontend_integration_automated.py --cov=api --cov=services --cov-report=html"
echo ""

# ============================================
# MANUAL API TESTING
# ============================================

echo -e "${GREEN}5. MANUAL API TESTING (cURL)${NC}\n"

echo "Test 1: Login"
echo '  curl -X POST http://localhost:8000/api/auth/login \'
echo '    -H "Content-Type: application/json" \'
echo '    -d '\''{"email":"testuser@example.com","password":"testpass123"}'\'' | jq'
echo ""

echo "Test 2: Get Posts"
echo '  TOKEN="your_token_here"'
echo '  curl -s http://localhost:8000/api/posts?limit=1 \'
echo '    -H "Authorization: Bearer $TOKEN" | jq'
echo ""

echo "Test 3: Check Quota"
echo '  curl -s http://localhost:8000/api/instagram/quota \'
echo '    -H "Authorization: Bearer $TOKEN" | jq'
echo ""

echo "Test 4: Generate Image"
echo '  POST_ID=30'
echo '  curl -X POST http://localhost:8000/api/posts/$POST_ID/generate-instagram-image \'
echo '    -H "Authorization: Bearer $TOKEN" \'
echo '    -H "Content-Type: application/json" \'
echo '    -d '\''{}'\'' | jq'
echo ""

echo "Test 5: Check Status"
echo '  JOB_ID="job_id_from_step4"'
echo '  curl -s http://localhost:8000/api/posts/$POST_ID/instagram-image/status?job_id=$JOB_ID \'
echo '    -H "Authorization: Bearer $TOKEN" | jq'
echo ""

echo "Test 6: Get Image"
echo '  curl -s http://localhost:8000/api/posts/$POST_ID/instagram-image \'
echo '    -H "Authorization: Bearer $TOKEN" | jq'
echo ""

# ============================================
# ERROR SCENARIO TESTING
# ============================================

echo -e "${GREEN}6. ERROR SCENARIO TESTS${NC}\n"

echo "Test unauthorized access:"
echo '  curl -X POST http://localhost:8000/api/posts/30/generate-instagram-image \'
echo '    -H "Content-Type: application/json" \'
echo '    -d '\''{}'\'' | jq'
echo "  Expected: 401 Unauthorized"
echo ""

echo "Test invalid post ID:"
echo '  curl -X POST http://localhost:8000/api/posts/999999/generate-instagram-image \'
echo '    -H "Authorization: Bearer $TOKEN" \'
echo '    -H "Content-Type: application/json" \'
echo '    -d '\''{}'\'' | jq'
echo "  Expected: 404 Not Found"
echo ""

echo "Test quota exceeded (run 51 times):"
echo '  for i in {1..51}; do'
echo '    curl -s -X POST http://localhost:8000/api/posts/30/generate-instagram-image \'
echo '      -H "Authorization: Bearer $TOKEN" \'
echo '      -H "Content-Type: application/json" \'
echo '      -d '\''{}'\'' | jq -r '\''.message'\'''
echo '  done'
echo "  Expected: 429 on 51st request"
echo ""

# ============================================
# DATABASE CHECKS
# ============================================

echo -e "${GREEN}7. DATABASE VERIFICATION${NC}\n"

echo "Check Instagram tables exist:"
echo "  sqlite3 ai_news.db"
echo "  > .tables"
echo "  > .schema instagram_images"
echo "  > .schema image_generation_quota"
echo ""

echo "Check data in tables:"
echo "  sqlite3 ai_news.db \"SELECT * FROM instagram_images;\""
echo "  sqlite3 ai_news.db \"SELECT * FROM image_generation_quota;\""
echo ""

echo "Count generated images:"
echo "  sqlite3 ai_news.db \"SELECT user_id, COUNT(*) as count FROM instagram_images GROUP BY user_id;\""
echo ""

# ============================================
# TROUBLESHOOTING
# ============================================

echo -e "${GREEN}8. TROUBLESHOOTING${NC}\n"

echo "Check server logs:"
echo "  tail -f /path/to/server.log"
echo ""

echo "Verify OpenAI API key:"
echo "  grep OPENAI_API_KEY .env"
echo ""

echo "Check image storage permissions:"
echo "  ls -la static/instagram_images/"
echo ""

echo "Reset quota for user:"
echo "  sqlite3 ai_news.db \"DELETE FROM image_generation_quota WHERE user_id=6;\""
echo ""

echo "Clear all Instagram data:"
echo "  sqlite3 ai_news.db \"DELETE FROM instagram_images;\""
echo "  sqlite3 ai_news.db \"DELETE FROM image_generation_quota;\""
echo ""

# ============================================
# PERFORMANCE MONITORING
# ============================================

echo -e "${GREEN}9. PERFORMANCE MONITORING${NC}\n"

echo "Monitor response times (real-time):"
echo '  while true; do'
echo '    TIME=$(curl -s -o /dev/null -w "%{time_total}" http://localhost:8000/api/health)'
echo '    echo "Health check: ${TIME}s"'
echo '    sleep 1'
echo '  done'
echo ""

echo "Load test with Apache Bench:"
echo "  ab -n 100 -c 10 -H \"Authorization: Bearer \$TOKEN\" http://localhost:8000/api/instagram/quota"
echo ""

echo "Monitor database size:"
echo "  watch -n 5 'ls -lh ai_news.db'"
echo ""

# ============================================
# CLEANUP
# ============================================

echo -e "${GREEN}10. CLEANUP${NC}\n"

echo "Stop server:"
echo "  pkill -f \"python main.py\""
echo ""

echo "Archive test results:"
echo "  tar -czf test_results_\$(date +%Y%m%d_%H%M%S).tar.gz *.log *.md"
echo ""

echo "Reset test database:"
echo "  rm ai_news.db"
echo "  python main.py  # Will recreate tables"
echo ""

# ============================================
# REPORTS
# ============================================

echo -e "${GREEN}11. VIEW REPORTS${NC}\n"

echo "Executive Summary:"
echo "  cat FRONTEND_INTEGRATION_EXECUTIVE_SUMMARY.md"
echo ""

echo "Comprehensive Report:"
echo "  cat FRONTEND_INTEGRATION_TEST_REPORT.md"
echo ""

echo "Quick stats:"
echo "  grep -E 'PASS|FAIL|BLOCKED' FRONTEND_INTEGRATION_TEST_REPORT.md | wc -l"
echo ""

# ============================================
# FOOTER
# ============================================

echo -e "${BLUE}════════════════════════════════════════════${NC}"
echo -e "${YELLOW}TIP: Copy these commands to your terminal${NC}"
echo -e "${YELLOW}All tests are in: /Users/ranhui/ai_post/web/backend/${NC}"
echo -e "${BLUE}════════════════════════════════════════════${NC}\n"
