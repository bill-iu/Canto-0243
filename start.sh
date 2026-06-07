#!/bin/bash
# 0243 押韻字典 一鍵啟動腳本

echo "🚀 正在啟動 0243 押韻字典..."

# 1. 檢查並啟動虛擬環境
if [ -d "venv" ]; then
    echo "✅ 找到虛擬環境，正在啟用..."
    source venv/Scripts/activate  # Windows Git Bash
else
    echo "⚠️  虛擬環境不存在，正在建立..."
    python -m venv venv
    source venv/Scripts/activate
    pip install fastapi uvicorn sqlalchemy pydantic python-multipart pycantonese pyjyutping
fi

# 2. 安裝/更新依賴
echo "📦 安裝依賴套件..."
pip install -q fastapi uvicorn sqlalchemy pydantic python-multipart

# 3. 啟動後端（背景執行）
echo "🌐 正在啟動後端伺服器..."
python main.py &

# 等待後端啟動
sleep 3

# 4. 自動打開前端
echo "🔗 正在打開前端..."
if command -v start &> /dev/null; then
    start http://127.0.0.1:8000/frontend/index.html
elif command -v xdg-open &> /dev/null; then
    xdg-open http://127.0.0.1:8000/frontend/index.html
else
    echo "請手動打開：http://127.0.0.1:8000/frontend/index.html"
fi

echo "✅ 0243 押韻字典已啟動！"
echo "後端：http://127.0.0.1:8000"
echo "前端：http://127.0.0.1:8000/frontend/index.html"