@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title Canto-0243

where python >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Python not found. Install Python 3.10+ and check "Add to PATH".
  echo https://www.python.org/downloads/
  pause
  exit /b 1
)

if not exist "lyrics.db" (
  echo [ERROR] lyrics.db not found. Extract the full portable package.
  pause
  exit /b 1
)

if not exist "venv\Scripts\python.exe" (
  echo [First run] Creating virtual environment and installing dependencies...
  python -m venv venv
  if errorlevel 1 (
    echo [ERROR] Failed to create venv
    pause
    exit /b 1
  )
  call venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  pip install -r requirements.txt
  if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
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
echo Starting server... Browser will open after backend is ready.
echo Close this window or press Ctrl+C to stop.
echo.

start /B cmd /c "venv\Scripts\python.exe scripts\wait_for_url.py http://%HOST%:%PORT%/ && start \"\" http://%HOST%:%PORT%/frontend/index.html && venv\Scripts\python.exe scripts\wait_for_url.py --gate http://%HOST%:%PORT%/ready"
venv\Scripts\python.exe main.py

pause
