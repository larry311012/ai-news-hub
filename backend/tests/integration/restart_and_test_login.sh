#!/bin/bash

# Quick Fix: Restart Backend and Test Login
# This script restarts the backend to clear in-memory rate limits and tests the login flow

set -e  # Exit on error

echo "=========================================="
echo "Backend Restart and Login Test"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Find and kill existing backend process
echo "Step 1: Stopping existing backend..."
PID=$(lsof -ti:8000 || echo "")
if [ -n "$PID" ]; then
    echo "  Found backend process: PID $PID"
    kill -9 $PID
    echo -e "  ${GREEN}✓ Backend stopped${NC}"
    sleep 2
else
    echo -e "  ${YELLOW}⚠ No backend process found on port 8000${NC}"
fi

# Step 2: Start backend in background
echo ""
echo "Step 2: Starting backend..."
cd /Users/ranhui/ai_post/web/backend

# Check if uvicorn is available
if ! command -v uvicorn &> /dev/null; then
    echo -e "  ${RED}✗ uvicorn not found. Please install: pip install uvicorn${NC}"
    exit 1
fi

# Start backend in background
nohup uvicorn main:app --reload --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!
echo "  Backend started with PID: $BACKEND_PID"
echo "  Waiting for backend to be ready..."
sleep 5

# Step 3: Test health endpoint
echo ""
echo "Step 3: Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo -e "  ${GREEN}✓ Backend is healthy${NC}"
    echo "  Response: $HEALTH_RESPONSE"
else
    echo -e "  ${RED}✗ Backend health check failed${NC}"
    echo "  Response: $HEALTH_RESPONSE"
    exit 1
fi

# Step 4: Test CORS preflight
echo ""
echo "Step 4: Testing CORS preflight (OPTIONS)..."
CORS_RESPONSE=$(curl -s -X OPTIONS http://localhost:8000/api/auth/login \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -w "\nHTTP_STATUS:%{http_code}" -o /dev/null)

HTTP_STATUS=$(echo "$CORS_RESPONSE" | grep HTTP_STATUS | cut -d: -f2)
if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "204" ]; then
    echo -e "  ${GREEN}✓ CORS preflight successful (HTTP $HTTP_STATUS)${NC}"
else
    echo -e "  ${RED}✗ CORS preflight failed (HTTP $HTTP_STATUS)${NC}"
    if [ "$HTTP_STATUS" = "429" ]; then
        echo -e "  ${YELLOW}⚠ Rate limit still active. Wait a few minutes or check slowapi storage.${NC}"
    fi
fi

# Step 5: Test login endpoint
echo ""
echo "Step 5: Testing login endpoint..."
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3000" \
  -d '{"email":"test@example.com","password":"wrongpassword"}' \
  -w "\nHTTP_STATUS:%{http_code}")

echo "$LOGIN_RESPONSE" | grep -v HTTP_STATUS
HTTP_STATUS=$(echo "$LOGIN_RESPONSE" | grep HTTP_STATUS | cut -d: -f2)

if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "401" ]; then
    echo -e "  ${GREEN}✓ Login endpoint accessible (HTTP $HTTP_STATUS)${NC}"
    if [ "$HTTP_STATUS" = "401" ]; then
        echo -e "  ${GREEN}  Expected: Invalid credentials${NC}"
    fi
elif [ "$HTTP_STATUS" = "429" ]; then
    echo -e "  ${RED}✗ Rate limit still active (HTTP $HTTP_STATUS)${NC}"
    echo -e "  ${YELLOW}  This means slowapi's in-memory storage was not cleared by restart.${NC}"
    echo -e "  ${YELLOW}  Recommendation: Implement Redis-based rate limiting or wait for rate limit to expire.${NC}"
else
    echo -e "  ${YELLOW}⚠ Unexpected status code: HTTP $HTTP_STATUS${NC}"
fi

# Step 6: Check CORS headers
echo ""
echo "Step 6: Checking CORS headers..."
CORS_HEADERS=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -H "Origin: http://localhost:3000" \
  -d '{"email":"test@example.com","password":"test"}' \
  -v 2>&1 | grep -i "access-control")

if echo "$CORS_HEADERS" | grep -q "access-control-allow-origin"; then
    echo -e "  ${GREEN}✓ CORS headers present${NC}"
    echo "$CORS_HEADERS" | sed 's/^/    /'
else
    echo -e "  ${RED}✗ CORS headers missing${NC}"
    echo -e "  ${YELLOW}  This might indicate rate limiting is blocking the request${NC}"
fi

# Summary
echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo ""
echo "Backend PID: $BACKEND_PID"
echo "Backend logs: /Users/ranhui/ai_post/web/backend/backend.log"
echo ""
echo "Next steps:"
echo "  1. If rate limit is still active, wait for it to expire (~3-15 minutes)"
echo "  2. Or implement Redis-based rate limiting for better control"
echo "  3. Or add development-mode bypass for localhost requests"
echo ""
echo "To stop backend:"
echo "  kill $BACKEND_PID"
echo ""
echo "To view backend logs:"
echo "  tail -f /Users/ranhui/ai_post/web/backend/backend.log"
echo ""
