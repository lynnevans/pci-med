@echo off
setlocal
cd /d "%~dp0.."

echo ============================================================
echo  PCI-MED public access (password protected)
echo ============================================================
echo.
echo  This window starts backend:8000 + auth proxy, then a public HTTPS URL.
echo  Send the URL, username and password to other computers.
echo  No same Wi-Fi required.
echo.
echo  Close this window to stop the services started here.
echo.

where pwsh >nul 2>nul
if %errorlevel%==0 (
  pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0serve_tunnel_auth.ps1"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0serve_tunnel_auth.ps1"
)

pause
