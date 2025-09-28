#!/bin/bash

echo "🚀 Starting Quran Recitation Feedback API Server with uv..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Sync dependencies with uv (uses pyproject.toml)
echo "📚 Syncing dependencies with uv (lightning fast)..."
uv sync

# Ensure python-multipart is installed (required for FastAPI file uploads)
echo "📦 Installing python-multipart for file uploads..."
uv pip install python-multipart

# Start the API server
echo "🎯 Starting API server on http://localhost:8001"
echo "📖 API Documentation available at http://localhost:8001/docs"
echo "🔧 Interactive API testing at http://localhost:8001/redoc"
echo ""
echo "Press Ctrl+C to stop the server"

# Run the server with uv
uv run uvicorn src.surah_splitter.api.main:app --reload --host 0.0.0.0 --port 8001