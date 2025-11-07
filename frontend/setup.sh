#!/bin/bash

# EVF Portugal 2030 Frontend Setup Script
# This script sets up the development environment

set -e

echo "🚀 Setting up EVF Portugal 2030 Frontend..."
echo ""

# Check Node.js version
NODE_VERSION=$(node -v | cut -d 'v' -f 2 | cut -d '.' -f 1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Error: Node.js 18 or higher is required"
    echo "   Current version: $(node -v)"
    exit 1
fi
echo "✅ Node.js version: $(node -v)"

# Check if package manager is available
if command -v pnpm &> /dev/null; then
    PKG_MANAGER="pnpm"
elif command -v yarn &> /dev/null; then
    PKG_MANAGER="yarn"
else
    PKG_MANAGER="npm"
fi
echo "✅ Using package manager: $PKG_MANAGER"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
if [ "$PKG_MANAGER" = "pnpm" ]; then
    pnpm install
elif [ "$PKG_MANAGER" = "yarn" ]; then
    yarn install
else
    npm install
fi
echo "✅ Dependencies installed"
echo ""

# Create .env.local if it doesn't exist
if [ ! -f .env.local ]; then
    echo "🔧 Creating .env.local file..."
    cp .env.local.example .env.local
    echo "✅ .env.local created from template"
    echo "⚠️  Please update .env.local with your configuration"
else
    echo "✅ .env.local already exists"
fi
echo ""

# Run type checking
echo "🔍 Running type check..."
if [ "$PKG_MANAGER" = "pnpm" ]; then
    pnpm run type-check
elif [ "$PKG_MANAGER" = "yarn" ]; then
    yarn type-check
else
    npm run type-check
fi
echo "✅ Type check passed"
echo ""

# Run linting
echo "🧹 Running linter..."
if [ "$PKG_MANAGER" = "pnpm" ]; then
    pnpm run lint
elif [ "$PKG_MANAGER" = "yarn" ]; then
    yarn lint
else
    npm run lint
fi
echo "✅ Linting passed"
echo ""

echo "🎉 Setup complete!"
echo ""
echo "📝 Next steps:"
echo "   1. Update .env.local with your backend API URL"
echo "   2. Start the development server:"
echo "      $PKG_MANAGER run dev"
echo ""
echo "   3. Open http://localhost:3000 in your browser"
echo ""
echo "📚 Documentation:"
echo "   - README.md - Quick start guide"
echo "   - IMPLEMENTATION_GUIDE.md - Detailed implementation docs"
echo ""
echo "Happy coding! 🚀"
