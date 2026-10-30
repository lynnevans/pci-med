# -*- coding: utf-8 -*-
"""
PCI 术后用药管理 —— RAG 核心（bge-m3 检索 + DeepSeek 生成）
供 FastAPI 调用。模型与向量库懒加载：首次问答时才加载 bge-m3（约几十秒），后端启动不卡。
"""
from pathlib import Path

from FlagEmbedding import BGEM3FlagModel
import chromadb
from openai import OpenAI

BASE = Path(__file__).parent


# ---------- 读 .env ----------
def load_env():
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


ENV = load_env()
API_KEY = ENV.get("DEEPSEEK_API_KEY", "")

MODEL_DIR = BASE / "models" / "bge-m3"
DB_DIR = BASE / "vector_db"
COLLECTION = "pci_med_guidelines"
K = 4

llm = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
MODEL = "deepseek-v4-pro"

SYSTEM_PROMPT = """你是「PCI术后长期用药管理助手」。你的任务：基于下方【指南片段】正面回答医生的用药问题——先给出直接、明确的总结性答案，再用片段原文佐证，让医生可核对依据。

回答要求（违反任何一条都不允许）：
1. 必须正面、直接回答问题，给出明确的总结性结论；禁止只罗列原文而不作答。
2. 总结性结论必须完全来自所给片段，禁止使用片段之外的知识、预训练知识、推测或常识补全做医学判断。
3. 涉及指南依据的句子，紧跟来源编号 [n]（n 为片段编号），例如"替格瑞洛维持剂量为 90 mg 每日两次[1]"。
4. 关键数值（剂量、疗程、目标值、禁忌、监测频次）必须逐字照抄片段原文，不得四舍五入、不得换算单位、不得改用近义词。
5. 不同指南意见不一致时，并列呈现各来源原话并标注 Tier，说明"不同指南存在差异"，不得自行判断取舍。
6. 所给片段不足以支撑结论时，只能回复"您的有效信息较少，推荐获取上级医师建议"，不得猜测或给建议。"""


# ---------- 懒加载 ----------
_model = None
_collection = None


def _ensure_loaded():
    global _model, _collection
    if _model is None:
        _model = BGEM3FlagModel(str(MODEL_DIR), use_fp16=False, devices="cpu")
    if _collection is None:
        _client = chromadb.PersistentClient(path=str(DB_DIR))
        _collection = _client.get_collection(COLLECTION)


def clean_src(src):
    """"一级指南/xxx.pdf" -> "xxx"""
    name = src.replace("\\", "/").split("/")[-1]
    if name.lower().endswith(".pdf"):
        name = name[:-4]
    return name


def retrieve(question):
    _ensure_loaded()
    emb = _model.encode([question], batch_size=1, max_length=512)["dense_vecs"]
    res = _collection.query(query_embeddings=emb.tolist(), n_results=K)
    return res["documents"][0], res["metadatas"][0]


def build_prompt(question, docs, metas):
    parts = []
    for i, (d, m) in enumerate(zip(docs, metas), 1):
        src = clean_src(m.get("source_file", "未知来源"))
        tier = m.get("tier", 3)
        parts.append(f"[片段{i}｜Tier{tier}｜{src}]\n{d}")
    context = "\n\n".join(parts)
    return (f"【指南片段】\n{context}\n\n【医生提问】\n{question}\n\n"
            f"请基于以上片段正面回答医生提问：先给出总结性结论（用 [编号] 标注来源），再列出支撑的原文依据。关键数值必须逐字照抄。")


def stream_answer(question):
    """返回 (stream, docs, metas)：stream 为 DeepSeek 流式响应对象"""
    docs, metas = retrieve(question)
    prompt = build_prompt(question, docs, metas)
    stream = llm.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        stream=True,
    )
    return stream, docs, metas