#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SITE_DIR="$ROOT_DIR/site"
DOCROOT="/var/www/blog-site"

echo "==> Step 1/5: Running AutoBlog engine (DeepSeek)"
python3 "$ROOT_DIR/engine/autoblog.py"

echo "==> Step 2/5: Converting article images to PNG (Facebook og:image)"
(cd "$SITE_DIR" && node "$ROOT_DIR/scripts/convert-images.mjs")

echo "==> Step 3/5: Building Astro site"
(cd "$SITE_DIR" && npm run build)

echo "==> Step 4/5: Publishing to $DOCROOT"
mkdir -p "$DOCROOT"
rm -rf "$DOCROOT"/*
cp -r "$SITE_DIR/dist/"* "$DOCROOT/"

echo "==> Step 5/5: Auto-publishing new articles to Facebook"
python3 "$ROOT_DIR/engine/facebook.py"

echo "==> Deploy complete"
