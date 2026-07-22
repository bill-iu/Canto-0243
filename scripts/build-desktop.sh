#!/usr/bin/env bash
# Build Desktop release for macOS (ADR-0068: PyApp + wheel + sidecar).
# Creator primary entry: Canto-0243.command (not unsigned .app).
set -eu
[[ "${BASH_VERSINFO[0]:-0}" -ge 4 ]] && set -o pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${ROOT}/dist/canto-0243-desktop"
DB_PATH="${ROOT}/lyrics.db"

# Prefer standalone 3.12 for build tooling; fall back to python3.
if [[ -x "${ROOT}/.build-python/python/bin/python3.12" ]]; then
  PY="${ROOT}/.build-python/python/bin/python3.12"
else
  PY="${PYTHON:-python3}"
fi

_project_version() {
  "$PY" -c "
from pathlib import Path
text = Path('${ROOT}/pyproject.toml').read_text(encoding='utf-8')
for line in text.splitlines():
    s = line.strip()
    if s.startswith('version') and '=' in s:
        print(s.split('=', 1)[1].strip().strip('\"').strip(\"'\"))
        break
else:
    raise SystemExit('version not found in pyproject.toml')
"
}

case "${DESKTOP_MACOS_ARCH:-${PORTABLE_MACOS_ARCH:-$(uname -m)}}" in
  arm64|aarch64) MAC_ARCH=arm64 ;;
  x86_64|amd64) MAC_ARCH=x86_64 ;;
  *) echo "unsupported macOS arch" >&2; exit 1 ;;
esac

TAR_PATH="${ROOT}/dist/canto-0243-desktop-macos-${MAC_ARCH}.tar.gz"

[[ -f "$DB_PATH" ]] || { echo "lyrics.db not found" >&2; exit 1; }
[[ -f "${ROOT}/client/dist-portable/index.html" ]] || {
  echo "client/dist-portable missing; run: cd client && npm run build:portable" >&2
  exit 1
}
command -v cargo >/dev/null || { echo "cargo required (rustup)" >&2; exit 1; }

echo "==> Clean $OUT_DIR"
rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR" "${ROOT}/dist/wheels"

echo "==> Build wheel (python=$PY)"
"$PY" -m pip install -q build wheel setuptools
"$PY" -m build --wheel --outdir "${ROOT}/dist/wheels"
WHEEL="$(ls -t "${ROOT}/dist/wheels"/canto_0243-*.whl | head -1)"
[[ -n "$WHEEL" && -f "$WHEEL" ]] || { echo "wheel missing" >&2; exit 1; }

echo "==> Sidecar"
mkdir -p "${OUT_DIR}/client" "${OUT_DIR}/data"
cp -R "${ROOT}/client/dist-portable" "${OUT_DIR}/client/dist-portable"
# slim data via python helper when present
if [[ -d "${ROOT}/data" ]]; then
  rsync -a --exclude '__pycache__' --exclude 'audit' --exclude 'fixtures' \
    --exclude 'raw' --exclude 'proposals' --exclude 'locks' --exclude 'pos' \
    --exclude 'project' "${ROOT}/data/" "${OUT_DIR}/data/" || \
    cp -R "${ROOT}/data/." "${OUT_DIR}/data/"
  "$PY" "${ROOT}/scripts/portable_data_slim.py" "${OUT_DIR}/data" || true
fi
cp "$DB_PATH" "${OUT_DIR}/lyrics.db"
cp "$WHEEL" "${OUT_DIR}/"
[[ -f "${ROOT}/portable/README.txt" ]] && cp "${ROOT}/portable/README.txt" "${OUT_DIR}/"
[[ -f "${ROOT}/portable/env.portable" ]] && cp "${ROOT}/portable/env.portable" "${OUT_DIR}/"

