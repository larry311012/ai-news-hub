#!/bin/bash

# Performance Testing Script for Phase 2 Authentication APIs
# Measures response times, throughput, and resource usage

BASE_URL="http://localhost:8001"
API_URL="$BASE_URL/api"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Check dependencies
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is required${NC}"
    exit 1
fi

if ! command -v bc &> /dev/null; then
    echo -e "${RED}Error: bc is required (brew install bc)${NC}"
    exit 1
fi

# Check server
if ! curl -s "$BASE_URL/health" > /dev/null 2>&1; then
    echo -e "${RED}Error: Server not running at $BASE_URL${NC}"
    exit 1
fi

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}PHASE 2 PERFORMANCE TESTS${NC}"
echo -e "${CYAN}========================================${NC}"
echo "Test Date: $(date)"
echo "Base URL: $BASE_URL"
echo ""

# Create test user
RANDOM_ID=$RANDOM
TEST_EMAIL="perf${RANDOM_ID}@example.com"
TEST_PASSWORD="perftest123"

echo -e "${YELLOW}Setting up test user...${NC}"
REGISTER=$(curl -s -X POST "$API_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$TEST_EMAIL\",
    \"password\": \"$TEST_PASSWORD\",
    \"full_name\": \"Performance Test User\"
  }")

LOGIN=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$TEST_EMAIL\",
    \"password\": \"$TEST_PASSWORD\",
    \"remember_me\": false
  }")

TOKEN=$(echo "$LOGIN" | jq -r '.token' 2>/dev/null)

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo -e "${RED}Failed to setup test user${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Test user ready${NC}"
echo ""

# ============================================
# TEST 1: Profile Retrieval Performance
# ============================================
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Test 1: Profile Retrieval Performance${NC}"
echo -e "${CYAN}========================================${NC}"

REQUESTS=100
echo "Running $REQUESTS sequential requests..."

START=$(date +%s%3N)
FAILED=0
for i in $(seq 1 $REQUESTS); do
    RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$API_URL/auth/profile" \
      -H "Authorization: Bearer $TOKEN")
    STATUS=$(echo "$RESPONSE" | tail -n 1)
    if [ "$STATUS" != "200" ]; then
        FAILED=$((FAILED + 1))
    fi
done
END=$(date +%s%3N)

DURATION=$((END - START))
AVG=$((DURATION / REQUESTS))
RPS=$(echo "scale=2; $REQUESTS / ($DURATION / 1000)" | bc)

echo ""
echo -e "${GREEN}Results:${NC}"
echo "  Total requests: $REQUESTS"
echo "  Failed requests: $FAILED"
echo "  Total time: ${DURATION}ms"
echo "  Average response time: ${AVG}ms"
echo "  Requests per second: $RPS"
echo ""

if [ $AVG -lt 100 ]; then
    echo -e "${GREEN}✓ EXCELLENT: <100ms average${NC}"
elif [ $AVG -lt 500 ]; then
    echo -e "${YELLOW}✓ GOOD: <500ms average${NC}"
else
    echo -e "${RED}⚠ NEEDS OPTIMIZATION: ${AVG}ms average${NC}"
fi

# ============================================
# TEST 2: Profile Update Performance
# ============================================
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Test 2: Profile Update Performance${NC}"
echo -e "${CYAN}========================================${NC}"

REQUESTS=50
echo "Running $REQUESTS sequential updates..."

START=$(date +%s%3N)
FAILED=0
for i in $(seq 1 $REQUESTS); do
    RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT "$API_URL/auth/profile" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"full_name\": \"Test User $i\"}")
    STATUS=$(echo "$RESPONSE" | tail -n 1)
    if [ "$STATUS" != "200" ]; then
        FAILED=$((FAILED + 1))
    fi
done
END=$(date +%s%3N)

DURATION=$((END - START))
AVG=$((DURATION / REQUESTS))
RPS=$(echo "scale=2; $REQUESTS / ($DURATION / 1000)" | bc)

echo ""
echo -e "${GREEN}Results:${NC}"
echo "  Total requests: $REQUESTS"
echo "  Failed requests: $FAILED"
echo "  Total time: ${DURATION}ms"
echo "  Average response time: ${AVG}ms"
echo "  Requests per second: $RPS"
echo ""

if [ $AVG -lt 200 ]; then
    echo -e "${GREEN}✓ EXCELLENT: <200ms average${NC}"
elif [ $AVG -lt 1000 ]; then
    echo -e "${YELLOW}✓ GOOD: <1000ms average${NC}"
else
    echo -e "${RED}⚠ NEEDS OPTIMIZATION: ${AVG}ms average${NC}"
fi

# ============================================
# TEST 3: Concurrent Request Handling
# ============================================
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Test 3: Concurrent Request Handling${NC}"
echo -e "${CYAN}========================================${NC}"

CONCURRENT=20
echo "Running $CONCURRENT concurrent profile requests..."

