#!/usr/bin/env bash
# macOS Desktop (PyApp) build + tar-only upload to an existing Release (ADR-0068 / 0044 §5).
# ponytail: one machine = one native arch; publisher channel is Windows.
set -eu
[[ "${BASH_VERSINFO[0]:-0}" -ge 4 ]] && set -o pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TAG=""
ARCH="auto"
UPLOAD=0
TEST=0
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

Build canto-0243-desktop-macos-{arch}.tar.gz on this Mac (PyApp + wheel + sidecar).
With --upload, only replaces the macOS Desktop tar on an existing Release
(publisher role must run first).

Options:
  --tag TAG          Required. Release tag (e.g. v1.1.0)
  --arch ARCH        auto (default), arm64, or x86_64 — must match this Mac's CPU
  --upload           Upload tar only via gh (Release must already exist)
  --tar-only         Accepted alias for --upload
  --test             After build, open dist/canto-0243-desktop/Canto-0243.app
  --sync-readme      Accepted for parity with older callers (no-op; Desktop build skips)
  -h, --help         Show this help

Prerequisites:
  --upload: gh auth, GH_REPO=bill-iu/Canto-0243 (fork clone), git checkout at TAG,
            Release must already exist (publisher role)
  build: lyrics.db from Release $TAG when available (--upload requires it; no build-db)
  cargo (rustup); python3; client: npm run build:portable; data/rime/char.csv (fetch script)

Examples:
  bash scripts/release-macos-local.sh --tag v1.1.0 --test

  GH_REPO=bill-iu/Canto-0243 bash scripts/release-macos-local.sh --tag v1.1.0 --arch x86_64 --upload

Sequoia: after download, Gatekeeper may need 系統設定 → 隱私與安全性 → 仍要開啟
(see portable/README.txt). First run needs network (PyApp CPython 3.11).
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
    --sync-readme) shift ;; # no-op: Desktop path has no README word-count step here
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
  echo "error: --arch $ARCH but this Mac is $HOST_ARCH (native PyApp binary would be wrong CPU)" >&2
  exit 1
fi

_verify_at_tag_commit() {
  local tag_commit head_commit
  tag_commit="$(git -C "$ROOT" rev-parse "${TAG}^{commit}")" || {
    echo "error: unknown git tag $TAG (git fetch origin --tags?)" >&2
    exit 1
  }
  head_commit="$(git -C "$ROOT" rev-parse HEAD)"
  if [[ "$tag_commit" != "$head_commit" ]]; then
    echo "error: HEAD ($head_commit) != $TAG ($tag_commit); run: git checkout $TAG" >&2
    exit 1
  fi
}

_assert_release_source() {
  git -C "$ROOT" fetch origin main dev --quiet || {
    echo "error: failed to fetch origin/main and origin/dev" >&2
    exit 1
  }
  if ! git -C "$ROOT" merge-base --is-ancestor "${TAG}^{commit}" origin/main; then
    echo "error: $TAG is not reachable from origin/main; tag from latest main after dev is merged" >&2
    exit 1
  fi
  # Tar-only refresh: product is the tag on main. Tooling commits may sit on dev only.
  if ! git -C "$ROOT" merge-base --is-ancestor origin/dev origin/main; then
    if command -v gh >/dev/null 2>&1 && _gh release view "$TAG" >/dev/null 2>&1; then
      echo "warn: origin/dev not fully merged into origin/main; continuing tar refresh for existing Release $TAG" >&2
    else
      echo "error: origin/dev is not merged into origin/main; merge dev first, then rebuild release assets" >&2
      exit 1
    fi
  fi
}

_sync_published_lexicon() {
  local require_release="${1:-0}"
  echo "==> Sync lyrics.db from Release $TAG (Release asset preferred; no build-db)..."

  if command -v gh >/dev/null 2>&1 && _gh release view "$TAG" >/dev/null 2>&1; then
    _gh release download "$TAG" -p "lyrics.db" -D "$ROOT" --clobber
    echo "    downloaded lyrics.db from Release $TAG"
    return 0
  fi

  if [[ "$require_release" -eq 1 ]]; then
    echo "error: --upload requires Release $TAG with lyrics.db (ignore stale local copy)" >&2
    exit 1
  fi

  if [[ -f "$ROOT/lyrics.db" ]]; then
    echo "    Release unavailable; using local lyrics.db"
    return 0
  fi

  echo "error: lyrics.db not found (Release $TAG or local)" >&2
  exit 1
}

_ensure_client_portable() {
  if [[ -f "$ROOT/client/dist-portable/index.html" ]]; then
    return 0
  fi
  echo "==> client/dist-portable missing — npm run build:portable..."
  (
    cd "$ROOT/client"
    if [[ ! -d node_modules ]]; then
      npm ci
    fi
    npm run build:portable
  )
}

