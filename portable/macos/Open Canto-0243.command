#!/bin/bash
# macOS 備用入口 — 清下載隔離後開啟 .app（Gatekeeper 阻擋雙擊時用）
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
APP="$DIR/Canto-0243.app"

if [[ ! -d "$APP" ]]; then
  osascript -e 'display alert "Canto-0243" message "找不到 Canto-0243.app。請完整解壓 tar。" as critical' || true
  exit 1
fi

if command -v xattr >/dev/null 2>&1; then
  xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true
fi

exec open "$APP"
