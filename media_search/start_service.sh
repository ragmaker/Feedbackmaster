#!/bin/bash
# Media Search Service Startup Script

echo "🚀 Starting Media Search Service..."
echo "=================================="

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose >/dev/null 2>&1; then
    echo "❌ docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

# Navigate to the parent directory (where docker-compose.yml is located)
cd "$(dirname "$0")/.."

echo "📦 Building and starting media_search service..."
docker-compose up --build media_search

echo "🎉 Media Search Service is now running!"
echo "   Service URL: http://localhost:5001"
echo "   Health Check: http://localhost:5001/health"
echo "   API Documentation: See README.md for API endpoints"
echo ""
echo "To run tests, use: python media_search/run_tests.py"
echo "To stop the service, press Ctrl+C" 