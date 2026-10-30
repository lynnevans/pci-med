#requires -Version 5.1
<#
    一键启动「公网访问 + 密码保护」

    做的事：
      1. 检查 8000 后端；没启动就自动在后台启动；
      2. 生成/读取隧道用户名密码；
      3. 启动 scripts/auth_proxy.py（默认 8001），给所有请求加 Basic Auth；
      4. 用 Pinggy SSH 隧道把 8001 暴露成公网 HTTPS；
      5. 关闭窗口 / Ctrl+C 时，停掉本次启动的代理和后端。

    用法：
      双击 scripts\serve_tunnel_auth.bat
      或：
        pwsh -NoProfile -ExecutionPolicy Bypass -File scripts\serve_tunnel_auth.ps1

    想固定密码（可选）：
        $env:TUNNEL_USER="doctor"
        $env:TUNNEL_PASSWORD="你自己的密码"
        .\scripts\serve_tunnel_auth.bat
#>
$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root 'backend\venv\Scripts\python.exe'
$ProxyScript = Join-Path $Root 'scripts\auth_proxy.py'

if (-not (Test-Path -LiteralPath $Python)) {
    Write-Host "找不到 Python：$Python" -ForegroundColor Red
    Write-Host "请确认 backend\venv 已创建。" -ForegroundColor Yellow
    exit 1
}
if (-not (Test-Path -LiteralPath $ProxyScript)) {
    Write-Host "找不到代理脚本：$ProxyScript" -ForegroundColor Red
    exit 1
}

$backendProc = $null
$proxyProc = $null

function Test-Health {
    param(
        [int]$Port,
        [hashtable]$Headers = @{}
    )
    try {
        $null = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -Headers $Headers -TimeoutSec 2
        return $true
    } catch {
        return $false
    }
}

function Get-FreePort {
    param([int]$Start = 8001)
    for ($p = $Start; $p -le ($Start + 20); $p++) {
        $client = New-Object System.Net.Sockets.TcpClient
        try {
            $client.Connect('127.0.0.1', $p)
            $client.Close()
        } catch {
            $client.Close()
            return $p
        }
    }
    throw "8001–8021 都被占用了，请先关闭其它代理进程。"
}

