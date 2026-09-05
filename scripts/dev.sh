#!/usr/bin/env bash
set -euo pipefail

if [ ! -x node_modules/.bin/tailwindcss ]; then
  echo "ERROR: node_modules is missing; run 'npm install' first." >&2
  exit 1
fi

cleanup() {
  if [ -n "${CSS_PID:-}" ]; then
    kill "$CSS_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

npm run dev:css &
CSS_PID=$!

uv run sphinx-autobuild \
  -a source build/dirhtml \
  --host 0.0.0.0 \
  --port 8000 \
  --watch source
