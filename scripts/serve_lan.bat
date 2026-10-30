@echo off
cd /d "%~dp0.."
where pwsh >nul 2>nul
if %errorlevel%==0 (
  pwsh -NoProfile -File "%~dp0serve_lan.ps1"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0serve_lan.ps1"
)
pause