_ensure_rime_char() {
  if [[ -f "$ROOT/data/rime/char.csv" ]]; then
    return 0
  fi
  echo "==> data/rime/char.csv missing — fetch_rime_data.py..."
  python3 "$ROOT/scripts/fetch/fetch_rime_data.py"
}

_verify_at_tag_commit
_assert_release_source

if [[ "$UPLOAD" -eq 1 ]]; then
  command -v gh >/dev/null 2>&1 || {
    echo "error: gh CLI required for --upload" >&2
    exit 1
  }
  if ! _gh release view "$TAG" >/dev/null 2>&1; then
    echo "error: Release $TAG does not exist — publisher role must publish first" >&2
    exit 1
  fi
  _sync_published_lexicon 1
elif command -v gh >/dev/null 2>&1 && _gh release view "$TAG" >/dev/null 2>&1; then
  _sync_published_lexicon 0
fi

[[ -f "$ROOT/lyrics.db" ]] || {
  echo "error: lyrics.db not found at repo root (local or Release $TAG)" >&2
  exit 1
}

command -v cargo >/dev/null 2>&1 || {
  echo "error: cargo required for Desktop/PyApp (install: https://rustup.rs )" >&2
  exit 1
}

_ensure_client_portable
_ensure_rime_char

TAR_PATH="$ROOT/dist/canto-0243-desktop-macos-${ARCH}.tar.gz"
BUNDLE_DIR="$ROOT/dist/canto-0243-desktop"
ENTRY_APP="$BUNDLE_DIR/Canto-0243.app"
MANIFEST_SIDECAR="$ROOT/dist/portable-manifest-macos-${ARCH}.json"

echo "==> Canto-0243 local macOS Desktop release (PyApp)"
echo "    tag:  $TAG"
echo "    arch: $ARCH (host $HOST_ARCH)"
echo "    root: $ROOT"
[[ -n "$GH_REPO" ]] && echo "    repo: $GH_REPO"

echo "==> Build Desktop (build-desktop.sh)..."
(
  export DESKTOP_MACOS_ARCH="$ARCH"
  export PORTABLE_MACOS_ARCH="$ARCH"
  export DESKTOP_RELEASE_TAG="$TAG"
  export PORTABLE_RELEASE_TAG="$TAG"
  bash "$ROOT/scripts/build-desktop.sh"
)

[[ -f "$TAR_PATH" ]] || {
  echo "error: expected $TAR_PATH" >&2
  exit 1
}

if [[ -d "$ENTRY_APP" ]] && command -v codesign >/dev/null 2>&1; then
  echo "==> Codesign check (Canto-0243.app)..."
  codesign --verify --verbose=2 "$ENTRY_APP" 2>&1 | head -15 || true
fi

tar_mb=$(du -m "$TAR_PATH" | cut -f1)
echo ""
echo "Built:"
echo "  $TAR_PATH (${tar_mb} MB)"
[[ -f "$MANIFEST_SIDECAR" ]] && echo "  $MANIFEST_SIDECAR"
[[ -d "$ENTRY_APP" ]] && echo "  $ENTRY_APP"

if [[ "$TEST" -eq 1 ]]; then
  echo "==> Local smoke: open $ENTRY_APP"
  echo "    First run needs network (PyApp installs CPython 3.11)."
  open "$ENTRY_APP"
fi

if [[ "$UPLOAD" -eq 1 ]]; then
  echo "==> Upload to GitHub Release $TAG (Desktop tar + manifest)..."
  _gh release upload "$TAG" "$TAR_PATH" --clobber
  if [[ -f "$MANIFEST_SIDECAR" ]]; then
    _gh release upload "$TAG" "$MANIFEST_SIDECAR" --clobber
  else
    echo "WARN: missing $MANIFEST_SIDECAR (套件更新提示 will not detect this build)" >&2
  fi
  # Drop legacy portable asset name if still on the Release (ADR-0068)
  if _gh release view "$TAG" --json assets -q '.assets[].name' 2>/dev/null | grep -qx "canto-0243-portable-macos-${ARCH}.tar.gz"; then
    echo "==> Remove legacy portable tar from Release..."
    _gh release delete-asset "$TAG" "canto-0243-portable-macos-${ARCH}.tar.gz" --yes || true
  fi
  if [[ -n "$GH_REPO" ]]; then
    repo="$GH_REPO"
  else
    repo="$(_gh repo view --json nameWithOwner -q .nameWithOwner)"
  fi
  echo ""
  echo "Uploaded: https://github.com/${repo}/releases/tag/${TAG}"
  echo "Asset: canto-0243-desktop-macos-${ARCH}.tar.gz"
fi

echo ""
echo "Done. Creators: extract folder → double-click Canto-0243.app (Gatekeeper once; first run may need network)."
