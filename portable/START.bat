@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title Canto-0243

set "PY=%~dp0venv\Scripts\python.exe"
if not exist "%PY%" (
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

"%PY%" scripts\local_launch.py --portable --lang en --wait-server --pause-on-exit