START=$(date +%s%3N)
for i in $(seq 1 $CONCURRENT); do
    curl -s -X GET "$API_URL/auth/profile" \
      -H "Authorization: Bearer $TOKEN" > /dev/null &
done
wait
END=$(date +%s%3N)

DURATION=$((END - START))
AVG=$((DURATION / CONCURRENT))

echo ""
echo -e "${GREEN}Results:${NC}"
echo "  Concurrent requests: $CONCURRENT"
echo "  Total time: ${DURATION}ms"
echo "  Average time: ${AVG}ms"
echo ""

if [ $DURATION -lt 1000 ]; then
    echo -e "${GREEN}✓ EXCELLENT: <1s for $CONCURRENT concurrent requests${NC}"
elif [ $DURATION -lt 5000 ]; then
    echo -e "${YELLOW}✓ GOOD: <5s for $CONCURRENT concurrent requests${NC}"
else
    echo -e "${RED}⚠ NEEDS OPTIMIZATION: ${DURATION}ms for $CONCURRENT requests${NC}"
fi

# ============================================
# TEST 4: API Key Operations Performance
# ============================================
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Test 4: API Key Operations Performance${NC}"
echo -e "${CYAN}========================================${NC}"

echo "Testing API key save operations..."
SAVE_TIMES=()
for i in {1..10}; do
    START=$(date +%s%3N)
    curl -s -X POST "$API_URL/auth/api-keys" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"provider\": \"test-provider-$i\",
        \"api_key\": \"sk-test-key-$i-$(date +%s)\"
      }" > /dev/null
    END=$(date +%s%3N)
    SAVE_TIMES+=($((END - START)))
done

# Calculate average save time
TOTAL_SAVE=0
for time in "${SAVE_TIMES[@]}"; do
    TOTAL_SAVE=$((TOTAL_SAVE + time))
done
AVG_SAVE=$((TOTAL_SAVE / 10))

echo "Testing API key list operations..."
LIST_TIMES=()
for i in {1..20}; do
    START=$(date +%s%3N)
    curl -s -X GET "$API_URL/auth/api-keys" \
      -H "Authorization: Bearer $TOKEN" > /dev/null
    END=$(date +%s%3N)
    LIST_TIMES+=($((END - START)))
done

# Calculate average list time
TOTAL_LIST=0
for time in "${LIST_TIMES[@]}"; do
    TOTAL_LIST=$((TOTAL_LIST + time))
done
AVG_LIST=$((TOTAL_LIST / 20))

echo ""
echo -e "${GREEN}Results:${NC}"
echo "  Average save time: ${AVG_SAVE}ms"
echo "  Average list time (10 keys): ${AVG_LIST}ms"
echo ""

if [ $AVG_SAVE -lt 200 ] && [ $AVG_LIST -lt 200 ]; then
    echo -e "${GREEN}✓ EXCELLENT: Fast encryption/decryption${NC}"
elif [ $AVG_SAVE -lt 500 ] && [ $AVG_LIST -lt 500 ]; then
    echo -e "${YELLOW}✓ GOOD: Acceptable performance${NC}"
else
    echo -e "${RED}⚠ NEEDS OPTIMIZATION: Slow encryption operations${NC}"
fi

# ============================================
# TEST 5: Password Change Performance
# ============================================
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Test 5: Password Change Performance${NC}"
echo -e "${CYAN}========================================${NC}"

echo "Testing password change operation..."

CHANGE_TIMES=()
CURRENT_PASS="$TEST_PASSWORD"
for i in {1..5}; do
    NEW_PASS="testpass${i}${RANDOM}"
    START=$(date +%s%3N)
    curl -s -X PUT "$API_URL/auth/password" \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{
        \"current_password\": \"$CURRENT_PASS\",
        \"new_password\": \"$NEW_PASS\"
      }" > /dev/null
    END=$(date +%s%3N)
    CHANGE_TIMES+=($((END - START)))
    CURRENT_PASS="$NEW_PASS"

    # Re-login to get new token
    LOGIN=$(curl -s -X POST "$API_URL/auth/login" \
      -H "Content-Type: application/json" \
      -d "{
        \"email\": \"$TEST_EMAIL\",
        \"password\": \"$CURRENT_PASS\",
        \"remember_me\": false
      }")
    TOKEN=$(echo "$LOGIN" | jq -r '.token' 2>/dev/null)
done

# Calculate average
TOTAL_CHANGE=0
for time in "${CHANGE_TIMES[@]}"; do
    TOTAL_CHANGE=$((TOTAL_CHANGE + time))
done
AVG_CHANGE=$((TOTAL_CHANGE / 5))

echo ""
echo -e "${GREEN}Results:${NC}"
echo "  Average password change time: ${AVG_CHANGE}ms"
echo ""

if [ $AVG_CHANGE -lt 500 ]; then
    echo -e "${GREEN}✓ EXCELLENT: <500ms average${NC}"
elif [ $AVG_CHANGE -lt 2000 ]; then
    echo -e "${YELLOW}✓ GOOD: <2s average${NC}"
