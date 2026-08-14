#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SITE_DIR="$ROOT_DIR/site"
DOCROOT="/var/www/blog-site"

echo "==> Step 1/3: Running AutoBlog engine (DeepSeek)"
python3 "$ROOT_DIR/engine/autoblog.py"

echo "==> Step 2/3: Building Astro site"
(cd "$SITE_DIR" && npm run build)

echo "==> Step 3/3: Publishing to $DOCROOT"
mkdir -p "$DOCROOT"
rm -rf "$DOCROOT"/*
cp -r "$SITE_DIR/dist/"* "$DOCROOT/"

echo "==> Deploy complete"
