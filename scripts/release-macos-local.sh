#!/usr/bin/env bash
# Local macOS portable build + optional GitHub Release upload (bypass CI).
# ponytail: one machine = one native arch; use CI for both arm64 + x86_64.
set -eu
[[ "${BASH_VERSINFO[0]:-0}" -ge 4 ]] && set -o pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG=""
ARCH="auto"
UPLOAD=0
DRAFT=0
TEST=0
TAR_ONLY=0
NOTES_FILE=""
SKIP_README=1
GH_REPO="${GH_REPO:-}"

_gh() {
  if [[ -n "$GH_REPO" ]]; then
    gh -R "$GH_REPO" "$@"
  else
    gh "$@"
  fi
}

usage() {
  cat <<'EOF'
Usage: bash scripts/release-macos-local.sh --tag vX.Y.Z [options]

Build canto-0243-portable-macos-{arch}.tar.gz on this Mac and optionally upload
to an existing GitHub Release (no CI wait).

Options:
  --tag TAG          Required. Release tag (e.g. v1.6.5)
  --arch ARCH        auto (default), arm64, or x86_64 — must match this Mac's CPU
  --upload           Upload built tar via gh (see --tar-only)
  --tar-only         With --upload: only replace macOS tar (do not clobber lyrics.db/json)
  --draft            With --upload: create draft release if tag missing
  --notes-file PATH  Release notes when creating a new release
  --test             After build, open dist/Canto-0243.app (no download quarantine)
  --sync-readme      Run update_readme_words_count during build (default: skip)
  -h, --help         Show this help

Prerequisites:
  lyrics.db at repo root, python3, gh (for --upload), gh auth login
  Optional: GH_REPO=bill-iu/Canto-0243 when uploading from a fork clone

Examples:
  # Build + smoke on this Mac (fast iteration):
  bash scripts/release-macos-local.sh --tag v1.6.5 --test

  # After Windows published zip — Intel Mac uploads tar only to upstream:
  GH_REPO=bill-iu/Canto-0243 bash scripts/release-macos-local.sh --tag v1.6.5 --arch x86_64 --upload --tar-only

Sequoia download quarantine:
  Apps built here open without quarantine. After downloading from GitHub, Gatekeeper
  may show only 完成/移至垃圾桶 — use 系統設定 → 隱私與安全性 → 仍要開啟 (see portable/README.txt).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tag) TAG="$2"; shift 2 ;;
    --arch) ARCH="$2"; shift 2 ;;
    --upload) UPLOAD=1; shift ;;
    --tar-only) TAR_ONLY=1; shift ;;
    --draft) DRAFT=1; shift ;;
    --notes-file) NOTES_FILE="$2"; shift 2 ;;
    --test) TEST=1; shift ;;
    --sync-readme) SKIP_README=0; shift ;;
    -h|--help) usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

[[ "$(uname -s)" == "Darwin" ]] || {
  echo "error: macOS only (run on a Mac, not Windows CI)" >&2
  exit 1
}

[[ -n "$TAG" ]] || {
  echo "error: --tag is required" >&2
  usage >&2
  exit 1
}

[[ -f "$ROOT/lyrics.db" ]] || {
  echo "error: lyrics.db not found at repo root" >&2
  exit 1
}

host_arch() {
  case "$(uname -m)" in
    arm64|aarch64) echo arm64 ;;
    x86_64) echo x86_64 ;;
    *)
      echo "error: unsupported machine arch $(uname -m)" >&2
      exit 1
      ;;
  esac
}

HOST_ARCH="$(host_arch)"
if [[ "$ARCH" == "auto" ]]; then
  ARCH="$HOST_ARCH"
fi

if [[ "$ARCH" != "$HOST_ARCH" ]]; then
  echo "error: --arch $ARCH but this Mac is $HOST_ARCH (venv would be wrong CPU)" >&2
  exit 1
fi

