#!/bin/bash

# Unset problematic environment variables
unset COMPOSE_FILE
unset COMPOSE_PROFILES
unset COMPOSE_PROJECT_NAME

# Build and run with docker compose
echo "Building Docker image..."
docker compose build

echo "Starting application..."
docker compose up -d

echo "Application is running at http://localhost:8001"
echo "API docs: http://localhost:8001/docs"
echo "Demo: http://localhost:8001/demo"