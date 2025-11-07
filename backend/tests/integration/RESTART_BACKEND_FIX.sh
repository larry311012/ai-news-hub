#!/bin/bash
# Quick fix script to restart backend with proper environment

echo "========================================"
echo "Backend Restart Fix"
echo "========================================"
echo ""
echo "Issue: Backend not loading ENCRYPTION_KEY from .env"
echo "Solution: Restart uvicorn to reload environment"
echo ""

# Stop existing backend
echo "Step 1: Stopping existing backend..."
pkill -f "uvicorn main:app"
sleep 2

# Verify it's stopped
if pgrep -f "uvicorn main:app" > /dev/null; then
    echo "ERROR: Backend still running. Trying force kill..."
    pkill -9 -f "uvicorn main:app"
    sleep 1
fi

echo "Step 2: Verifying .env file..."
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found in current directory!"
    echo "Make sure you're in /Users/ranhui/ai_post/web/backend"
    exit 1
fi

if ! grep -q "ENCRYPTION_KEY" .env; then
    echo "ERROR: ENCRYPTION_KEY not found in .env!"
    exit 1
fi

echo "✓ .env file found with ENCRYPTION_KEY"

echo ""
echo "Step 3: Starting backend with fresh environment..."
echo "Running: python -m uvicorn main:app --port 8000 --reload"
echo ""
echo "Backend will start in foreground. To run in background, use:"
echo "  nohup python -m uvicorn main:app --port 8000 --reload > backend.log 2>&1 &"
echo ""
echo "Press Ctrl+C to cancel, or wait 5 seconds to start..."
sleep 5

# Start backend
cd /Users/ranhui/ai_post/web/backend
python -m uvicorn main:app --port 8000 --reload
