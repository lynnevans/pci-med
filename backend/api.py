# -*- coding: utf-8 -*-
"""
PCI 术后用药管理 —— FastAPI 接口
- POST /api/analyze：规则
- POST /api/chat：RAG 问答
- POST /api/ocr：化验单识别（qwen3-vl-plus 视觉识别）
"""
import json

from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from rule_engine import match
from rag import stream_answer, clean_src
from ocr import ocr_from_base64

app = FastAPI(title="PCI 术后用药管理助手", version="0.4")

# 允许前端（Vite 5173）跨域调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DISCLAIMER = "本结果仅供基层医生辅助参考，不构成医疗决策，最终用药以专科医师判断为准。"


@app.get("/")
def root():
    return {"msg": "PCI 用药管理后端已启动"}


@app.post("/api/analyze")
def analyze(payload: dict = Body(...)):
    """输入患者信息字段字典（字段见 rule_engine.py 头部注释），返回规则引擎判定结果。"""
    result = match(payload)
    result["disclaimer"] = DISCLAIMER
    return result


@app.post("/api/ocr")
def ocr(payload: dict = Body(...)):
    """化验单识别。入参 {"image_base64": "...", "card_hint": "血脂"}，
    返回 {"items": [...], "remark": "..."}。"""
    img = payload.get("image_base64", "")
    if not img:
        return {"error": "image_base64 为空"}
    card_hint = payload.get("card_hint", "")
    try:
        result = ocr_from_base64(img, card_hint)
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