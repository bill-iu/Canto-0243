#!/usr/bin/env bash
# macOS portable build + tar-only upload to an existing upstream Release (ADR-0018).
# ponytail: one machine = one native arch; publisher channel is Windows.
set -eu
[[ "${BASH_VERSINFO[0]:-0}" -ge 4 ]] && set -o pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG=""
ARCH="auto"
UPLOAD=0
TEST=0
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

Build canto-0243-portable-macos-{arch}.tar.gz on this Mac. With --upload, only
replaces the macOS tar on an existing Release (publisher role must run first).

Options:
  --tag TAG          Required. Release tag (e.g. v1.6.5)
  --arch ARCH        auto (default), arm64, or x86_64 — must match this Mac's CPU
  --upload           Upload tar only via gh (Release must already exist)
  --tar-only         Accepted alias for --upload (tar-only is the only upload mode)
  --test             After build, open dist/canto-0243-portable/Canto-0243.command
  --sync-readme      Run update_readme_words_count during build (default: skip)
  -h, --help         Show this help

Prerequisites:
  --upload: gh auth, GH_REPO=bill-iu/Canto-0243 (fork clone), git checkout at TAG,
            Release must already exist (publisher role)
  build: lyrics.db at repo root (upload syncs from Release before build)
  python3; optional .build-python/ via scripts/fetch-macos-build-python.sh

Examples:
  bash scripts/release-macos-local.sh --tag v1.6.5 --test

  GH_REPO=bill-iu/Canto-0243 bash scripts/release-macos-local.sh --tag v1.6.5 --arch x86_64 --upload

Sequoia download quarantine:
  Apps built here open without quarantine. After downloading from GitHub, Gatekeeper
  may show only 完成/移至垃圾桶 — use 系統設定 → 隱私與安全性 → 仍要開啟 (see portable/README.txt).
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tag) TAG="$2"; shift 2 ;;
    --arch) ARCH="$2"; shift 2 ;;
    --upload|--tar-only) UPLOAD=1; shift ;;
    --draft|--notes-file)
      echo "error: $1 removed — publisher role creates Release and notes" >&2
      exit 1
      ;;
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

_verify_at_tag_commit() {
  local tag_commit head_commit
  tag_commit="$(git -C "$ROOT" rev-parse "${TAG}^{commit}")" || {
    echo "error: unknown git tag $TAG (git fetch upstream --tags?)" >&2
    exit 1
  }
  head_commit="$(git -C "$ROOT" rev-parse HEAD)"
  if [[ "$tag_commit" != "$head_commit" ]]; then
    echo "error: HEAD ($head_commit) != $TAG ($tag_commit); run: git checkout $TAG" >&2
    exit 1
  fi
}

_sync_published_lexicon() {
  echo "==> Sync 發佈詞庫快照 from Release $TAG..."
  _gh release download "$TAG" -p "lyrics.db" -D "$ROOT" --clobber
}

if [[ "$UPLOAD" -eq 1 ]]; then
  command -v gh >/dev/null 2>&1 || {
    echo "error: gh CLI required for --upload" >&2
    exit 1
  }
  if ! _gh release view "$TAG" >/dev/null 2>&1; then
    echo "error: Release $TAG does not exist — publisher role must publish first" >&2
    exit 1
  fi
  _verify_at_tag_commit
  _sync_published_lexicon
fi

[[ -f "$ROOT/lyrics.db" ]] || {
  echo "error: lyrics.db not found at repo root" >&2
  exit 1
}

TAR_PATH="$ROOT/dist/canto-0243-portable-macos-${ARCH}.tar.gz"
BUNDLE_DIR="$ROOT/dist/canto-0243-portable"
ENTRY_CMD="$BUNDLE_DIR/Canto-0243.command"

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

if [[ -x "$ENTRY_CMD" ]] && command -v codesign >/dev/null 2>&1; then
  echo "==> Codesign check..."
  codesign --verify --strict "$ENTRY_CMD" && echo "    Canto-0243.command: OK"
fi

echo "==> Export words-lexicon.json (local dist only; not uploaded by this script)..."
python3 "$ROOT/scripts/export_words_lexicon.py" -o "$ROOT/dist/words-lexicon.json"

tar_mb=$(du -m "$TAR_PATH" | cut -f1)
echo ""
echo "Built:"
echo "  $TAR_PATH (${tar_mb} MB)"
echo "  $ROOT/dist/words-lexicon.json"

if [[ "$TEST" -eq 1 ]]; then
  echo "==> Local smoke: open $ENTRY_CMD"
  echo "    (same-machine build has no com.apple.quarantine — should launch)"
  open "$ENTRY_CMD"
fi

if [[ "$UPLOAD" -eq 1 ]]; then
  echo "==> Upload to GitHub Release $TAG (tar only)..."
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
