#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

echo "🧩 Skills Registry"
echo "=================="

# Backend setup
echo ""
echo "→ Setting up backend..."
cd "$BACKEND"

if [ ! -d ".venv" ]; then
  echo "  Creating Python virtual environment..."
  python3 -m venv .venv
fi

source .venv/bin/activate
echo "  Installing Python dependencies..."
pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "  ⚠️  Created .env from template — set ANTHROPIC_API_KEY for LLM research"
fi

# Frontend setup
echo ""
echo "→ Setting up frontend..."
cd "$FRONTEND"
if [ ! -d "node_modules" ]; then
  echo "  Installing npm dependencies..."
  npm install --silent
fi

# Start both
echo ""
echo "→ Starting services..."
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo "   MCP:      http://localhost:8000/mcp"
echo "   Frontend: http://localhost:5173"
echo ""

cd "$BACKEND"
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

cd "$FRONTEND"
npm run dev &
FRONTEND_PID=$!

echo "✅ Both services started!"
echo "   Press Ctrl+C to stop"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait $BACKEND_PID $FRONTEND_PID
