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

bash scripts/build-papers.sh
npm run dev:css &
CSS_PID=$!

uv run sphinx-autobuild \
  -b dirhtml -a source build/dirhtml \
  --host 127.0.0.1 \
  --port 8000 \
  --watch source
