#!/bin/bash

echo "🚀 Starting Quran Recitation API Demo"
echo "=" * 50

# Kill any existing processes on port 8001
echo "🧹 Cleaning up port 8001..."
lsof -ti:8001 | xargs kill -9 2>/dev/null

# Start the API server
echo "🎯 Starting API server..."
./start_api_server.sh &
API_PID=$!

# Wait for server to start
echo "⏳ Waiting for server to start..."
sleep 5

# Check if server is running
if curl -s http://localhost:8001/health > /dev/null; then
    echo "✅ API server is running!"
    echo ""
    echo "📱 Access the demo at:"
    echo "   👉 http://localhost:8001/ (Full API Demo)"
    echo "   📖 http://localhost:8001/docs (API Documentation)"
    echo "   🔧 http://localhost:8001/redoc (Alternative Docs)"
    echo ""
    echo "Press Ctrl+C to stop the demo"

    # Keep script running
    wait $API_PID
else
    echo "❌ Failed to start API server"
    exit 1
fi