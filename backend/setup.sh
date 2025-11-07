#!/bin/bash
set -e  # Exit on error

echo "========================================================================"
echo "  AI Post Generator - Backend Setup"
echo "========================================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check Python version
echo -e "${BLUE}Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | awk '{print $2}')
python_major=$(echo $python_version | cut -d. -f1)
python_minor=$(echo $python_version | cut -d. -f2)

echo "Python version: $python_version"

if [ "$python_major" -lt 3 ] || ([ "$python_major" -eq 3 ] && [ "$python_minor" -lt 8 ]); then
    echo -e "${RED}ERROR: Python 3.8 or higher is required${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python version OK${NC}"
echo ""

# Install dependencies
echo -e "${BLUE}Installing dependencies...${NC}"
pip3 install -r requirements.txt --upgrade
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file from example...${NC}"
    cp .env.example .env

    # Generate encryption key
    echo -e "${BLUE}Generating ENCRYPTION_KEY...${NC}"
    encryption_key=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

    # Update .env file with generated key
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|ENCRYPTION_KEY=your-encryption-key-here|ENCRYPTION_KEY=$encryption_key|" .env
    else
        # Linux
        sed -i "s|ENCRYPTION_KEY=your-encryption-key-here|ENCRYPTION_KEY=$encryption_key|" .env
    fi

    echo -e "${GREEN}✓ Generated ENCRYPTION_KEY and saved to .env${NC}"
    echo ""
    echo -e "${YELLOW}IMPORTANT: If you need OAuth or email features:${NC}"
    echo "  1. Edit .env file"
    echo "  2. Add your OAuth credentials (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)"
    echo "  3. Configure email settings (EMAIL_MODE, SENDGRID_API_KEY or SMTP settings)"
    echo ""
else
    echo -e "${GREEN}✓ .env file already exists${NC}"

    # Check if ENCRYPTION_KEY is set
    if grep -q "ENCRYPTION_KEY=your-encryption-key-here" .env 2>/dev/null; then
        echo -e "${YELLOW}WARNING: ENCRYPTION_KEY still has default value${NC}"
        echo "Generating a new key..."
        encryption_key=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

        if [[ "$OSTYPE" == "darwin"* ]]; then
            sed -i '' "s|ENCRYPTION_KEY=your-encryption-key-here|ENCRYPTION_KEY=$encryption_key|" .env
        else
            sed -i "s|ENCRYPTION_KEY=your-encryption-key-here|ENCRYPTION_KEY=$encryption_key|" .env
        fi

        echo -e "${GREEN}✓ Updated ENCRYPTION_KEY${NC}"
    fi
    echo ""
fi

# Check if database exists
if [ -f ai_news.db ]; then
    echo -e "${GREEN}✓ Database already exists${NC}"
    echo ""
    read -p "Do you want to run migrations anyway? (y/N): " run_migrations
    if [[ ! $run_migrations =~ ^[Yy]$ ]]; then
        echo "Skipping migrations..."
        skip_migrations=true
    fi
else
    echo -e "${YELLOW}Database not found. Will create and run migrations...${NC}"
    skip_migrations=false
fi

# Run migrations
if [ "$skip_migrations" != true ]; then
    echo ""
    echo -e "${BLUE}Running database migrations...${NC}"

    if [ -f migrate_phase2.py ]; then
        echo "Running Phase 2 migration..."
        python3 migrate_phase2.py
    fi

    if [ -f migrate_phase3.py ]; then
        echo "Running Phase 3 migration..."
        python3 migrate_phase3.py
    fi

    if [ -f migrate_phase4.py ]; then
        echo "Running Phase 4 migration..."
        python3 migrate_phase4.py
    fi

    echo -e "${GREEN}✓ Database migrations complete${NC}"
    echo ""
fi

# Verify setup
echo -e "${BLUE}Verifying setup...${NC}"
if [ -f verify_imports.py ]; then
    python3 verify_imports.py
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ All imports verified${NC}"
    else
        echo -e "${YELLOW}⚠ Some optional imports missing (this is OK for development)${NC}"
    fi
else
    echo -e "${YELLOW}⚠ verify_imports.py not found, skipping verification${NC}"
fi

echo ""
echo "========================================================================"
echo -e "${GREEN}  Setup Complete!${NC}"
echo "========================================================================"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""
echo "  1. Review your .env file configuration:"
echo "     nano .env"
echo ""
echo "  2. Start the backend server:"
echo "     python3 main.py"
echo "     or"
echo "     ./start.sh"
echo ""
echo "  3. Run tests to verify everything works:"
echo "     ./run_all_tests.sh"
echo ""
echo -e "${BLUE}API Documentation:${NC}"
echo "  Once server is running, visit:"
echo "  http://localhost:8001/docs"
echo ""
echo -e "${BLUE}Troubleshooting:${NC}"
echo "  - Check logs: tail -f backend.log"
echo "  - Verify imports: python3 verify_imports.py"
echo "  - Reset database: rm ai_news.db && ./setup.sh"
echo ""
echo "========================================================================"
