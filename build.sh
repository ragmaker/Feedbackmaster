#!/bin/bash

# Make the script executable
chmod +x build.sh

# Build and start the containers
echo "Building and starting Docker containers..."
docker-compose up --build -d

# Wait for the application to start
echo "Waiting for the application to start..."
sleep 5

# Check if the container is running
if [ "$(docker-compose ps -q web)" ]; then
    echo "Application is running at http://localhost:8081"
else
    echo "Error: Application failed to start"
    exit 1
fi 