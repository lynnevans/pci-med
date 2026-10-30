#!/usr/bin/env python
"""带 HTTP Basic Auth 的反向代理，给公网隧道加一道密码门。

拓扑：
    Pinggy HTTPS  ->  127.0.0.1:8001 (本脚本)  ->  127.0.0.1:8000 (uvicorn)

为什么需要它：
    Pinggy 免费隧道是公开 URL，应用本身没有登录。这里用 Basic Auth
    把所有请求（页面、/api/analyze、/api/ocr、/api/chat 的 SSE）都保护起来。
    浏览器第一次打开会弹用户名/密码框，之后同源请求会自动带上。

启动：
    cd C:\\Users\\sakura\\pci-med
    $env:TUNNEL_USER="doctor"
    $env:TUNNEL_PASSWORD="换成你自己的密码"
    backend\\venv\\Scripts\\python.exe scripts\\auth_proxy.py

默认监听 127.0.0.1:8001，转发到 http://127.0.0.1:8000。
（只给本机的 cloudflared/ssh 隧道连，不在局域网多开一个入口。）
"""
from __future__ import annotations

import asyncio
import base64
import hmac
import os
import sys

from aiohttp import ClientSession, ClientTimeout, web

TARGET = os.getenv("TUNNEL_TARGET", "http://127.0.0.1:8000").rstrip("/")
HOST = os.getenv("TUNNEL_HOST", "127.0.0.1")
PORT = int(os.getenv("TUNNEL_PORT", "8001"))
USER = os.getenv("TUNNEL_USER", "doctor")
PASSWORD = os.getenv("TUNNEL_PASSWORD", "")

REQ_SKIP = {
    "host", "authorization", "connection", "keep-alive",
    "proxy-authenticate", "proxy-authorization", "te", "trailers",
    "transfer-encoding", "upgrade", "content-length", "accept-encoding",
}
RESP_SKIP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "content-length",
    "content-encoding",
}

if not PASSWORD:
    print("ERROR: 请先设置 TUNNEL_PASSWORD 环境变量，例如：", file=sys.stderr)
    print('  $env:TUNNEL_PASSWORD="Pci-你的密码"', file=sys.stderr)
    raise SystemExit(2)

SESSION: ClientSession | None = None


def unauthorized() -> web.Response:
    return web.Response(
        status=401,
        text="需要登录：请输入管理员提供的用户名和密码。",
        headers={"WWW-Authenticate": 'Basic realm="PCI-MED (authorized users only)"'},
        content_type="text/plain",
        charset="utf-8",
    )


@web.middleware
async def basic_auth(request: web.Request, handler):
    header = request.headers.get("Authorization", "")
    if not header.startswith("Basic "):
        return unauthorized()
    try:
        decoded = base64.b64decode(header[6:], validate=True).decode("utf-8")
        username, password = decoded.split(":", 1)
    except Exception:
        return unauthorized()
    if not (
        hmac.compare_digest(username, USER)
        and hmac.compare_digest(password, PASSWORD)
    ):
        return unauthorized()
    return await handler(request)


async def proxy(request: web.Request) -> web.StreamResponse:
    assert SESSION is not None
    url = TARGET + request.path_qs
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in REQ_SKIP
    }
    body = await request.read()

    try:
        async with SESSION.request(
            request.method,
            url,
            headers=headers,
            data=body if body else None,
            allow_redirects=False,
        ) as upstream:
            response = web.StreamResponse(
                status=upstream.status,
                reason=upstream.reason,
            )
            for key, value in upstream.headers.items():
                if key.lower() not in RESP_SKIP:
                    response.headers[key] = value
            # SSE / 大文件都走 chunked，不写死 Content-Length
            if request.method == "HEAD":
                await response.prepare(request)
                return response
            await response.prepare(request)
            async for chunk in upstream.content.iter_chunked(16 * 1024):
                if chunk:
                    await response.write(chunk)
            await response.write_eof()
            return response
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001
        return web.Response(
            status=502,
            text=f"上游 8000 不可用：{exc}",
            content_type="text/plain",
            charset="utf-8",
        )


async def on_startup(app: web.Application) -> None:
    global SESSION
    SESSION = ClientSession(
        timeout=ClientTimeout(total=None, sock_connect=10, sock_read=None),
        auto_decompress=False,
    )
    app["session"] = SESSION
    print(f"[auth-proxy] {HOST}:{PORT} -> {TARGET}  user={USER}", flush=True)


async def on_cleanup(app: web.Application) -> None:
    session: ClientSession | None = app.get("session")
    if session is not None:
        await session.close()


def main() -> None:
    app = web.Application(middlewares=[basic_auth], client_max_size=30 * 1024 * 1024)
    app.router.add_route("*", "/{tail:.*}", proxy)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    web.run_app(app, host=HOST, port=PORT, access_log=None, print=None)


if __name__ == "__main__":
    main()