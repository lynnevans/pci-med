@echo off
setlocal
cd /d "%~dp0..\backend"

if not exist "requirements.txt" (
  echo [ERROR] backend\requirements.txt not found.
  pause
  exit /b 1
)

if not exist "venv\Scripts\python.exe" (
  echo Creating backend\venv ...
  python -m venv venv
  if errorlevel 1 (
    echo [ERROR] python -m venv failed. Install Python 3.12 and retry.
    pause
    exit /b 1
  )
)

echo Installing backend requirements...
venv\Scripts\python.exe -m pip install --upgrade pip
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] pip install failed.
  pause
  exit /b 1
)

if not exist ".env" (
  if exist ".env.example" (
    copy ".env.example" ".env" >nul
    echo Created backend\.env from .env.example
    echo Edit backend\.env and fill DEEPSEEK_API_KEY / DASHSCOPE_API_KEY.
  )
)

echo.
echo Backend environment is ready.
echo Run scripts\serve_local.bat to start.
pause
