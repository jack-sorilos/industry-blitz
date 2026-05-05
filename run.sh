#!/bin/bash
set -e
cd "$(dirname "$0")"

# Check for .env file
if [ ! -f .env ]; then
    echo "Error: .env file not found. Please create it with your ANTHROPIC_API_KEY."
    exit 1
fi

# Create virtual environment if needed
VENV_PYTHON="$(pwd)/.venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    echo "First-time setup: creating virtual environment..."
    /opt/homebrew/bin/python3.13 -m venv .venv
    .venv/bin/pip install -r requirements.txt --quiet
    echo "✓ Setup complete."
fi

# Load environment
if [ ! -f .env ]; then
    echo "Error: .env file not found."
    exit 1
fi

export $(cat .env | xargs)

# Launch
echo ""
echo "🚀 Starting Industry Blitz at http://localhost:5000"
echo "Press Ctrl+C to stop."
echo ""

# Verify token is set
if [ -z "$SHOPIFY_AI_PROXY_TOKEN" ]; then
    echo "Error: SHOPIFY_AI_PROXY_TOKEN not set. Check your .env file."
    exit 1
fi

# Open browser
sleep 1 && open "http://localhost:5000" &

# Run Flask with environment variables
SHOPIFY_AI_PROXY_TOKEN="$SHOPIFY_AI_PROXY_TOKEN" SF_ORG_ALIAS="$SF_ORG_ALIAS" SF_OWNER_ID="$SF_OWNER_ID" .venv/bin/flask --app app run --port 5000
