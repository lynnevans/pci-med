@echo off
setlocal
cd /d "%~dp0..\backend"

if not exist "venv\Scripts\python.exe" (
  echo [ERROR] backend\venv\Scripts\python.exe not found.
  echo Run scripts\setup_backend.bat first.
  pause
  exit /b 1
)

venv\Scripts\python.exe -c "import fastapi, uvicorn" >nul 2>nul
if errorlevel 1 (
  echo [ERROR] backend\venv exists, but dependencies are not installed.
  echo Run scripts\setup_backend.bat and wait until it finishes.
  pause
  exit /b 1
)

echo ============================================================
echo  PCI-MED local server
echo  Open http://127.0.0.1:8000/ after startup
echo  Press Ctrl+C to stop
echo ============================================================
echo.

venv\Scripts\python.exe -m uvicorn api:app --host 0.0.0.0 --port 8000

pause
