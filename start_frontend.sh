#!/bin/bash
# EVF Portugal 2030 - Frontend Startup Script
# This script starts the Next.js frontend development server

set -e  # Exit on error

echo "🚀 Starting EVF Portugal 2030 Frontend..."

# Navigate to frontend directory
cd "$(dirname "$0")/frontend"

# Check if .env.local file exists
if [ ! -f ".env.local" ]; then
    echo "⚠️  Warning: .env.local file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env.local
        echo "✅ Created .env.local file."
    else
        echo "📝 Creating default .env.local..."
        cat > .env.local << 'EOF'
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_PREFIX=/api/v1

# App Configuration
NEXT_PUBLIC_APP_NAME=EVF Portugal 2030
NEXT_PUBLIC_APP_VERSION=1.0.0
NEXT_PUBLIC_ENVIRONMENT=development
EOF
        echo "✅ Created default .env.local file."
    fi
fi

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies (first time setup)..."
    npm install
else
    echo "📦 Checking for dependency updates..."
    npm install --quiet
fi

# Start the development server
echo ""
echo "✨ Starting Next.js development server..."
echo "📍 Frontend will be available at: http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

npm run dev
