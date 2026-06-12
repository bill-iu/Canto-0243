@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title 0243 Lyric Rhyme Workbench

where python >nul 2>&1
if errorlevel 1 (
  echo [錯誤] 找不到 Python。請安裝 Python 3.10 或以上並勾選 Add to PATH。
  echo https://www.python.org/downloads/
  pause
  exit /b 1
)

if not exist "lyrics.db" (
  echo [錯誤] 找不到 lyrics.db，請確認 portable 套件完整。
  pause
  exit /b 1
)

if not exist "venv\Scripts\python.exe" (
  echo [初次啟動] 建立虛擬環境並安裝依賴...
  python -m venv venv
  if errorlevel 1 (
    echo [錯誤] 無法建立 venv
    pause
    exit /b 1
  )
  call venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  if errorlevel 1 (
    echo [錯誤] 依賴安裝失敗
    pause
    exit /b 1
  )
) else (
  call venv\Scripts\activate.bat
)

set PORTABLE=1
set ENV=local
if not exist ".env.local" copy /Y "env.portable" ".env.local" >nul

set HOST=127.0.0.1
if defined PORT goto :have_port
set PORT=8000
:have_port

echo.
echo 啟動中... 瀏覽器將開啟 http://%HOST%:%PORT%/frontend/index.html
echo 關閉此視窗或按 Ctrl+C 可停止服務
echo.

start "" "http://%HOST%:%PORT%/frontend/index.html"
venv\Scripts\python.exe main.py

pause
