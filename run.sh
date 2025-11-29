#!/usr/bin/env zsh
set -euo pipefail

echo "Starting ISP AI Chatbot Environment..."

# Find a Python executable (prefer python3)
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "Python is not installed. Please install Python 3 (homebrew: brew install python)."
  exit 1
fi

echo "Using: $PY"

# Allow skipping install/run for quick tests
SKIP_INSTALL=${SKIP_INSTALL:-0}
SKIP_RUN=${SKIP_RUN:-0}

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  $PY -m venv venv
fi

echo "Activating virtual environment..."
# Prefer POSIX venv layout, but handle Windows-style `Scripts` folder if present
if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
  echo "Detected Windows-style venv; sourcing venv/Scripts/activate"
  source venv/Scripts/activate
else
  echo "No activation script found in venv. Recreating virtualenv..."
  rm -rf venv
  $PY -m venv venv
  source venv/bin/activate
fi

if [ "$SKIP_INSTALL" != "1" ]; then
  echo "Upgrading pip and wheel..."
  python -m pip install --upgrade pip setuptools wheel

  echo "Installing dependencies..."
  pip install -r requirements.txt
else
  echo "SKIP_INSTALL=1 set — skipping dependency installation"
fi

if [ "$SKIP_RUN" = "1" ]; then
  echo "SKIP_RUN=1 set — skipping server start"
  echo "Virtual environment ready. Activate with: source venv/bin/activate (or venv/Scripts/activate)"
  exit 0
fi

echo "Starting FastAPI Server..."
echo "Access the chat at http://127.0.0.1:8000"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

exit 0
