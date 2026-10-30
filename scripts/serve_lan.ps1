# 局域网单端口启动：构建前端 + FastAPI 托管 dist
# 用法（在项目根目录或任意位置）：powershell -ExecutionPolicy Bypass -File scripts\serve_lan.ps1
# 其他电脑访问脚本打印的 http://<本机IP>:8000

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot

Write-Host '[1/2] 构建前端...' -ForegroundColor Cyan
Push-Location (Join-Path $root 'frontend')
try {
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw '前端构建失败' }
} finally {
    Pop-Location
}

Write-Host '[2/2] 启动后端：0.0.0.0:8000' -ForegroundColor Cyan
Write-Host ''
Write-Host '其他电脑（同一 Wi-Fi/局域网）可访问：' -ForegroundColor Yellow
$ips = @()
try {
    $ips = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
        Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
        Select-Object -ExpandProperty IPAddress -Unique
} catch { }
if (-not $ips) {
    Write-Host '  未自动识别到 IPv4，请运行 ipconfig 查看 WLAN/以太网的 IPv4 地址' -ForegroundColor Yellow
} else {
    foreach ($ip in $ips) { Write-Host "  http://$ip`:8000" -ForegroundColor Green }
}
Write-Host ''
Write-Host '如果其他电脑连不上：检查 Windows 防火墙是否放行 TCP 8000（见 docs/局域网访问.md）' -ForegroundColor DarkGray
Write-Host '按 Ctrl+C 停止服务' -ForegroundColor DarkGray
Write-Host ''

Push-Location (Join-Path $root 'backend')
try {
    & .\venv\Scripts\python.exe -m uvicorn api:app --host 0.0.0.0 --port 8000
} finally {
    Pop-Location
}