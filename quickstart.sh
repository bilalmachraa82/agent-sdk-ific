#!/bin/bash

# FundAI Quick Start Script
# Sets up local development environment in one command

set -e

echo "🚀 FundAI Quick Start"
echo "===================="
echo ""

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "❌ Docker not found. Install from https://docker.com"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose not found."; exit 1; }
command -v poetry >/dev/null 2>&1 || { echo "⚠️  Poetry not found. Installing..."; curl -sSL https://install.python-poetry.org | python3 -; }

echo "✅ Prerequisites OK"
echo ""

# Setup environment
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp .env.example .env
    echo "⚠️  IMPORTANT: Edit .env and add your ANTHROPIC_API_KEY"
    echo "   Get your key from: https://console.anthropic.com/"
    echo ""
    read -p "Press Enter after adding your API key..."
fi

# Validate API key
if grep -q "your-.*-key-here" .env; then
    echo "❌ ERROR: API keys not configured in .env"
    echo "   Please edit .env and replace placeholder keys"
    exit 1
fi

echo "✅ Environment configured"
echo ""

# Install dependencies
echo "📦 Installing Python dependencies..."
poetry install

echo "✅ Dependencies installed"
echo ""

# Start services
echo "🐳 Starting Docker services..."
docker-compose up -d postgres redis

# Wait for database
echo "⏳ Waiting for PostgreSQL..."
sleep 5

# Run migrations (when implemented)
# poetry run alembic upgrade head

echo "✅ Services started"
echo ""

# Run tests
echo "🧪 Running tests..."
poetry run pytest -v

echo ""
echo "🎉 Setup Complete!"
echo ""
echo "Next steps:"
echo "1. Start API:     poetry run uvicorn api.main:app --reload"
echo "2. View docs:     http://localhost:8000/docs"
echo "3. Test endpoint: curl http://localhost:8000/health"
echo ""
echo "Or use Makefile commands:"
echo "  make dev          - Start development server"
echo "  make test         - Run tests"
echo "  make docker-up    - Start all services with Docker"
echo ""
echo "Full documentation: README.md"
