#!/bin/bash
# Run End-to-End File CRUD Test V1: FAISS Synchronization
# This script tests that file deletions properly sync with FAISS indexes

echo "🚀 Running End-to-End File CRUD Test V1..."
echo "Testing FAISS synchronization with file CRUD operations"
echo ""

# Check if media search service is running
if ! curl -s http://localhost:5001/health > /dev/null 2>&1; then
    echo "❌ Media search service is not running on port 5001"
    echo "Please start the service first:"
    echo "  docker-compose up -d media_search"
    exit 1
fi

# Run the test
python test_e2e_file_crud_v1.py --url http://localhost:5001

echo ""
echo "CRUD test completed! Check the results above." 