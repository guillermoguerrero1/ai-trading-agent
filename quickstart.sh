#!/bin/bash
# AI Trading Agent Quickstart Script

set -e

echo "🤖 AI Trading Agent Quickstart"
echo "==============================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    echo "   Please install Python 3.11+ and try again."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ Python 3.11+ is required, but found Python $PYTHON_VERSION"
    echo "   Please upgrade Python and try again."
    exit 1
fi

echo "✅ Python $PYTHON_VERSION detected"
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ pyproject.toml not found. Please run this script from the trading-agent directory."
    exit 1
fi

echo "✅ In correct directory"
echo ""

# Install dependencies
echo "📦 Installing dependencies..."
if command -v poetry &> /dev/null; then
    echo "   Using Poetry..."
    poetry install
else
    echo "   Using pip..."
    pip install -e .
fi

echo "✅ Dependencies installed"
echo ""

# Copy environment file
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cp .env.example .env
    echo "✅ .env file created (using example values)"
    echo "   You may want to edit .env to customize settings"
else
    echo "✅ .env file already exists"
fi

echo ""

# Run tests
echo "🧪 Running tests..."
if command -v poetry &> /dev/null; then
    poetry run python -m pytest tests/ -v --tb=short
else
    python -m pytest tests/ -v --tb=short
fi

echo "✅ Tests passed"
echo ""

# Start API server
echo "🚀 Starting API server..."
echo "   API will be available at: http://localhost:8000"
echo "   API docs at: http://localhost:8000/docs"
echo "   Press Ctrl+C to stop"
echo ""

if command -v poetry &> /dev/null; then
    poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi
