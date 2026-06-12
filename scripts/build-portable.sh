#!/usr/bin/env bash
# Build portable release (Windows / macOS / Linux) including lyrics.db
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$ROOT/dist/0243-lyrics-portable"
ZIP_PATH="$ROOT/dist/0243-lyrics-portable.zip"
TAR_PATH="$ROOT/dist/0243-lyrics-portable-macos.tar.gz"

DB_PATH="$ROOT/lyrics.db"
if [[ ! -f "$DB_PATH" ]]; then
  echo "lyrics.db not found" >&2
  exit 1
fi

echo "==> Clean output dir..."
rm -rf "$OUT_DIR"
mkdir -p "$ROOT/dist"

copy_tree() {
  local src="$1" dst="$2"
  [[ -d "$src" ]] || return 0
  mkdir -p "$dst"
  rsync -a --delete \
    --exclude '__pycache__' --exclude '.git' --exclude 'venv' --exclude '.venv' \
    --exclude 'dist' --exclude '.agents' --exclude '*.pyc' --exclude '*.pyo' \
    "$src/" "$dst/"
}

echo "==> Copy app, data, frontend..."
copy_tree "$ROOT/app" "$OUT_DIR/app"
copy_tree "$ROOT/frontend" "$OUT_DIR/frontend"
copy_tree "$ROOT/data" "$OUT_DIR/data"
copy_tree "$ROOT/portable" "$OUT_DIR"

for f in main.py utils.py requirements.txt; do
  cp -f "$ROOT/$f" "$OUT_DIR/$f"
done

echo "==> Copy lyrics.db..."
cp -f "$DB_PATH" "$OUT_DIR/lyrics.db"

chmod +x "$OUT_DIR/START.sh" "$OUT_DIR/START.command" 2>/dev/null || true

echo "==> Create zip..."
rm -f "$ZIP_PATH"
(cd "$OUT_DIR" && zip -r -q "$ZIP_PATH" .)

echo "==> Create macOS tar.gz (preserves executable bit)..."
rm -f "$TAR_PATH"
tar -czf "$TAR_PATH" -C "$ROOT/dist" "0243-lyrics-portable"

zip_mb=$(du -m "$ZIP_PATH" | cut -f1)
tar_mb=$(du -m "$TAR_PATH" | cut -f1)
db_mb=$(du -m "$DB_PATH" | cut -f1)

echo ""
echo "Done."
echo "  Folder: $OUT_DIR"
echo "  ZIP:    $ZIP_PATH (${zip_mb} MB)"
echo "  macOS:  $TAR_PATH (${tar_mb} MB, db ${db_mb} MB)"
echo "  Windows: extract zip, run START.bat"
echo "  macOS:   extract tar.gz, double-click START.command"
