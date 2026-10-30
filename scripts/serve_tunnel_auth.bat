@echo off
chcp 65001 >nul
cd /d "%~dp0.."

echo ============================================================
echo  PCI-MED 公网访问（带密码，Cloudflare / Pinggy）
echo ============================================================
echo.
echo  这个窗口会先启动 8000 后端 + 认证代理，
echo  然后显示一个 https://....trycloudflare.com 地址（没有则用 Pinggy）。
echo  把地址、用户名、密码发给其他电脑即可，不需要同一 Wi-Fi。
echo.
echo  地址变化 / 断开后，重新双击本文件即可。
echo  关闭窗口会停止本次启动的服务。
echo.

where pwsh >nul 2>nul
if %errorlevel%==0 (
  pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0serve_tunnel_auth.ps1"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0serve_tunnel_auth.ps1"
)

echo.
pause