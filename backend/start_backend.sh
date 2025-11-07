#!/bin/bash

# Start Backend Script with Proper Environment Loading
# This ensures .env file is loaded correctly

cd /Users/ranhui/ai_post/web/backend

echo "======================================================"
echo "Starting AI Post Generator Backend"
echo "======================================================"
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "ERROR: .env file not found!"
    exit 1
fi

echo "✓ .env file found"

# Load environment variables from .env
export $(grep -v '^#' .env | grep -v '^$' | xargs)

# Verify ENCRYPTION_KEY is loaded
if [ -z "$ENCRYPTION_KEY" ]; then
    echo "ERROR: ENCRYPTION_KEY not found in .env"
    exit 1
fi

echo "✓ ENCRYPTION_KEY loaded (${#ENCRYPTION_KEY} characters)"
echo ""

echo "Starting uvicorn server..."
echo "  Port: 8000"
echo "  Auto-reload: enabled"
echo "  Logs: backend.log"
echo ""

# Start uvicorn with loaded environment
nohup python3 -m uvicorn main:app --port 8000 --reload > backend.log 2>&1 &

SERVER_PID=$!
echo "✓ Server started with PID: $SERVER_PID"
echo ""

# Wait a moment for server to start
sleep 3

# Test if server is responding
if curl -s http://localhost:8000/docs > /dev/null; then
    echo "✓ Server is responding at http://localhost:8000"
    echo ""
    echo "======================================================"
    echo "Backend started successfully!"
    echo "======================================================"
    echo ""
    echo "Test API key decryption:"
    python3 << 'EOF'
import sqlite3
from utils.encryption import decrypt_value

conn = sqlite3.connect('ai_news.db')
cursor = conn.cursor()
cursor.execute('SELECT encrypted_key FROM user_api_keys WHERE user_id = 6 AND provider = "openai"')
row = cursor.fetchone()

if row:
    try:
        decrypted = decrypt_value(row[0])
        if decrypted and decrypted.startswith('sk-'):
            print('  ✓ API key decryption: SUCCESS')
        else:
            print('  ✗ API key decryption: FAILED')
    except Exception as e:
        print(f'  ✗ Decryption error: {e}')
conn.close()
EOF
else
    echo "✗ Server failed to start or is not responding"
    echo ""
    echo "Check backend.log for errors:"
    tail -20 backend.log
    exit 1
fi

echo ""
echo "To stop the server: pkill -f 'uvicorn main:app'"
echo "To view logs: tail -f backend.log"
echo ""
