#!/bin/bash
# EVF Portugal 2030 - Complete Application Startup Script
# This script starts PostgreSQL, Backend, and Frontend in the correct order

set -e  # Exit on error

echo "🚀 Starting EVF Portugal 2030 - Complete Stack"
echo "================================================"
echo ""

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Cleanup function to kill background processes
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    exit 0
}

trap cleanup SIGINT SIGTERM

# Step 1: Start PostgreSQL
echo "Step 1/3: Starting PostgreSQL..."
echo "-------------------------------"
"${PROJECT_DIR}/start_postgres.sh"
echo ""

# Step 2: Start Backend
echo "Step 2/3: Starting Backend..."
echo "-------------------------------"
(cd "${PROJECT_DIR}" && ./start_backend.sh) &
BACKEND_PID=$!

# Wait for backend to be ready
echo "⏳ Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "✅ Backend is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend failed to start within 30 seconds"
        cleanup
        exit 1
    fi
    sleep 1
done
echo ""

# Step 3: Start Frontend
echo "Step 3/3: Starting Frontend..."
echo "-------------------------------"
(cd "${PROJECT_DIR}" && ./start_frontend.sh) &
FRONTEND_PID=$!

# Wait for frontend to be ready
echo "⏳ Waiting for frontend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "✅ Frontend is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "⚠️  Frontend may still be starting..."
        break
    fi
    sleep 1
done

echo ""
echo "================================================"
echo "✨ EVF Portugal 2030 is now running!"
echo "================================================"
echo ""
echo "📍 Services:"
echo "   Frontend:  http://localhost:3000"
echo "   Backend:   http://localhost:8000"
echo "   API Docs:  http://localhost:8000/api/docs"
echo "   Health:    http://localhost:8000/api/health"
echo ""
echo "🔐 Demo Credentials (after seeding):"
echo "   Email:     demo@evfportugal2030.pt"
echo "   Password:  Demo123!@#"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for processes
wait
