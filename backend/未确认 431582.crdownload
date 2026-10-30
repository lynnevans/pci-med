# -*- coding: utf-8 -*-
"""
PCI 术后用药管理 —— 化验单 OCR（qwen3-vl-plus 视觉识别）
供 FastAPI 调用。输入化验单图片（base64），输出结构化字段 JSON。

说明：本模块只负责「读单子」——把化验单上真实存在的检测项、数值、单位、
参考范围、异常箭头原样读出来；不做任何医学判断或字段映射。
字段映射（项目名 → rule_engine 字段 key）在后续用确定性字典完成，不进 LLM。
"""
import json
from pathlib import Path

from openai import OpenAI

BASE = Path(__file__).parent

# 阿里云百炼（DashScope）OpenAI 兼容端点（旧域名仍可用，新手无需查 WorkspaceId）
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL = "qwen3-vl-plus"


def _load_env():
    env = {}
    p = BASE / ".env"
    if not p.exists():
        return env
    with open(p, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


ENV = _load_env()
API_KEY = ENV.get("DASHSCOPE_API_KEY", "")

_ocr_llm = OpenAI(api_key=API_KEY, base_url=BASE_URL)

SYSTEM_PROMPT = """你是医疗化验单识别助手。请识别图片中的化验单，提取所有检测项目及其结果。
只输出一个合法 JSON 对象，不要输出任何其他文字、解释或 markdown 代码块标记（不要 ```）。

输出结构：
{
  "items": [
    {
      "item": "检测项目中文名（照抄化验单上的名字）",
      "value": "结果数值（原样字符串，如 3.8、阳性、<0.01、120/80）",
      "unit": "单位（如 mmol/L、g/L、×10^9/L；无单位填空字符串）",
      "ref_range": "化验单上印的参考范围（如 2.60-3.40；没印填空字符串）",
      "flag": "high / low / normal（依化验单的箭头或参考范围判断；无箭头且无参考范围时填 normal）"
    }
  ],
  "remark": "整张单的其他要点：带异常箭头但难以归类的项、'危急值'提示等；没有则填空字符串"
}

硬性要求：
1. value 必须原样照抄，禁止四舍五入、禁止换算单位、禁止改写。
2. 看不清、不确定的项，不要编造，宁可不输出该项。
3. items 只列化验单上真实存在的检测项目，不要补充想象的项目。
4. 有条码、患者姓名、年龄、性别等非检测项，不放进 items。"""


def ocr_from_base64(img_base64: str, card_hint: str = "") -> dict:
    """输入图片 base64（可带 data: 前缀），返回识别结果 dict。card_hint 可选，提示当前检查卡片。"""
    if not API_KEY:
        return {"error": "未配置 DASHSCOPE_API_KEY，请在 .env 中填写阿里云百炼 API Key"}

    if not img_base64.startswith("data:"):
        img_base64 = "data:image/jpeg;base64," + img_base64

    task_line = f"当前这张化验单对应的检查卡片是「{card_hint}」，请重点识别该卡片涉及的检测项目。" if card_hint else ""

    resp = _ocr_llm.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": img_base64}},
                    {"type": "text", "text": (task_line + "请按 system 要求的 JSON 结构输出识别结果。")},
                ],
            },
        ],
        temperature=0,
    )
    content = (resp.choices[0].message.content or "").strip()
    # 剥离可能出现的 markdown 围栏
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:]
        content = content.strip()
    try:
        return json.loads(content)
    except Exception:
        return {"items": [], "raw": content, "error": "模型返回不是合法 JSON，请重试"}