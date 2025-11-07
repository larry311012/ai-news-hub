#!/bin/bash

echo "Starting AI News Aggregator Frontend..."
echo ""
echo "Frontend will be available at: http://localhost:8080"
echo "Make sure the backend is running on: http://localhost:8001"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python3 -m http.server 8080
