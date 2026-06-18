#!/bin/bash
# macOS 創作者入口 — 雙擊開啟 Terminal，清下載隔離後啟動（免 .app 包裝）
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

if command -v xattr >/dev/null 2>&1; then
  xattr -dr com.apple.quarantine "$ROOT" 2>/dev/null || true
fi

exec /bin/bash "$ROOT/START.sh"
