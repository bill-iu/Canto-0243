#!/usr/bin/env bash
# Build Desktop release for macOS (ADR-0068 + ADR-0070: PyApp + wheel + sidecar).
# Creator primary entry: Canto-0243.app (not .command).
set -eu
[[ "${BASH_VERSINFO[0]:-0}" -ge 4 ]] && set -o pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="${ROOT}/dist/canto-0243-desktop"
DB_PATH="${ROOT}/lyrics.db"
APP_NAME="Canto-0243.app"
BUNDLE_ID="com.canto0243.desktop"

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

# ADR-0070: AppIcon.icns from PWA icon-512.png
_make_app_icns() {
  local src="$1" dest_icns="$2"
  local iconset tmp
  [[ -f "$src" ]] || {
    echo "error: icon source missing: $src" >&2
    return 1
  }
  command -v sips >/dev/null 2>&1 || {
    echo "error: sips required to build AppIcon.icns" >&2
    return 1
  }
  command -v iconutil >/dev/null 2>&1 || {
    echo "error: iconutil required to build AppIcon.icns" >&2
    return 1
  }
  tmp="$(mktemp -d)"
  iconset="${tmp}/AppIcon.iconset"
  mkdir -p "$iconset"
  # Standard iconutil set (512@2x = 1024 via upsample if needed)
  sips -z 16 16 "$src" --out "${iconset}/icon_16x16.png" >/dev/null
  sips -z 32 32 "$src" --out "${iconset}/icon_16x16@2x.png" >/dev/null
  sips -z 32 32 "$src" --out "${iconset}/icon_32x32.png" >/dev/null
  sips -z 64 64 "$src" --out "${iconset}/icon_32x32@2x.png" >/dev/null
  sips -z 128 128 "$src" --out "${iconset}/icon_128x128.png" >/dev/null
  sips -z 256 256 "$src" --out "${iconset}/icon_128x128@2x.png" >/dev/null
  sips -z 256 256 "$src" --out "${iconset}/icon_256x256.png" >/dev/null
  sips -z 512 512 "$src" --out "${iconset}/icon_256x256@2x.png" >/dev/null
  sips -z 512 512 "$src" --out "${iconset}/icon_512x512.png" >/dev/null
  # 1024 for 512@2x — upsample from 512 is fine for Finder
  sips -z 1024 1024 "$src" --out "${iconset}/icon_512x512@2x.png" >/dev/null
  iconutil -c icns "$iconset" -o "$dest_icns"
  rm -rf "$tmp"
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

echo "==> Sidecar (beside .app; ADR-0070 B1)"
mkdir -p "${OUT_DIR}/client" "${OUT_DIR}/data"
cp -R "${ROOT}/client/dist-portable" "${OUT_DIR}/client/dist-portable"
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

(
  cd "$BUILD_ROOT"
  cargo build --release
)
PYAPP_BIN="${BUILD_ROOT}/target/release/pyapp"
[[ -f "$PYAPP_BIN" ]] || { echo "pyapp binary missing" >&2; exit 1; }

echo "==> Desktop install progress shell (wry)"
(
  cd "${ROOT}/desktop-shell"
  cargo build --release
)
SHELL_BIN="${ROOT}/desktop-shell/target/release/canto-desktop-shell"
[[ -f "$SHELL_BIN" ]] || { echo "desktop-shell binary missing" >&2; exit 1; }

echo "==> Assemble ${APP_NAME} (ADR-0070)"
APP="${OUT_DIR}/${APP_NAME}"
MACOS_DIR="${APP}/Contents/MacOS"
RES_DIR="${APP}/Contents/Resources"
RUNTIME_DIR="${RES_DIR}/runtime"
mkdir -p "$MACOS_DIR" "$RUNTIME_DIR"
cp "$SHELL_BIN" "${MACOS_DIR}/Canto-0243"
cp "$PYAPP_BIN" "${RUNTIME_DIR}/Canto-0243-runtime"
chmod +x "${MACOS_DIR}/Canto-0243" "${RUNTIME_DIR}/Canto-0243-runtime"

ICON_SRC="${ROOT}/client/public/icon-512.png"
if [[ ! -f "$ICON_SRC" ]]; then
  ICON_SRC="${ROOT}/client/dist-portable/icon-512.png"
fi
echo "==> AppIcon.icns from ${ICON_SRC}"
_make_app_icns "$ICON_SRC" "${RES_DIR}/AppIcon.icns"

cat > "${APP}/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>
  <string>Canto-0243</string>
  <key>CFBundleIdentifier</key>
  <string>${BUNDLE_ID}</string>
  <key>CFBundleName</key>
  <string>Canto-0243</string>
  <key>CFBundleDisplayName</key>
  <string>Canto-0243</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>${VER}</string>
  <key>CFBundleVersion</key>
  <string>${VER}</string>
  <key>CFBundleIconFile</key>
  <string>AppIcon</string>
  <key>LSMinimumSystemVersion</key>
  <string>11.0</string>
  <key>NSHighResolutionCapable</key>
  <true/>
</dict>
</plist>
EOF
echo -n "APPL????" > "${APP}/Contents/PkgInfo"

"$PY" "${ROOT}/scripts/warm_word_cache.py" "$OUT_DIR" || true

if command -v codesign >/dev/null 2>&1; then
  echo "==> Ad-hoc deep codesign ${APP_NAME} (S1)"
  codesign --force --deep --sign - "$APP"
  codesign --verify --verbose=2 "$APP" 2>&1 | head -20 || true
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
echo "Creators: extract folder → double-click ${APP_NAME} (Gatekeeper once; first run needs network)."
