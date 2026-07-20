@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title Canto-0243

rem ADR-0067: extract venv.pack before any venv python runs
if exist "%~dp0venv.pack" (
  if not exist "%~dp0venv\.portable-venv-extracted" (
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\portable_ensure_venv.ps1" -Root "%~dp0."
    if errorlevel 1 (
      echo [ERROR] Runtime extract failed. Re-download the full portable package if it keeps failing.
      pause
      exit /b 1
    )
  )
)

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

if not exist "client\dist-portable\index.html" (
  echo [ERROR] Product UI missing: client\dist-portable\index.html
  echo Re-download the full portable zip, or from a source checkout run:
  echo   cd client ^&^& npm run build:portable
  pause
  exit /b 1
)

rem #66: rewrite pyvenv.cfg home to this extract before any venv python runs
set "PYHOME=%~dp0venv\python-home"
set "PYCFG=%~dp0venv\pyvenv.cfg"
if exist "%PYHOME%\python.exe" if exist "%PYCFG%" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$cfg = $env:PYCFG; $h = (Resolve-Path -LiteralPath $env:PYHOME).Path; $lines = Get-Content -LiteralPath $cfg; $out = foreach ($line in $lines) { if ($line -match '^home = ') { 'home = ' + $h } else { $line } }; Set-Content -LiteralPath $cfg -Value $out -Encoding ascii"
)

set PORTABLE=1
set ENV=local
if not exist ".env.local" copy /Y "env.portable" ".env.local" >nul

set HOST=127.0.0.1
if defined PORT goto :have_port
set PORT=8000
:have_port

"%PY%" scripts\local_launch.py --portable --lang en --wait-server --pause-on-exit
