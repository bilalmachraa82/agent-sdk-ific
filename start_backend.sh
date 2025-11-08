#!/bin/bash
# EVF Portugal 2030 - Backend Startup Script
# This script starts the FastAPI backend server with all necessary setup

set -e  # Exit on error

echo "🚀 Starting EVF Portugal 2030 Backend..."

# Navigate to backend directory
cd "$(dirname "$0")/backend"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip > /dev/null 2>&1

# Install/update dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt --quiet

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ Created .env file. Please configure it before proceeding."
        echo "   Edit backend/.env with your database and API keys."
        exit 1
    else
        echo "❌ Error: No .env.example file found. Please create .env manually."
        exit 1
    fi
fi

# Check database connection
echo "🗄️  Checking database connection..."
python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from backend.core.config import settings

async def check_db():
    try:
        engine = create_async_engine(settings.database_url, echo=False)
        async with engine.connect() as conn:
            await conn.execute('SELECT 1')
        await engine.dispose()
        print('✅ Database connection successful')
        return True
    except Exception as e:
        print(f'❌ Database connection failed: {e}')
        print('   Please ensure PostgreSQL is running and configured correctly.')
        return False

exit(0 if asyncio.run(check_db()) else 1)
" || {
    echo ""
    echo "💡 Quick fix: Run './start_postgres.sh' to start PostgreSQL in Docker"
    exit 1
}

# Run database migrations
echo "🔄 Running database migrations..."
alembic upgrade head

# Seed initial data if needed
if [ -f "seed_data.py" ]; then
    echo "🌱 Seeding initial data..."
    python seed_data.py
fi

# Start the server
echo ""
echo "✨ Starting FastAPI server..."
echo "📍 API will be available at: http://localhost:8000"
echo "📖 API docs will be at: http://localhost:8000/api/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python main.py