else
    echo -e "${RED}⚠ SLOW: ${AVG_CHANGE}ms (bcrypt hashing is expensive)${NC}"
fi

# ============================================
# TEST 6: Load Test - Sustained Throughput
# ============================================
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Test 6: Load Test - Sustained Throughput${NC}"
echo -e "${CYAN}========================================${NC}"

DURATION_SECONDS=10
echo "Running sustained load for ${DURATION_SECONDS} seconds..."

COUNT=0
FAILED=0
START=$(date +%s)
END_TARGET=$((START + DURATION_SECONDS))

while [ $(date +%s) -lt $END_TARGET ]; do
    RESPONSE=$(curl -s -w "\n%{http_code}" -X GET "$API_URL/auth/profile" \
      -H "Authorization: Bearer $TOKEN")
    STATUS=$(echo "$RESPONSE" | tail -n 1)
    if [ "$STATUS" = "200" ]; then
        COUNT=$((COUNT + 1))
    else
        FAILED=$((FAILED + 1))
    fi
done

ACTUAL_DURATION=$(($(date +%s) - START))
RPS=$(echo "scale=2; $COUNT / $ACTUAL_DURATION" | bc)
ERROR_RATE=$(echo "scale=2; ($FAILED / ($COUNT + $FAILED)) * 100" | bc)

echo ""
echo -e "${GREEN}Results:${NC}"
echo "  Duration: ${ACTUAL_DURATION}s"
echo "  Successful requests: $COUNT"
echo "  Failed requests: $FAILED"
echo "  Requests per second: $RPS"
echo "  Error rate: ${ERROR_RATE}%"
echo ""

if [ $FAILED -eq 0 ] && (( $(echo "$RPS > 50" | bc -l) )); then
    echo -e "${GREEN}✓ EXCELLENT: High throughput, no errors${NC}"
elif [ $FAILED -lt 5 ] && (( $(echo "$RPS > 20" | bc -l) )); then
    echo -e "${YELLOW}✓ GOOD: Acceptable performance${NC}"
else
    echo -e "${RED}⚠ NEEDS ATTENTION: Low throughput or high error rate${NC}"
fi

# ============================================
# TEST 7: Stress Test - Finding Breaking Point
# ============================================
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Test 7: Stress Test - Concurrent Users${NC}"
echo -e "${CYAN}========================================${NC}"

echo "Testing with increasing concurrent load..."

for CONCURRENT in 10 25 50 100; do
    echo ""
    echo -e "${YELLOW}Testing with $CONCURRENT concurrent requests...${NC}"

    START=$(date +%s%3N)
    PIDS=()
    for i in $(seq 1 $CONCURRENT); do
        curl -s -X GET "$API_URL/auth/profile" \
          -H "Authorization: Bearer $TOKEN" > /dev/null &
        PIDS+=($!)
    done

    # Wait for all to complete
    for pid in "${PIDS[@]}"; do
        wait $pid
    done

    END=$(date +%s%3N)
    DURATION=$((END - START))
    AVG=$((DURATION / CONCURRENT))

    echo "  Total time: ${DURATION}ms"
    echo "  Average per request: ${AVG}ms"

    if [ $DURATION -gt 10000 ]; then
        echo -e "  ${RED}⚠ Breaking point: System struggling at $CONCURRENT concurrent users${NC}"
        break
    elif [ $DURATION -gt 5000 ]; then
        echo -e "  ${YELLOW}⚠ Performance degrading at $CONCURRENT concurrent users${NC}"
    else
        echo -e "  ${GREEN}✓ Handling $CONCURRENT concurrent users well${NC}"
    fi
done

# ============================================
# TEST SUMMARY
# ============================================
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}PERFORMANCE TEST SUMMARY${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

echo -e "${BLUE}Benchmarks:${NC}"
echo "  Profile GET: Target <100ms avg, <1000 RPS"
echo "  Profile PUT: Target <200ms avg, >100 RPS"
echo "  API Keys: Target <200ms for save/list operations"
echo "  Password Change: Target <500ms (bcrypt is expensive)"
echo "  Concurrent: Handle 50+ concurrent users gracefully"
echo ""

echo -e "${GREEN}Recommendations:${NC}"
echo "  1. Add caching for frequently accessed profile data"
echo "  2. Consider connection pooling for database operations"
echo "  3. Monitor bcrypt rounds (currently 12, may adjust for speed)"
echo "  4. Add rate limiting to prevent abuse"
echo "  5. Consider async operations for non-critical updates"
echo "  6. Add API response compression (gzip)"
echo "  7. Implement database indexes on frequently queried fields"
echo ""

echo -e "${YELLOW}Cleanup:${NC}"
curl -s -X POST "$API_URL/auth/logout" \
  -H "Authorization: Bearer $TOKEN" > /dev/null
echo "✓ Test user cleaned up"
echo ""

echo -e "${GREEN}Performance testing complete!${NC}"
