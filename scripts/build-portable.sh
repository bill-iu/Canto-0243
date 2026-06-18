#!/usr/bin/env bash
# Build portable release: macOS .app (免安裝) + optional folder for dev smoke test
set -eu
# ponytail: macOS /bin/bash 3.x lacks pipefail; CI macos-latest uses env bash
[[ "${BASH_VERSINFO[0]:-0}" -ge 4 ]] && set -o pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$ROOT/dist/canto-0243-portable"
APP_DIR="$ROOT/dist/Canto-0243.app"
APP_RES="$APP_DIR/Contents/Resources/app"
case "${PORTABLE_MACOS_ARCH:-$(uname -m)}" in
  arm64|aarch64) MAC_ARCH=arm64 ;;
  x86_64) MAC_ARCH=x86_64 ;;
  *)
    echo "unsupported macOS arch: ${PORTABLE_MACOS_ARCH:-$(uname -m)}" >&2
    exit 1
    ;;
esac
TAR_PATH="$ROOT/dist/canto-0243-portable-macos-${MAC_ARCH}.tar.gz"

DB_PATH="$ROOT/lyrics.db"
if [[ ! -f "$DB_PATH" ]]; then
  echo "lyrics.db not found" >&2
  exit 1
fi

if [[ -z "${SKIP_README_SYNC:-}" ]]; then
  echo "==> Sync README word count..."
  python3 "$ROOT/scripts/update_readme_words_count.py" --db "$DB_PATH"
fi

copy_tree() {
  local src="$1" dst="$2"
  [[ -d "$src" ]] || return 0
  mkdir -p "$dst"
  rsync -a --delete \
    --exclude '__pycache__' --exclude '.git' --exclude 'venv' --exclude '.venv' \
    --exclude 'dist' --exclude '.agents' --exclude 'macos' \
    --exclude '*.pyc' --exclude '*.pyo' \
    "$src/" "$dst/"
}

copy_portable_bundle() {
  local dst="$1"
  echo "==> Copy bundle into $dst..."
  rm -rf "$dst"
  mkdir -p "$dst"
  copy_tree "$ROOT/app" "$dst/app"
  copy_tree "$ROOT/frontend" "$dst/frontend"
  copy_tree "$ROOT/data" "$dst/data"
  copy_tree "$ROOT/portable" "$dst"
  cp -f "$ROOT/main.py" "$ROOT/requirements.txt" "$dst/"
  cp -f "$DB_PATH" "$dst/lyrics.db"
  chmod +x "$dst/START.sh" "$dst/START.command" 2>/dev/null || true
}

bundle_venv() {
  local dst="$1"
  echo "==> Build bundled venv in $dst (may take a few minutes)..."
  python3 "$ROOT/scripts/portable_venv.py" "$dst"
  python3 "$ROOT/scripts/portable_venv.py" "$dst" --self-check
}

echo "==> Clean output dirs..."
rm -rf "$OUT_DIR" "$APP_DIR"
mkdir -p "$ROOT/dist"

copy_portable_bundle "$OUT_DIR"
bundle_venv "$OUT_DIR"

echo "==> Warm word cache snapshot (.cache/word_meta.bin)..."
"$OUT_DIR/venv/bin/python" "$ROOT/scripts/warm_word_cache.py" "$OUT_DIR"

echo "==> Build Canto-0243.app..."
mkdir -p "$APP_DIR/Contents/MacOS"
copy_portable_bundle "$APP_RES"
bundle_venv "$APP_RES"
if [[ -d "$OUT_DIR/.cache" ]]; then
  rm -rf "$APP_RES/.cache"
  cp -R "$OUT_DIR/.cache" "$APP_RES/.cache"
fi

cp -f "$ROOT/portable/macos/Info.plist" "$APP_DIR/Contents/Info.plist"
cp -f "$ROOT/portable/macos/launcher" "$APP_DIR/Contents/MacOS/Canto-0243"
chmod +x "$APP_DIR/Contents/MacOS/Canto-0243"

if [[ "$(uname -s)" == "Darwin" ]] && command -v codesign >/dev/null 2>&1; then
  echo "==> Ad-hoc codesign Canto-0243.app (shallow; ponytail: no --deep over venv)..."
  codesign --force --sign - "$APP_DIR/Contents/MacOS/Canto-0243"
  codesign --force --sign - "$APP_DIR"
fi

OPEN_CMD_SRC="$ROOT/portable/macos/Open Canto-0243.command"
OPEN_CMD_DIST="$ROOT/dist/Open Canto-0243.command"
cp -f "$OPEN_CMD_SRC" "$OPEN_CMD_DIST"
chmod +x "$OPEN_CMD_DIST"
if [[ "$(uname -s)" == "Darwin" ]] && command -v codesign >/dev/null 2>&1; then
  echo "==> Ad-hoc codesign Open Canto-0243.command..."
  codesign --force --sign - "$OPEN_CMD_DIST"
fi

echo "==> Create macOS tar.gz (Canto-0243.app, ${MAC_ARCH})..."
rm -f "$TAR_PATH"
tar -czf "$TAR_PATH" -C "$ROOT/dist" "Canto-0243.app" "Open Canto-0243.command"

tar_mb=$(du -m "$TAR_PATH" | cut -f1)
db_mb=$(du -m "$DB_PATH" | cut -f1)

echo ""
echo "Done."
echo "  Dev folder: $OUT_DIR"
echo "  macOS app:  $APP_DIR"
echo "  tar.gz:     $TAR_PATH (${tar_mb} MB, .app 免安裝)"
echo "  db:         ${db_mb} MB"
echo "  Windows zip: run scripts/build-portable.ps1 on Windows"
echo "  Upload tar.gz + zip + lyrics.db + words-lexicon.json to GitHub Release."
