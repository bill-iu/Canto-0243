#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ "$(uname -s)" == "Darwin" ]] && command -v xattr >/dev/null 2>&1; then
  xattr -dr com.apple.quarantine "$ROOT" 2>/dev/null || true
fi

if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
  echo "[錯誤] 找不到 Python 3.10+"
  echo "macOS 可安裝：brew install python@3.12  或從 https://www.python.org/downloads/ 下載"
  exit 1
fi

PY=python3
command -v python3 >/dev/null 2>&1 || PY=python

if [[ ! -f lyrics.db ]]; then
  echo "[錯誤] 找不到 lyrics.db，請確認套件完整解壓"
  exit 1
fi

if [[ ! -d venv ]]; then
  echo "[初次啟動] 建立虛擬環境並安裝依賴（約 1–3 分鐘）..."
  "$PY" -m venv venv
  # shellcheck disable=SC1091
  source venv/bin/activate
  python -m pip install --upgrade pip
  pip install -r requirements.txt
else
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

RUN_PY="$ROOT/venv/bin/python"
if [[ ! -x "$RUN_PY" ]]; then
  echo "[錯誤] venv 損壞，請刪除 venv 資料夾後重試"
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

"$RUN_PY" main.py &
SERVER_PID=$!

# HTTP up first, then word-cache /ready (progress echoed by wait_for_url.py)
if ! "$RUN_PY" scripts/wait_for_url.py "${BASE_URL}/"; then
  echo "[警告] 後端啟動逾時，仍嘗試打開瀏覽器…"
fi
if ! "$RUN_PY" scripts/wait_for_url.py --ready "${BASE_URL}/ready"; then
  echo "[警告] 詞庫預載逾時，仍嘗試打開瀏覽器（搜尋可能較慢）…"
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
  open "$URL" >/dev/null 2>&1 || true
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$URL" >/dev/null 2>&1 || true
fi

wait "$SERVER_PID"
