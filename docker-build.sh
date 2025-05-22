#!/bin/bash

# Create required directories if they don't exist
mkdir -p uploads
mkdir -p nginx

# Copy the nginx configuration to the nginx directory
cp nginx/nginx.conf nginx/

# Export OpenAI API key if provided
if [ -n "$1" ]; then
  export OPENAI_API_KEY=$1
fi

# Stop and remove existing containers
docker-compose down

# Build and start the services
docker-compose up --build -d

echo "Services started. Access the application at http://localhost:7080" 