echo "==> PyApp launcher"
PYAPP_DIR="${ROOT}/dist/_pyapp_src"
rm -rf "$PYAPP_DIR"
mkdir -p "$PYAPP_DIR"
curl -fsSL -o "${ROOT}/dist/pyapp-source.tar.gz" \
  "https://github.com/ofek/pyapp/releases/latest/download/source.tar.gz"
tar -xzf "${ROOT}/dist/pyapp-source.tar.gz" -C "$PYAPP_DIR"
BUILD_ROOT="$(find "$PYAPP_DIR" -maxdepth 1 -type d -name 'pyapp*' | head -1)"
VER="$(_project_version)"

export PYAPP_PROJECT_PATH="$WHEEL"
export PYAPP_PROJECT_NAME="canto-0243"
export PYAPP_PROJECT_VERSION="$VER"
export PYAPP_PYTHON_VERSION="3.11"
export PYAPP_EXEC_SPEC="app.desktop_entry:main"
export PYAPP_PIP_EXTERNAL=1
export PYAPP_UV_ENABLED=1
# GUI flag is mainly Windows; macOS uses .command console path for Gatekeeper.

(
  cd "$BUILD_ROOT"
  cargo build --release
)
BIN="${BUILD_ROOT}/target/release/pyapp"
[[ -f "$BIN" ]] || { echo "pyapp binary missing" >&2; exit 1; }
mkdir -p "${OUT_DIR}/runtime"
cp "$BIN" "${OUT_DIR}/runtime/Canto-0243-runtime"
chmod +x "${OUT_DIR}/runtime/Canto-0243-runtime"

echo "==> Desktop install progress shell (wry)"
(
  cd "${ROOT}/desktop-shell"
  cargo build --release
)
SHELL_BIN="${ROOT}/desktop-shell/target/release/canto-desktop-shell"
[[ -f "$SHELL_BIN" ]] || { echo "desktop-shell binary missing" >&2; exit 1; }
cp "$SHELL_BIN" "${OUT_DIR}/Canto-0243"
chmod +x "${OUT_DIR}/Canto-0243"

# Creator primary: .command wraps outer shell + sets cwd to payload root
cat > "${OUT_DIR}/Canto-0243.command" <<'EOF'
#!/bin/bash
# Desktop macOS entry (ADR-0068) — Gatekeeper: right-click → Open
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
export CANTO_PAYLOAD_ROOT="$ROOT"
export PORTABLE=1
export ENV=local
# Best-effort quarantine clear on this tree
xattr -dr com.apple.quarantine "$ROOT" 2>/dev/null || true
exec "$ROOT/Canto-0243"
EOF
chmod +x "${OUT_DIR}/Canto-0243.command"

"$PY" "${ROOT}/scripts/warm_word_cache.py" "$OUT_DIR" || true

if command -v codesign >/dev/null 2>&1; then
  echo "==> Ad-hoc codesign Desktop binaries..."
  codesign --force --sign - "${OUT_DIR}/Canto-0243" 2>/dev/null || true
  codesign --force --sign - "${OUT_DIR}/runtime/Canto-0243-runtime" 2>/dev/null || true
  codesign --force --sign - "${OUT_DIR}/Canto-0243.command" 2>/dev/null || true
fi

TAG="${DESKTOP_RELEASE_TAG:-${PORTABLE_RELEASE_TAG:-}}"
if [[ -n "$TAG" ]]; then
  PLATFORM="macos-${MAC_ARCH}"
  SIDECAR="${ROOT}/dist/portable-manifest-${PLATFORM}.json"
  "$PY" "${ROOT}/scripts/write_portable_manifest.py" \
    --root "$OUT_DIR" --tag "$TAG" --platform "$PLATFORM" --sidecar "$SIDECAR"
fi

echo "==> tar $TAR_PATH"
rm -f "$TAR_PATH"
tar -czf "$TAR_PATH" -C "$(dirname "$OUT_DIR")" "$(basename "$OUT_DIR")"
echo "Done: $TAR_PATH"
echo "First run needs network (CPython 3.11); use Canto-0243.command (not unsigned .app)."