try {
    $env:PYTHONIOENCODING = 'utf-8'

    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host " PCI-MED 公网访问（Cloudflare / Pinggy + Basic Auth）" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""

    # 1) 后端 8000
    if (Test-Health -Port 8000) {
        Write-Host "[1/4] 后端 8000 已在运行。" -ForegroundColor Green
    } else {
        Write-Host "[1/4] 后端 8000 未启动，正在后台启动..." -ForegroundColor Yellow
        $backendProc = Start-Process -FilePath $Python `
            -ArgumentList @('-m', 'uvicorn', 'api:app', '--host', '0.0.0.0', '--port', '8000') `
            -WorkingDirectory (Join-Path $Root 'backend') `
            -PassThru -WindowStyle Hidden
        $backendOk = $false
        for ($i = 0; $i -lt 40; $i++) {
            Start-Sleep -Milliseconds 500
            if (Test-Health -Port 8000) { $backendOk = $true; break }
        }
        if (-not $backendOk) {
            throw "后端 8000 启动失败。请先在 backend 目录运行：.\venv\Scripts\python.exe -m uvicorn api:app --host 0.0.0.0 --port 8000"
        }
        Write-Host "      后端 8000 已启动。" -ForegroundColor Green
    }

    # 2) 凭据
    $user = if ($env:TUNNEL_USER) { $env:TUNNEL_USER } else { 'doctor' }
    $pass = $env:TUNNEL_PASSWORD
    if (-not $pass) {
        $chars = (48..57) + (65..90) + (97..122)
        $pass = 'Pci-' + (-join ($chars | Get-Random -Count 10 | ForEach-Object { [char]$_ }))
    }
    $env:TUNNEL_USER = $user
    $env:TUNNEL_PASSWORD = $pass

    # 3) 认证代理（每次选一个空闲端口，避免和手动开的代理冲突）
    $proxyPort = Get-FreePort -Start 8001
    $env:TUNNEL_PORT = "$proxyPort"
    $env:TUNNEL_TARGET = 'http://127.0.0.1:8000'
    Write-Host "[2/4] 启动认证代理 127.0.0.1:$proxyPort ..." -ForegroundColor Yellow
    $proxyProc = Start-Process -FilePath $Python `
        -ArgumentList @($ProxyScript) `
        -WorkingDirectory $Root `
        -PassThru -WindowStyle Hidden

    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("${user}:${pass}"))
    $headers = @{ Authorization = "Basic $b64" }
    $proxyOk = $false
    for ($i = 0; $i -lt 30; $i++) {
        Start-Sleep -Milliseconds 400
        if (Test-Health -Port $proxyPort -Headers $headers) { $proxyOk = $true; break }
    }
    if (-not $proxyOk) {
        throw "认证代理启动失败（端口 $proxyPort）。可手动运行：$Python $ProxyScript"
    }
    Write-Host "      认证代理正常。" -ForegroundColor Green
    # 代理子进程已继承凭据；从当前环境移除，避免 cloudflared 日志打印密码
    Remove-Item Env:TUNNEL_PASSWORD -ErrorAction SilentlyContinue
    Remove-Item Env:TUNNEL_USER -ErrorAction SilentlyContinue

    # 4) 隧道
    Write-Host "[3/4] 准备公网隧道..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "------------------------------------------------------------" -ForegroundColor Cyan
    Write-Host " 用户名：$user" -ForegroundColor White
    Write-Host " 密码：  $pass" -ForegroundColor White
    Write-Host " 注意：浏览器第一次打开会弹登录框；用户名/密码就是上面两行。" -ForegroundColor Yellow
    Write-Host " 隧道输出里的 https://....trycloudflare.com（或 pinggy）就是地址。" -ForegroundColor Yellow
    Write-Host " 地址变化 / 断开后，重新双击本脚本即可生成新地址。" -ForegroundColor Yellow
    Write-Host " 关闭本窗口 / Ctrl+C 会停止本次代理和后端。" -ForegroundColor Yellow
    Write-Host "------------------------------------------------------------" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "[4/4] 正在连接，稍等几秒会出现公网地址..." -ForegroundColor Yellow
    Write-Host ""

    $cloudflared = $null
    $cmd = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($cmd) {
        $cloudflared = $cmd.Source
    } elseif (Test-Path -LiteralPath 'C:\Program Files (x86)\cloudflared\cloudflared.exe') {
        $cloudflared = 'C:\Program Files (x86)\cloudflared\cloudflared.exe'
    } elseif (Test-Path -LiteralPath 'C:\Program Files\cloudflared\cloudflared.exe') {
        $cloudflared = 'C:\Program Files\cloudflared\cloudflared.exe'
    }

    if ($cloudflared) {
        Write-Host "使用 Cloudflare Quick Tunnel（自动重连；地址形式 https://....trycloudflare.com）" -ForegroundColor Green
        & $cloudflared tunnel --url "http://127.0.0.1:$proxyPort" --no-autoupdate
    } else {
        Write-Host "未找到 cloudflared，回退 Pinggy（免费版约 60 分钟）。" -ForegroundColor Yellow
        Write-Host "想更稳定可先安装：winget install --id Cloudflare.cloudflared -e" -ForegroundColor Yellow
        & ssh -p 443 -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=20 -o ServerAliveCountMax=3 -o TCPKeepAlive=yes -o ExitOnForwardFailure=yes "-R0:localhost:$proxyPort" a.pinggy.io
    }
}
catch {
    Write-Host ""
    Write-Host "启动失败：$($_.Exception.Message)" -ForegroundColor Red
    Write-Host "如果校园网禁止 SSH 443，可换用其它隧道（见 docs\局域网访问.md）。" -ForegroundColor Yellow
}
finally {
    Write-Host ""
    Write-Host "正在清理本次启动的代理/后端..." -ForegroundColor DarkGray
    if ($proxyProc -and -not $proxyProc.HasExited) {
        Stop-Process -Id $proxyProc.Id -Force -ErrorAction SilentlyContinue
    }
    if ($backendProc -and -not $backendProc.HasExited) {
        Stop-Process -Id $backendProc.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "已停止。窗口可以关闭。" -ForegroundColor DarkGray
}