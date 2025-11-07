#!/bin/bash
# Start Backend for iOS Development
# This script starts the backend server with proper configuration for iOS app access

set -e

BACKEND_DIR="/Users/ranhui/ai_post/ai-news-hub-web/backend"
LOG_FILE="/tmp/backend.log"
PID_FILE="/tmp/backend.pid"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Starting Backend for iOS Development ===${NC}"
echo ""

# Check if backend is already running
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        echo -e "${YELLOW}Backend already running with PID: $OLD_PID${NC}"
        echo "Stop it first with: kill $OLD_PID"
        exit 1
    else
        rm "$PID_FILE"
    fi
fi

# Change to backend directory
cd "$BACKEND_DIR" || exit 1

# Activate virtual environment if it exists
if [ -d "/Users/ranhui/ai_post/venv" ]; then
    source "/Users/ranhui/ai_post/venv/bin/activate"
    echo -e "${GREEN}✓${NC} Virtual environment activated"
fi

# Get local IP address
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}')

# Start backend
echo -e "${GREEN}Starting backend server...${NC}"
echo "  Directory: $BACKEND_DIR"
echo "  Port: 8000"
echo "  Binding: 0.0.0.0 (all interfaces)"
echo "  Local IP: $LOCAL_IP"
echo "  Log file: $LOG_FILE"
echo ""

# Start uvicorn in background
nohup uvicorn main:app --reload --port 8000 --host 0.0.0.0 > "$LOG_FILE" 2>&1 &
BACKEND_PID=$!

# Save PID
echo "$BACKEND_PID" > "$PID_FILE"

# Wait for startup
echo "Waiting for backend to start..."
sleep 3

# Check if process is still running
if ps -p "$BACKEND_PID" > /dev/null 2>&1; then
    # Test health endpoint
    HEALTH_CHECK=$(curl -s http://localhost:8000/api/health 2>/dev/null | grep -c "healthy" || echo "0")

    if [ "$HEALTH_CHECK" -eq "1" ]; then
        echo -e "${GREEN}✓ Backend started successfully!${NC}"
        echo ""
        echo "Backend Information:"
        echo "  PID: $BACKEND_PID"
        echo "  Status: RUNNING"
        echo ""
        echo "Access URLs:"
        echo "  Local:   http://localhost:8000"
        echo "  Network: http://$LOCAL_IP:8000"
        echo "  API:     http://$LOCAL_IP:8000/api"
        echo "  Docs:    http://$LOCAL_IP:8000/docs"
        echo ""
        echo "iOS App Configuration:"
        echo "  Base URL: http://$LOCAL_IP:8000"
        echo "  Endpoint: /api/articles/recent"
        echo ""
        echo "Monitoring:"
        echo "  View logs: tail -f $LOG_FILE"
        echo "  Stop backend: kill $BACKEND_PID"
        echo "  Check status: ps -p $BACKEND_PID"
        echo ""

        # Test articles endpoint
        ARTICLES_COUNT=$(curl -s "http://localhost:8000/api/articles/recent?limit=1" 2>/dev/null | python3 -c "import json, sys; data=json.load(sys.stdin); print(len(data.get('articles', [])))" 2>/dev/null || echo "0")
        echo "Quick Test:"
        echo "  Articles endpoint: ${GREEN}✓${NC} ($ARTICLES_COUNT articles available)"

    else
        echo -e "${RED}✗ Backend started but health check failed${NC}"
        echo "Check logs: tail -f $LOG_FILE"
        exit 1
    fi
else
    echo -e "${RED}✗ Backend failed to start${NC}"
    echo "Check logs: tail -f $LOG_FILE"
    exit 1
fi

echo ""
echo -e "${GREEN}Backend is ready for iOS development!${NC}"