TAR_PATH="$ROOT/dist/canto-0243-portable-macos-${ARCH}.tar.gz"
APP_DIR="$ROOT/dist/Canto-0243.app"

echo "==> Canto-0243 local macOS release"
echo "    tag:  $TAG"
echo "    arch: $ARCH (host $HOST_ARCH)"
echo "    root: $ROOT"
[[ -n "$GH_REPO" ]] && echo "    repo: $GH_REPO"

echo "==> Build portable..."
(
  export PORTABLE_MACOS_ARCH="$ARCH"
  export SKIP_README_SYNC="$SKIP_README"
  BUILD_PY="$ROOT/.build-python/python/bin/python3.12"
  if [[ ! -x "$BUILD_PY" ]]; then
    echo "==> Fetch build Python (standalone CPython 3.12)..."
    bash "$ROOT/scripts/fetch-macos-build-python.sh"
  fi
  export PORTABLE_BUILD_PYTHON="$BUILD_PY"
  bash "$ROOT/scripts/build-portable.sh"
)

[[ -f "$TAR_PATH" ]] || {
  echo "error: expected $TAR_PATH" >&2
  exit 1
}

if [[ -d "$APP_DIR" ]] && command -v codesign >/dev/null 2>&1; then
  echo "==> Codesign check..."
  codesign --verify --deep --strict "$APP_DIR" && echo "    codesign: OK"
  if command -v spctl >/dev/null 2>&1; then
    spctl -a -vv "$APP_DIR" 2>&1 || echo "    spctl: expected reject until notarized or user override"
  fi
fi

echo "==> Export words-lexicon.json..."
python3 "$ROOT/scripts/export_words_lexicon.py" -o "$ROOT/dist/words-lexicon.json"

tar_mb=$(du -m "$TAR_PATH" | cut -f1)
echo ""
echo "Built:"
echo "  $TAR_PATH (${tar_mb} MB)"
echo "  $ROOT/dist/words-lexicon.json"

if [[ "$TEST" -eq 1 ]]; then
  echo "==> Local smoke: open $APP_DIR"
  echo "    (same-machine build has no com.apple.quarantine — should launch)"
  open "$APP_DIR"
fi

if [[ "$UPLOAD" -eq 1 ]]; then
  command -v gh >/dev/null 2>&1 || {
    echo "error: gh CLI required for --upload" >&2
    exit 1
  }
  if ! _gh release view "$TAG" >/dev/null 2>&1; then
    title="Canto-0243 ${TAG}"
    if [[ "$DRAFT" -eq 1 ]]; then
      if [[ -n "$NOTES_FILE" ]]; then
        _gh release create "$TAG" --draft --title "$title" --notes-file "$NOTES_FILE"
      else
        _gh release create "$TAG" --draft --title "$title" --notes "macOS ${ARCH} local build"
      fi
    elif [[ -n "$NOTES_FILE" ]]; then
      _gh release create "$TAG" --title "$title" --notes-file "$NOTES_FILE"
    else
      _gh release create "$TAG" --title "$title" --notes "macOS ${ARCH} local build"
    fi
  fi
  echo "==> Upload to GitHub Release $TAG..."
  if [[ "$TAR_ONLY" -eq 0 ]]; then
    _gh release upload "$TAG" "$ROOT/lyrics.db" --clobber
    _gh release upload "$TAG" "$ROOT/dist/words-lexicon.json" --clobber
  fi
  _gh release upload "$TAG" "$TAR_PATH" --clobber
  if [[ -n "$GH_REPO" ]]; then
    repo="$GH_REPO"
  else
    repo="$(_gh repo view --json nameWithOwner -q .nameWithOwner)"
  fi
  echo ""
  echo "Uploaded: https://github.com/${repo}/releases/tag/${TAG}"
  echo "Asset: canto-0243-portable-macos-${ARCH}.tar.gz"
fi

echo ""
echo "Done. Downloaders on Sequoia: see portable/README.txt (隱私與安全性 → 仍要開啟)."
