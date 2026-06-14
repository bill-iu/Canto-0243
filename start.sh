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

pip install -q -r requirements.txt 2>/dev/null || pip install -q fastapi uvicorn sqlalchemy pydantic python-multipart

echo "🌐 正在啟動後端..."
python main.py &
SERVER_PID=$!

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
BASE_URL="http://${HOST}:${PORT}"
URL="${BASE_URL}/frontend/index.html"

if ! python scripts/wait_for_url.py "${BASE_URL}/"; then
  echo "⚠️  後端啟動逾時，仍嘗試等待詞庫…"
fi

if ! python scripts/wait_for_url.py --ready "${BASE_URL}/ready"; then
  echo "⚠️  詞庫預載逾時，仍嘗試打開瀏覽器（搜尋可能較慢）…"
fi

echo "🔗 正在打開前端..."
if [[ "$(uname -s)" == "Darwin" ]]; then
  open "$URL" >/dev/null 2>&1 || true
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 || true
elif command -v start >/dev/null 2>&1; then
  start "$URL"
else
  echo "請手動打開：$URL"
fi

echo "✅ 已啟動（PID $SERVER_PID）"
echo "後端：${BASE_URL}"
echo "前端：$URL"
if [[ -n "${PORTABLE:-}" ]]; then
  echo "標題應顯示：Canto-0243 (移動版)"
fi
