#!/usr/bin/env zsh
set -euo pipefail

echo "🚀 Starting ISP AI Chatbot Environment..."

# Find Python executable
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "❌ Python is not installed. Please install Python 3."
  exit 1
fi
echo "Using: $PY"

# Skip flags
SKIP_INSTALL=${SKIP_INSTALL:-0}
SKIP_RUN=${SKIP_RUN:-0}

# Create virtual environment
if [ ! -d "venv" ]; then
  echo "🛠 Creating virtual environment..."
  $PY -m venv venv
fi

# Activate virtual environment
echo "🔑 Activating virtual environment..."
if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
  echo "Detected Windows-style venv; sourcing venv/Scripts/activate"
  source venv/Scripts/activate
else
  echo "No activation script found. Recreating venv..."
  rm -rf venv
  $PY -m venv venv
  source venv/bin/activate
fi

# Install dependencies
if [ "$SKIP_INSTALL" != "1" ]; then
  echo "📦 Upgrading pip & wheel..."
  python -m pip install --upgrade pip setuptools wheel

  echo "📥 Installing dependencies from requirements.txt..."
  pip install -r requirements.txt
else
  echo "⚡ SKIP_INSTALL=1 set — skipping dependency installation"
fi

# Skip run
if [ "$SKIP_RUN" = "1" ]; then
  echo "⚡ SKIP_RUN=1 set — skipping server start"
  echo "✅ Virtual environment ready. Activate with: source venv/bin/activate"
  exit 0
fi

# Try port 80 first, fallback to 8000
PORT=80
if ! python -c "import socket; s=socket.socket(); s.bind(('0.0.0.0', $PORT))" >/dev/null 2>&1; then
  echo "⚠️ Cannot bind to port 80 — falling back to 8000"
  PORT=8000
fi

echo "🚀 Starting FastAPI Server on 0.0.0.0:$PORT..."
echo "🌐 Access your chat at http://YOUR_DOMAIN or http://VPS_IP:$PORT"

nohup uvicorn app.main:app --host 0.0.0.0 --port $PORT

exit 0
