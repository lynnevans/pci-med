# -*- coding: utf-8 -*-
"""
PCI 术后用药管理 —— FastAPI 接口
- POST /api/analyze：规则引擎（确定性结论，零自由发挥）
- POST /api/chat：RAG 摘录式问答（流式 SSE，指南溯源）
- POST /api/ocr：化验单识别（qwen3-vl-plus 视觉识别，返回结构化字段）

运行（backend 目录、venv 激活下）：
    uvicorn api:app --reload
"""
import json

from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from rule_engine import match


app = FastAPI(title="PCI 术后用药管理助手", version="0.4")

# 允许前端（Vite 5173）跨域调用；比赛演示放开，生产再收紧来源
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
