#!/usr/bin/env bash
# Build portable release: macOS folder + Canto-0243.command (免安裝)
set -eu
# ponytail: macOS /bin/bash 3.x lacks pipefail; CI macos-latest uses env bash
[[ "${BASH_VERSINFO[0]:-0}" -ge 4 ]] && set -o pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$ROOT/dist/canto-0243-portable"
case "${PORTABLE_MACOS_ARCH:-$(uname -m)}" in
  arm64|aarch64) MAC_ARCH=arm64 ;;
  x86_64) MAC_ARCH=x86_64 ;;
  *)
    echo "unsupported macOS arch: ${PORTABLE_MACOS_ARCH:-$(uname -m)}" >&2
    exit 1
    ;;
esac
TAR_PATH="$ROOT/dist/canto-0243-portable-macos-${MAC_ARCH}.tar.gz"
MAC_CMD_SRC="$ROOT/portable/macos/Canto-0243.command"

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
  copy_tree "$ROOT/portable" "$dst"
  copy_tree "$ROOT/app" "$dst/app"
  copy_tree "$ROOT/frontend" "$dst/frontend"
  copy_tree "$ROOT/data" "$dst/data"
  cp -f "$ROOT/main.py" "$ROOT/requirements.txt" "$dst/"
  cp -f "$DB_PATH" "$dst/lyrics.db"
  chmod +x "$dst/START.sh" "$dst/START.command" 2>/dev/null || true
}

bundle_venv() {
  local dst="$1"
  echo "==> Build bundled venv in $dst (may take a few minutes)..."
  local py="${PORTABLE_BUILD_PYTHON:-python3}"
  "$py" "$ROOT/scripts/portable_venv.py" "$dst"
  "$py" "$ROOT/scripts/portable_venv.py" "$dst" --self-check
}

strip_cr() {
  python3 -c 'import pathlib, sys; p = pathlib.Path(sys.argv[1]); p.write_bytes(p.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n"))' "$1"
}

echo "==> Clean output dirs..."
rm -rf "$OUT_DIR"
mkdir -p "$ROOT/dist"

copy_portable_bundle "$OUT_DIR"
bundle_venv "$OUT_DIR"

echo "==> Warm word cache snapshot (.cache/word_meta.bin)..."
"$OUT_DIR/venv/bin/python" "$ROOT/scripts/warm_word_cache.py" "$OUT_DIR"

echo "==> Install Canto-0243.command..."
cp -f "$MAC_CMD_SRC" "$OUT_DIR/Canto-0243.command"
chmod +x "$OUT_DIR/Canto-0243.command"
strip_cr "$OUT_DIR/Canto-0243.command"

if [[ "$(uname -s)" == "Darwin" ]] && command -v codesign >/dev/null 2>&1; then
  echo "==> Ad-hoc deep codesign venv + Canto-0243.command..."
  codesign --deep --force --sign - "$OUT_DIR/venv"
  codesign --force --sign - "$OUT_DIR/Canto-0243.command"
fi

echo "==> Create macOS tar.gz (canto-0243-portable + Canto-0243.command, ${MAC_ARCH})..."
rm -f "$TAR_PATH"
tar -czf "$TAR_PATH" -C "$ROOT/dist" "canto-0243-portable"

tar_mb=$(du -m "$TAR_PATH" | cut -f1)
db_mb=$(du -m "$DB_PATH" | cut -f1)

echo ""
echo "Done."
echo "  Bundle:     $OUT_DIR"
echo "  Entry:      $OUT_DIR/Canto-0243.command"
echo "  tar.gz:     $TAR_PATH (${tar_mb} MB)"
echo "  db:         ${db_mb} MB"
echo "  Windows zip: run scripts/build-portable.ps1 on Windows"
echo "  Upload tar.gz + zip + lyrics.db + words-lexicon.json to GitHub Release."
