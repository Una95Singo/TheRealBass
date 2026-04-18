#!/usr/bin/env bash
# One-time (idempotent) setup for TheRealBass: creates the backend venv,
# installs Python + npm deps. Safe to re-run — skips completed steps.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if ! command -v python3.11 >/dev/null 2>&1; then
  echo "error: python3.11 not found on PATH." >&2
  echo "  macOS:  brew install python@3.11" >&2
  echo "  Linux:  use your package manager (apt/dnf/etc.)" >&2
  echo "The backend pins torch==2.2.2, which has no wheels for Python 3.12+." >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "error: npm not found on PATH. Install Node.js (https://nodejs.org)." >&2
  exit 1
fi

echo "==> Backend venv"
cd "$ROOT/backend"
if [ ! -d .venv ]; then
  python3.11 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
deactivate

echo "==> Frontend deps"
cd "$ROOT/frontend"
if [ ! -d node_modules ]; then
  npm install --silent
fi

echo "==> Setup complete."
