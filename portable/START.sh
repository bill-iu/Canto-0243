#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" == "Darwin" ]] && command -v xattr >/dev/null 2>&1; then
  xattr -dr com.apple.quarantine "$ROOT" 2>/dev/null || true
fi

if [[ ! -f lyrics.db ]]; then
  echo "[錯誤] 找不到 lyrics.db，請確認套件完整解壓"
  exit 1
fi

RUN_PY="$ROOT/venv/bin/python"
if [[ ! -x "$RUN_PY" ]]; then
  if [[ "$(uname -s)" == "Linux" ]]; then
    echo "[Linux] 此套件未內建 Python 環境，請使用本機 Python 3.10+ 執行："
    echo "  python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && ./START.sh"
    exit 1
  fi
  echo "[錯誤] 找不到內建執行環境。請重新下載完整免安裝套件。"
  exit 1
fi

export PORTABLE=1
export ENV=local
[[ -f .env.local ]] || cp -f env.portable .env.local

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"
BASE_URL="http://${HOST}:${PORT}"
URL="${BASE_URL}/frontend/index.html"

echo ""
echo "啟動中... ${URL}"
echo "關閉請按 Ctrl+C"
echo ""

"$RUN_PY" scripts/free_port.py --port "$PORT" --host "$HOST" || true

PORT="$PORT" HOST="$HOST" "$RUN_PY" main.py &
SERVER_PID=$!

if ! "$RUN_PY" scripts/wait_for_url.py "${BASE_URL}/"; then
  echo "[警告] 後端啟動逾時，仍嘗試打開瀏覽器…"
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
  open "$URL" >/dev/null 2>&1 || true
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 || true
fi

"$RUN_PY" scripts/wait_for_url.py --gate "${BASE_URL}/ready" &

wait "$SERVER_PID"
