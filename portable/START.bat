@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title Canto-0243

set "PY=%~dp0venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERROR] 找不到內建執行環境。請重新下載完整免安裝套件。
  echo [ERROR] Bundled runtime missing. Re-download the full portable package.
  pause
  exit /b 1
)

if not exist "lyrics.db" (
  echo [ERROR] lyrics.db not found. Extract the full portable package.
  pause
  exit /b 1
)

set PORTABLE=1
set ENV=local
if not exist ".env.local" copy /Y "env.portable" ".env.local" >nul

set HOST=127.0.0.1
if defined PORT goto :have_port
set PORT=8000
:have_port

echo.
echo Starting Canto-0243... Browser opens when backend is ready.
echo Close this window or press Ctrl+C to stop.
echo.

start /B cmd /c ""%PY%" scripts\wait_for_url.py http://%HOST%:%PORT%/ && start \"\" http://%HOST%:%PORT%/frontend/index.html && "%PY%" scripts\wait_for_url.py --gate http://%HOST%:%PORT%/ready"
"%PY%" main.py

pause
