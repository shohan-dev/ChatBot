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

# Force port 80 (note: binding to port 80 typically requires root privileges)
PORT=80

echo "🚀 Starting FastAPI Server on 0.0.0.0:$PORT..."
echo "🌐 Access your chat at http://YOUR_DOMAIN or http://VPS_IP:$PORT"
# Helper: get PIDs listening on port 80
get_port_pids() {
  # Prefer lsof, fallback to ss where available
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti tcp:80 2>/dev/null || true
  elif command -v ss >/dev/null 2>&1; then
    ss -ltnp 2>/dev/null | awk '/:80/ { gsub(/.*pid=/,"",$0); gsub(/,.*/,"",$0); print $NF }' || true
  else
    # Neither tool available
    echo "" 
  fi
}

# If port 80 is in use, try to free it
existing_pids=$(get_port_pids)
if [ -n "${existing_pids// /}" ]; then
  echo "⚠️ Port 80 is in use by PID(s): $existing_pids — attempting to terminate..."

  # Try graceful termination first
  if kill $existing_pids >/dev/null 2>&1; then
    echo "Attempted graceful termination of $existing_pids"
  fi

  # Wait briefly for sockets to free
  sleep 2
  existing_pids=$(get_port_pids)
  if [ -n "${existing_pids// /}" ]; then
    echo "⚠️ Graceful termination did not free port 80. Attempting force kill (requires sudo)..."
    if command -v sudo >/dev/null 2>&1; then
      sudo kill -9 $existing_pids || true
      sleep 1
      existing_pids=$(get_port_pids)
      if [ -n "${existing_pids// /}" ]; then
        echo "❌ Could not free port 80 after force kill. Please free the port or run this script as root." >&2
        exit 1
      fi
    else
      echo "❌ 'sudo' not available to force-kill processes. Please free port 80 or run script as root." >&2
      exit 1
    fi
  fi
  echo "✅ Port 80 is now available."
fi

# Start uvicorn in background and suppress all output so nohup does not create nohup.out
# If you prefer to keep logs, change >/dev/null 2>&1 to a logfile path e.g. >./logs/uvicorn.log 2>&1
nohup uvicorn app.main:app --host 0.0.0.0 --port $PORT >/dev/null 2>&1 &

# Detach the job from the shell
# disown

exit 0
