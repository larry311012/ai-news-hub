#!/bin/bash

echo "Starting AI News Aggregator Backend..."
echo ""

# Check if venv exists in parent directory
if [ ! -d "../../venv" ]; then
    echo "Error: Virtual environment not found"
    echo "Please run from the project root: python3 -m venv venv"
    exit 1
fi

# Activate venv
source ../../venv/bin/activate

# Install backend dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Set PYTHONPATH to include parent directories
export PYTHONPATH="${PYTHONPATH}:../..:."

# Run the server
echo ""
echo "Backend API starting on http://localhost:8000"
echo "API documentation: http://localhost:8000/docs"
echo ""

python main.py
