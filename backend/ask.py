# -*- coding: utf-8 -*-
"""
PCI 术后用药管理助手 —— 端到端问答（RAG + DeepSeek，含指南 Tier）
运行前：pip install openai；并先运行 add_tier.py 给向量库补 tier 标签
"""
import sys
from pathlib import Path

from FlagEmbedding import BGEM3FlagModel
import chromadb

BASE = Path(__file__).parent


# ---------- 1. 读 .env ----------
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
if not API_KEY:
    print("❌ 没读到 DEEPSEEK_API_KEY，请检查 backend/.env")
    sys.exit(1)


# ---------- 2. 加载向量模型 ----------
MODEL_DIR = BASE / "models" / "bge-m3"
print("加载向量模型 bge-m3 ...（约几十秒）")
model = BGEM3FlagModel(str(MODEL_DIR), use_fp16=False, devices="cpu")


# ---------- 3. 加载向量库 ----------
DB_DIR = BASE / "vector_db"
client = chromadb.PersistentClient(path=str(DB_DIR))
collection = client.get_collection("pci_med_guidelines")
print(f"向量库就绪，共 {collection.count()} 条知识块")


# ---------- 4. 检索 ----------
K = 4


def clean_src(src):
    # "一级指南/xxx.pdf" -> "xxx"
    name = src.replace("\\", "/").split("/")[-1]
    if name.lower().endswith(".pdf"):
        name = name[:-4]
    return name


def retrieve(question):
    emb = model.encode([question], batch_size=1, max_length=512)["dense_vecs"]
    res = collection.query(query_embeddings=emb.tolist(), n_results=K)
    docs = res["documents"][0]
    metas = res["metadatas"][0]
    return docs, metas


# ---------- 5. 调 DeepSeek ----------
# 给DeepSeek定规则，后续要完善提示词
from openai import OpenAI

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


def build_prompt(question, docs, metas):  #打包问题-指南证据    
    parts = []
    for i, (d, m) in enumerate(zip(docs, metas), 1):
        src = clean_src(m.get("source_file", "未知来源"))
        tier = m.get("tier", 3)
        parts.append(f"[片段{i}｜Tier{tier}｜{src}]\n{d}")
    context = "\n\n".join(parts)
    prompt = (f"【指南片段】\n{context}\n\n【医生提问】\n{question}\n\n"
              f"请基于以上片段正面回答医生提问：先给出总结性结论（用 [编号] 标注来源），再列出支撑的原文依据。关键数值必须逐字照抄。")
    return prompt

#调用AI
def ask(question):
    docs, metas = retrieve(question)
    prompt = build_prompt(question, docs, metas)
    try:
        resp = llm.chat.completions.create(  # 呼叫 DeepSeek
            model=MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            stream=False,
        )
        answer = resp.choices[0].message.content
    except Exception as e:
        answer = f"调用 DeepSeek 出错：{e}"
    return answer, metas


# ---------- 6. 交互 ----------
print("\n===== PCI 术后用药管理助手（输入 exit 退出）=====")
while True:
    q = input("\n请输入患者情况或用药问题：\n> ").strip()
    if not q:
        continue
    if q.lower() in ("exit", "quit", "退出"):
        break
    print("\n正在检索并生成...")
    answer, metas = ask(q)
    print("\n" + "=" * 50)
    print(answer)
    print("-" * 50)
    print("溯源（本次召回的指南，按 Tier 排序）：")
    rows = sorted(
        {(m.get("tier", 3), clean_src(m.get("source_file", "未知来源"))) for m in metas},
        key=lambda x: (x[0], x[1]),
    )
    for tier, src in rows:
        print(f"  · [Tier{tier}] {src}")
    print("=" * 50)