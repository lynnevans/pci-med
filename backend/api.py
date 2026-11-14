# -*- coding: utf-8 -*-
"""
PCI 术后用药管理 —— FastAPI 接口
- POST /api/analyze：规则引擎 + 八部分结构化报告（确定性结论，零自由发挥）
- POST /api/chat：RAG 摘录式问答（流式 SSE，指南溯源）
- POST /api/ocr：化验单识别（qwen3-vl-plus 读单）+ 确定性字段映射（ocr_map.py，零 LLM）

运行（backend 目录、venv 激活下）：
    本机开发：  uvicorn api:app --reload
    局域网访问：uvicorn api:app --host 0.0.0.0 --port 8000
                （前端先 npm run build，FastAPI 会直接托管 dist，其他电脑只访问 8000）
"""
import json
from pathlib import Path

from fastapi import FastAPI, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from rule_engine import match
from report_builder import DISCLAIMER, build_report
from patient_normalize import normalize_patient
from rag import stream_answer, clean_src
from ocr import ocr_from_base64
from ocr_map import map_items
from auth import (
    DB_PATH,
    SESSION_DAYS,
    create_session,
    delete_session,
    get_session_user,
    init_db,
    login as auth_login,
    register as auth_register,
)

app = FastAPI(title="PCI 术后用药管理助手（专为基层医生使用）", version="0.5")
init_db()

COOKIE_NAME = "pci_session"
PUBLIC_API_PATHS = {
    "/api/health",
    "/api/auth/register",
    "/api/auth/login",
    "/api/auth/logout",
    "/api/auth/me",
}


@app.middleware("http")
async def require_login(request: Request, call_next):
    """除健康检查与登录注册外，所有 /api/* 均需医生登录。"""
    path = request.url.path
    if (
        path.startswith("/api/")
        and path not in PUBLIC_API_PATHS
        and request.method != "OPTIONS"
    ):
        user = get_session_user(request.cookies.get(COOKIE_NAME))
        if not user:
            return JSONResponse({"error": "未登录或登录已过期，请先登录"}, status_code=401)
        request.state.user = user
    return await call_next(request)


def _set_login_cookie(response: JSONResponse, token: str, request: Request) -> None:
    forwarded = request.headers.get("x-forwarded-proto", "").lower()
    secure = request.url.scheme == "https" or forwarded == "https"
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_DAYS * 86400,
        httponly=True,
        samesite="lax",
        secure=secure,
        path="/",
    )


@app.post("/api/auth/register")
def register(request: Request, payload: dict = Body(...)):
    try:
        user = auth_register(
            payload.get("username", ""),
            payload.get("password", ""),
            payload.get("display_name", ""),
        )
    except ValueError as exc:
        return JSONResponse({"error": str(exc)}, status_code=400)
    token = create_session(user["id"])
    response = JSONResponse({"user": user})
    _set_login_cookie(response, token, request)
    return response


@app.post("/api/auth/login")
def login(request: Request, payload: dict = Body(...)):
    user = auth_login(payload.get("username", ""), payload.get("password", ""))
    if not user:
        return JSONResponse({"error": "用户名或密码错误"}, status_code=401)
    token = create_session(user["id"])
    response = JSONResponse({"user": user})
    _set_login_cookie(response, token, request)
    return response


@app.get("/api/auth/me")
def me(request: Request):
    user = get_session_user(request.cookies.get(COOKIE_NAME))
    if not user:
        return JSONResponse({"error": "未登录"}, status_code=401)
    return {"user": user}


@app.post("/api/auth/logout")
def logout(request: Request):
    delete_session(request.cookies.get(COOKIE_NAME))
    response = JSONResponse({"ok": True})
    response.delete_cookie(COOKIE_NAME, path="/")
    return response


DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

# 允许前端（Vite 5173）跨域调用；比赛演示放开，生产再收紧来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    """连通性自检：其他电脑访问 /api/health 应返回 {"ok": true, "web": true}。"""
    return {"ok": True, "web": (DIST / "index.html").is_file()}


@app.post("/api/analyze")
def analyze(payload: dict = Body(...)):
    """先统一推导后台字段，再运行规则并生成结构化报告。"""
    patient = normalize_patient(payload)
    result = match(patient)
    result["disclaimer"] = DISCLAIMER
    result["normalized_patient"] = patient
    result["report"] = build_report(patient, result)
    return result


@app.post("/api/ocr")
def ocr(payload: dict = Body(...)):
    """化验单识别 + 确定性字段映射。

    入参 {"image_base64": "...", "card_hint": "血脂"}
    返回 {"items": [...], "remark": "...", "fields": [...], "unmatched": [...], "warnings": [...]}
    - items     ：模型原样读出的检测项（不做判断）
    - fields    ：已按字典映射到前端表单字段，可直接回填
    - unmatched ：未命中字典 / 单位不一致 / 仅提示的项，交给医生人工处理
    """
    img = payload.get("image_base64", "")
    if not img:
        return {"error": "image_base64 为空"}
    card_hint = payload.get("card_hint", "")
    try:
        result = ocr_from_base64(img, card_hint)
        if "error" not in result:
            result.update(map_items(result.get("items", []), result.get("conclusion", "")))
        result["disclaimer"] = DISCLAIMER
        return result
    except Exception as e:
        return {"error": "识别失败：" + str(e)}


@app.post("/api/chat")
def chat(payload: dict = Body(...)):
    """RAG 摘录式问答，流式 SSE 返回。入参 {"question": "..."}。"""
    question = (payload.get("question") or "").strip()
    if not question:
        return {"error": "question 不能为空"}

    def gen():
        try:
            stream, docs, metas = stream_answer(question)
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': 'RAG 调用失败：' + str(e)}, ensure_ascii=False)}\n\n"
            return
        # 先送溯源片段（Tier + 指南名）
        sources = [
            {"index": i, "tier": m.get("tier", 3), "source": clean_src(m.get("source_file", "未知来源"))}
            for i, m in enumerate(metas, 1)
        ]
        yield f"data: {json.dumps({'type': 'sources', 'data': sources}, ensure_ascii=False)}\n\n"
        # 再逐段送回答正文
        try:
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield f"data: {json.dumps({'type': 'delta', 'data': delta}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'data': '生成中断：' + str(e)}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


# ================= 前端托管（局域网/单端口） =================
# 前端已构建时，FastAPI 直接托管 dist：其他电脑只访问 http://<本机IP>:8000 即可，
# 不再需要 5173 的 Vite。API 路由都在这个 mount 之前注册，优先级更高。
if (DIST / "index.html").is_file():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="web")
else:
    @app.get("/")
    def root():
        return {
            "msg": "PCI 用药管理后端已启动；前端未构建。"
                   "先在 frontend 目录执行 npm run build，再重启本服务。"
        }