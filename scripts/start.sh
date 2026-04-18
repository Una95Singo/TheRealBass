#!/usr/bin/env bash
# Start both servers and open the app in the browser.
# Ctrl+C tears both down.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

"$ROOT/scripts/setup.sh"

BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo
  echo "==> Stopping servers..."
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "==> Starting backend on http://127.0.0.1:8000"
(
  cd "$ROOT/backend"
  # shellcheck disable=SC1091
  source .venv/bin/activate
  exec python main.py
) &
BACKEND_PID=$!

echo "==> Starting frontend on http://127.0.0.1:5173"
(
  cd "$ROOT/frontend"
  exec npm run dev --silent
) &
FRONTEND_PID=$!

# Wait up to 30s for the frontend to respond, then open the browser.
echo "==> Waiting for frontend..."
for _ in $(seq 1 60); do
  if curl -fsS -o /dev/null http://127.0.0.1:5173 2>/dev/null; then
    break
  fi
  sleep 0.5
done

if command -v open >/dev/null 2>&1; then
  open http://127.0.0.1:5173 || true
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open http://127.0.0.1:5173 || true
fi

echo
echo "==> TheRealBass is running. Press Ctrl+C to stop."
wait
