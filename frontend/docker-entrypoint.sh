#!/bin/sh
# ============================================================================
# Docker Entrypoint Script for Frontend
# ============================================================================
# Injects runtime environment variables into built JavaScript files
# This allows configuration without rebuilding the Docker image
# ============================================================================

set -e

# Default values if not provided
VITE_API_URL="${VITE_API_URL:-http://localhost:8000}"
VITE_APP_ENV="${VITE_APP_ENV:-production}"

echo "Configuring frontend with runtime environment variables..."
echo "API URL: $VITE_API_URL"
echo "Environment: $VITE_APP_ENV"

# Find all JavaScript files in the dist directory and replace placeholder
# This works because Vite bundles create static strings we can replace
find /usr/share/nginx/html -type f -name "*.js" -exec sed -i \
    -e "s|__VITE_API_URL__|$VITE_API_URL|g" \
    -e "s|__VITE_APP_ENV__|$VITE_APP_ENV|g" \
    {} +

echo "Frontend configuration complete!"

# Execute the main command (nginx)
exec "$@"
