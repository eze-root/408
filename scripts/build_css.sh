#!/usr/bin/env bash
set -euo pipefail

if [ ! -x node_modules/.bin/tailwindcss ]; then
  echo "ERROR: node_modules is missing; run 'npm install' first." >&2
  exit 1
fi

mkdir -p source/_static/css
./node_modules/.bin/tailwindcss \
  -i source/_static/css/src/site.css \
  -o source/_static/css/site.css \
  --minify
