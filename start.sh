#!/usr/bin/env bash
# Canto-0243 一鍵啟動腳本（開發用）
# 移動版請用：PORTABLE=1 ./start.sh  或  ./start.sh --portable
# portable 套件請用目錄內的 START.sh / START.command

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

for arg in "$@"; do
  case "$arg" in
    --portable|-p) export PORTABLE=1 ;;
  esac
done

if [[ -n "${PORTABLE:-}" ]]; then
  echo "📦 移動版模式（PORTABLE=1）"
  export ENV="${ENV:-local}"
  [[ -f .env.local ]] || [[ ! -f env.portable ]] || cp -f env.portable .env.local
else
  echo "🚀 正在啟動 Canto-0243（開發版）..."
fi

if [[ -d venv ]]; then
  # shellcheck disable=SC1091
  if [[ -f venv/bin/activate ]]; then
    source venv/bin/activate
  else
    source venv/Scripts/activate
  fi
  echo "✅ 已進入虛擬環境 (venv)"
else
  echo "⚠️  虛擬環境不存在，正在建立..."
  python3 -m venv venv 2>/dev/null || python -m venv venv
  # shellcheck disable=SC1091
  if [[ -f venv/bin/activate ]]; then
    source venv/bin/activate
  else
    source venv/Scripts/activate
  fi
  pip install -r requirements.txt 2>/dev/null || pip install fastapi uvicorn sqlalchemy pydantic python-multipart
fi

REQS="requirements.txt"
STAMP=".venv-reqs.stamp"
if [[ -f "$REQS" ]]; then
  HASH="$(python -c "import hashlib, pathlib; print(hashlib.sha256(pathlib.Path('$REQS').read_bytes()).hexdigest()[:16])")"
  if [[ ! -f "$STAMP" ]] || [[ "$(cat "$STAMP")" != "$HASH" ]]; then
    pip install -q -r "$REQS" 2>/dev/null || pip install -q fastapi uvicorn sqlalchemy pydantic python-multipart
    echo "$HASH" > "$STAMP"
  fi
fi

export HOST="${HOST:-127.0.0.1}"
export PORT="${PORT:-8000}"

LAUNCH=(python scripts/local_launch.py --tail-ready --no-wait-server)
if [[ -n "${PORTABLE:-}" ]]; then
  LAUNCH+=(--portable --wait-server --lang zh)
fi

"${LAUNCH[@]}" &
