#!/bin/bash
# Redis Caching Layer - Quick Setup Script
#
# This script helps you set up Redis caching for the AI Post Generator

set -e  # Exit on error

echo "========================================="
echo "Redis Caching Layer - Quick Setup"
echo "========================================="
echo ""

# Detect OS
OS="$(uname -s)"
echo "Detected OS: $OS"
echo ""

# Check if Redis is installed
echo "Checking if Redis is installed..."
if command -v redis-server &> /dev/null; then
    echo "✓ Redis is already installed"
    REDIS_VERSION=$(redis-server --version | head -n 1)
    echo "  Version: $REDIS_VERSION"
else
    echo "✗ Redis is not installed"
    echo ""
    echo "Installing Redis..."

    case "$OS" in
        Darwin*)
            echo "Installing via Homebrew (macOS)..."
            if ! command -v brew &> /dev/null; then
                echo "Error: Homebrew is not installed. Please install from https://brew.sh/"
                exit 1
            fi
            brew install redis
            ;;
        Linux*)
            echo "Installing via apt (Linux)..."
            sudo apt-get update
            sudo apt-get install -y redis-server
            ;;
        *)
            echo "Unsupported OS: $OS"
            echo "Please install Redis manually: https://redis.io/download"
            exit 1
            ;;
    esac

    echo "✓ Redis installed successfully"
fi

echo ""
echo "========================================="
echo "Starting Redis Server"
echo "========================================="

# Check if Redis is already running
if redis-cli ping &> /dev/null; then
    echo "✓ Redis is already running"
else
    echo "Starting Redis server..."

    case "$OS" in
        Darwin*)
            # macOS - use brew services
            brew services start redis
            sleep 2
            ;;
        Linux*)
            # Linux - use systemctl
            sudo systemctl start redis-server
            sudo systemctl enable redis-server
            sleep 2
            ;;
    esac

    # Verify Redis started
    if redis-cli ping &> /dev/null; then
        echo "✓ Redis started successfully"
    else
        echo "✗ Failed to start Redis"
        echo "Please start Redis manually:"
        echo "  macOS: brew services start redis"
        echo "  Linux: sudo systemctl start redis-server"
        exit 1
    fi
fi

echo ""
echo "========================================="
echo "Testing Redis Connection"
echo "========================================="

# Test connection
echo "Testing Redis with PING command..."
REDIS_RESPONSE=$(redis-cli ping)

if [ "$REDIS_RESPONSE" = "PONG" ]; then
    echo "✓ Redis connection successful (PONG received)"
else
    echo "✗ Redis connection failed"
    echo "Response: $REDIS_RESPONSE"
    exit 1
fi

# Test basic operations
echo "Testing SET operation..."
redis-cli SET test_key "test_value" > /dev/null
echo "✓ SET successful"

echo "Testing GET operation..."
TEST_VALUE=$(redis-cli GET test_key)
if [ "$TEST_VALUE" = "test_value" ]; then
    echo "✓ GET successful (value: $TEST_VALUE)"
else
    echo "✗ GET failed"
    exit 1
fi

echo "Testing DEL operation..."
redis-cli DEL test_key > /dev/null
echo "✓ DEL successful"

echo ""
echo "========================================="
echo "Redis Info"
echo "========================================="

# Get Redis info
echo "Redis Server Info:"
redis-cli INFO SERVER | grep "redis_version\|os\|tcp_port" | sed 's/^/  /'

echo ""
echo "Memory Info:"
redis-cli INFO MEMORY | grep "used_memory_human\|maxmemory" | sed 's/^/  /'

echo ""
echo "========================================="
echo "Backend Configuration"
echo "========================================="

# Check if .env exists
if [ -f ".env" ]; then
    echo "✓ .env file exists"

    # Check if Redis config exists in .env
    if grep -q "REDIS_HOST" .env; then
        echo "✓ Redis configuration found in .env"
        echo ""
        echo "Current Redis configuration:"
        grep "REDIS_" .env | grep -v "^#" | sed 's/^/  /'
    else
        echo "⚠ Redis configuration not found in .env"
        echo ""
        echo "Adding Redis configuration to .env..."
        cat >> .env << 'EOF'

# Redis Caching Layer
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_SSL=false
REDIS_MAX_CONNECTIONS=50
CACHE_ENABLED=true
CACHE_DEBUG=false
EOF
        echo "✓ Redis configuration added to .env"
    fi
else
    echo "⚠ .env file not found"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "✓ .env file created"
    echo "⚠ Please edit .env and set your ENCRYPTION_KEY and other settings"
fi

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Redis caching is now configured and ready to use."
echo ""
echo "Next steps:"
echo "  1. Start the backend server:"
echo "     python main.py"
echo ""
echo "  2. Check cache health:"
echo "     curl http://localhost:8000/api/health/cache/stats"
echo ""
echo "  3. Monitor Redis:"
echo "     redis-cli MONITOR"
echo ""
echo "  4. View cache keys:"
echo "     redis-cli KEYS \"aipost:*\""
echo ""
echo "Documentation: See REDIS_CACHING_GUIDE.md for complete guide"
echo ""
echo "Happy caching! 🚀"
