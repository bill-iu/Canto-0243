@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title Canto-0243

rem ADR-0068 Desktop: outer shell (or runtime if shell missing)
if exist "%~dp0Canto-0243.exe" (
  set CANTO_PAYLOAD_ROOT=%~dp0
  set PORTABLE=1
  set ENV=local
  if not exist ".env.local" if exist "env.portable" copy /Y "env.portable" ".env.local" >nul
  echo Starting Desktop launcher (first run may need network for CPython 3.11)...
  start "" "%~dp0Canto-0243.exe"
  exit /b 0
)
if exist "%~dp0runtime\Canto-0243-runtime.exe" (
  set CANTO_PAYLOAD_ROOT=%~dp0
  set PORTABLE=1
  set ENV=local
  start "" "%~dp0runtime\Canto-0243-runtime.exe"
  exit /b 0
)

rem Legacy Portable venv path (build-portable-legacy.ps1 / old zips)
if exist "%~dp0venv.pack" (
  if not exist "%~dp0venv\.portable-venv-extracted" (
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\portable_ensure_venv.ps1" -Root "%~dp0."
    if errorlevel 1 (
      echo [ERROR] Runtime extract failed. Re-download the full package if it keeps failing.
      pause
      exit /b 1
    )
  )
)

set "PY=%~dp0venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERROR] No Canto-0243.exe and no bundled venv. Re-download the Desktop package.
  pause
  exit /b 1
)

if not exist "lyrics.db" (
  echo [ERROR] lyrics.db not found. Extract the full package.
  pause
  exit /b 1
)

if not exist "client\dist-portable\index.html" (
  echo [ERROR] Product UI missing: client\dist-portable\index.html
  pause
  exit /b 1
)

set "PYHOME=%~dp0venv\python-home"
set "PYCFG=%~dp0venv\pyvenv.cfg"
if exist "%PYHOME%\python.exe" if exist "%PYCFG%" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$cfg = $env:PYCFG; $h = (Resolve-Path -LiteralPath $env:PYHOME).Path; $lines = Get-Content -LiteralPath $cfg; $out = foreach ($line in $lines) { if ($line -match '^home = ') { 'home = ' + $h } else { $line } }; Set-Content -LiteralPath $cfg -Value $out -Encoding ascii"
)

set PORTABLE=1
set ENV=local
if not exist ".env.local" if exist "env.portable" copy /Y "env.portable" ".env.local" >nul

set HOST=127.0.0.1
if defined PORT goto :have_port
set PORT=8000
:have_port

"%PY%" scripts\local_launch.py --portable --lang en --wait-server --pause-on-exit
if errorlevel 1 pause
