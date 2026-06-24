@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo Starting Canto-0243 (dev)...

set "PY=%~dp0venv\Scripts\python.exe"
if not exist "%PY%" (
  echo venv missing, creating...
  py -3.10 -m venv venv 2>nul || python -m venv venv
  set "PY=%~dp0venv\Scripts\python.exe"
)

if not exist "%PY%" (
  echo [ERROR] Failed to create venv. Install Python 3.10+ and retry.
  exit /b 1
)

"%PY%" -m pip install -q -r requirements.txt 2>nul

if not defined HOST set HOST=127.0.0.1
if not defined PORT set PORT=8000

REM ponytail: %~dp0 ends with \ which escapes the closing quote in cmd; %CD% is safe after cd above
"%PY%" scripts\local_launch.py --tail-ready --no-wait-server --python "%PY%" --root "%CD%"
