#!/usr/bin/env bash
# Intel Mac 維護者：一鍵建置 canto-0243-desktop-macos-x86_64.tar.gz (ADR-0068 PyApp)
# 詳見 docs/macos-maintainer.md
set -eu
[[ "${BASH_VERSINFO[0]:-0}" -ge 4 ]] && set -o pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export GH_REPO="${GH_REPO:-bill-iu/Canto-0243}"

TAG=""
UPLOAD=0
TEST=0
EXTRA=()

usage() {
  cat <<'EOF'
Usage: bash scripts/macos-tar.sh --tag vX.Y.Z [options]

Build dist/canto-0243-desktop-macos-x86_64.tar.gz on this Intel Mac (Desktop/PyApp).

Options:
  --tag TAG     Required. Git tag to build (checkout 由你喺 repo 自己做)
  --upload      Upload tar to existing GitHub Release (發佈補件)
  --test        After build, open dist/.../Canto-0243.command
  -h, --help    Show help

Examples:
  bash scripts/macos-tar.sh --tag v1.1.0
  bash scripts/macos-tar.sh --tag v1.1.0 --upload
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tag) TAG="$2"; shift 2 ;;
    --upload|--tar-only) UPLOAD=1; shift ;;
    --test) TEST=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) EXTRA+=("$1"); shift ;;
  esac
done

[[ -n "$TAG" ]] || { echo "error: --tag required" >&2; usage >&2; exit 1; }

args=(--tag "$TAG" --arch x86_64)
[[ "$UPLOAD" -eq 1 ]] && args+=(--upload)
[[ "$TEST" -eq 1 ]] && args+=(--test)
[[ ${#EXTRA[@]} -gt 0 ]] && args+=("${EXTRA[@]}")

exec bash "$ROOT/scripts/release-macos-local.sh" "${args[@]}"
