#!/bin/bash
# Stop Backend Server

PID_FILE="/tmp/backend.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Stopping backend (PID: $PID)..."
        kill "$PID"
        rm "$PID_FILE"
        echo "Backend stopped."
    else
        echo "Backend not running (stale PID file)"
        rm "$PID_FILE"
    fi
else
    # Fallback: kill all uvicorn on port 8000
    PIDS=$(lsof -ti:8000)
    if [ -n "$PIDS" ]; then
        echo "Stopping backend processes on port 8000..."
        echo "$PIDS" | xargs kill
        echo "Backend stopped."
    else
        echo "Backend not running."
    fi
fi
