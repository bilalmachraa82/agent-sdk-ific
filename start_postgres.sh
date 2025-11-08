#!/bin/bash
# EVF Portugal 2030 - PostgreSQL Startup Script
# This script starts PostgreSQL in Docker for local development

set -e  # Exit on error

echo "🐘 Starting PostgreSQL for EVF Portugal 2030..."

CONTAINER_NAME="evf-postgres"
POSTGRES_VERSION="16-alpine"
POSTGRES_USER="evf_user"
POSTGRES_PASSWORD="evf_password"
POSTGRES_DB="evf_portugal_2030"
POSTGRES_PORT="5432"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Check if container already exists and is running
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo "✅ PostgreSQL container is already running"
        echo "📍 Connection: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}"
        exit 0
    else
        echo "🔄 Starting existing PostgreSQL container..."
        docker start ${CONTAINER_NAME}
        echo "✅ PostgreSQL container started"
        echo "📍 Connection: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}"
        exit 0
    fi
fi

# Create new container
echo "📦 Creating new PostgreSQL container..."
docker run -d \
    --name ${CONTAINER_NAME} \
    -e POSTGRES_USER=${POSTGRES_USER} \
    -e POSTGRES_PASSWORD=${POSTGRES_PASSWORD} \
    -e POSTGRES_DB=${POSTGRES_DB} \
    -p ${POSTGRES_PORT}:5432 \
    -v evf-postgres-data:/var/lib/postgresql/data \
    postgres:${POSTGRES_VERSION}

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5

# Test connection
for i in {1..30}; do
    if docker exec ${CONTAINER_NAME} pg_isready -U ${POSTGRES_USER} > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready!"
        echo ""
        echo "📍 Connection details:"
        echo "   Host: localhost"
        echo "   Port: ${POSTGRES_PORT}"
        echo "   Database: ${POSTGRES_DB}"
        echo "   User: ${POSTGRES_USER}"
        echo "   Password: ${POSTGRES_PASSWORD}"
        echo ""
        echo "📍 Connection string:"
        echo "   postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:${POSTGRES_PORT}/${POSTGRES_DB}"
        echo ""
        echo "💡 To stop: docker stop ${CONTAINER_NAME}"
        echo "💡 To remove: docker rm ${CONTAINER_NAME}"
        echo "💡 To view logs: docker logs ${CONTAINER_NAME}"
        exit 0
    fi
    echo "   Still waiting... ($i/30)"
    sleep 1
done

echo "❌ PostgreSQL failed to start within 30 seconds"
echo "🔍 Check logs with: docker logs ${CONTAINER_NAME}"
exit 1
