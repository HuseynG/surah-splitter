#!/bin/bash

echo "🧪 Testing Quran Recitation API with uv..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Sync dependencies
echo "📚 Syncing dependencies..."
uv sync

# Run the test client
echo "🚀 Running API test client..."
uv run python src/surah_splitter/api/test_client.py