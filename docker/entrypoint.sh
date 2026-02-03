#!/bin/bash
# Content Core Docker Entrypoint
# Handles first-run setup for components that need persistent storage

set -e

# Install Playwright browsers if Crawl4AI is available and browsers aren't installed
if python -c "import crawl4ai" 2>/dev/null; then
    # Check if chromium directory exists (any version)
    if ! ls "$PLAYWRIGHT_BROWSERS_PATH"/chromium-* 1>/dev/null 2>&1; then
        echo "Installing Playwright browsers for Crawl4AI (first run)..."
        playwright install chromium
        echo "Playwright browsers installed."
    fi
fi

# Execute the main command
exec "$@"
