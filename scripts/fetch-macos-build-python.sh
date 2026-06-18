#!/usr/bin/env bash
# Fetch relocatable CPython for macOS portable builds (Intel MacBook without python.org install).
set -eu
[[ "${BASH_VERSINFO[0]:-0}" -ge 4 ]] && set -o pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$ROOT/.build-python"
URL="https://github.com/indygreg/python-build-standalone/releases/download/20241016/cpython-3.12.7%2B20241016-x86_64-apple-darwin-install_only.tar.gz"

case "$(uname -m)" in
  x86_64) ;;
  *)
    echo "error: fetch-macos-build-python.sh supports x86_64 only (this machine: $(uname -m))" >&2
    exit 1
    ;;
esac

PY="$DEST/python/bin/python3.12"
if [[ -x "$PY" ]]; then
  echo "Build Python already present: $PY"
  "$PY" --version
  exit 0
fi

mkdir -p "$DEST"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

echo "==> Download standalone CPython 3.12 (x86_64)..."
curl -fsSL -o "$tmp/python.tar.gz" "$URL"
tar -xzf "$tmp/python.tar.gz" -C "$DEST"
echo "==> Ready: $PY"
"$PY" --version
