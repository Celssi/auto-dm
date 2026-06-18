#!/usr/bin/env bash
# Start FastAPI backend + Vite frontend (http://localhost:5173)

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

API_PORT="${API_PORT:-8000}"
UI_PORT="${UI_PORT:-5173}"

if [[ ! -d .venv ]]; then
  echo "Virtualenv missing. Create it first:"
  echo "  python3 -m venv .venv && source .venv/bin/activate && pip install -e ."
  exit 1
fi

if [[ ! -d frontend/node_modules ]]; then
  echo "Installing frontend dependencies..."
  (cd frontend && npm install)
fi

# shellcheck disable=SC1091
source .venv/bin/activate

cleanup() {
  echo ""
  echo "Shutting down..."
  local pid
  for pid in $(jobs -p); do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "=== Auto-DM ==="
echo "API:  http://127.0.0.1:${API_PORT}"
echo "UI:   http://localhost:${UI_PORT}"
echo "Press Ctrl+C to stop both servers."
echo ""

uvicorn backend.main:app --reload --host 127.0.0.1 --port "$API_PORT" &
API_PID=$!

# Wait until API responds (optional quick check)
for _ in {1..30}; do
  if curl -sf "http://127.0.0.1:${API_PORT}/api/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

cd frontend
npm run dev -- --host 127.0.0.1 --port "$UI_PORT" &
UI_PID=$!

wait "$API_PID" "$UI_PID"
