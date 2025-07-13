#!/bin/bash
# Run End-to-End Test V1: Pacific Ocean vs Volcano
# This script tests the semantic search precision

echo "🚀 Running End-to-End Test V1..."
echo "Testing Pacific Ocean vs Volcano semantic search precision"
echo ""

# Check if media search service is running
if ! curl -s http://localhost:5001/health > /dev/null 2>&1; then
    echo "❌ Media search service is not running on port 5001"
    echo "Please start the service first:"
    echo "  docker-compose up -d media_search"
    exit 1
fi

# Run the test
python test_e2e_v1.py --url http://localhost:5001

echo ""
echo "Test completed! Check the results above." 