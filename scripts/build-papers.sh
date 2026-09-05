#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$project_root"

python3 scripts/convert_materials.py
mkdir -p source/_static/files/papers

for source in typst/papers/*.typ; do
  year="$(basename "$source" .typ)"
  typst compile --root "$project_root" "$source" "source/_static/files/papers/${year}-408-paper.pdf"
done
