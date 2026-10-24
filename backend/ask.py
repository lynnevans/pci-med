# -*- coding: utf-8 -*-
"""
PCI 术后用药管理助手 —— 端到端问答（RAG + DeepSeek，含指南 Tier 冲突消解）
运行前：pip install openai；并先运行 add_tier.py 给向量库补 tier 标签
"""
import sys
from pathlib import Path

from FlagEmbedding import BGEM3FlagModel
import chromadb

BASE = Path(__file__).parent


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

MODEL_DIR = BASE / "models" / "bge-m3"
print("加载向量模型 bge-m3 ...（约几十秒）")
model = BGEM3FlagModel(str(MODEL_DIR), use_fp16=False, devices="cpu")

DB_DIR = BASE / "vector_db"
client = chromadb.PersistentClient(path=str(DB_DIR))
collection = client.get_collection("pci_med_guidelines")
print(f"向量库就绪，共 {collection.count()} 条知识块")

K = 4


def clean_src(src):
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


from openai import OpenAI

llm = OpenAI(api_key=API_KEY, base_url="https://api.deepseek.com")
MODEL = "deepseek-v4-pro"

SYSTEM_PROMPT = """你是「PCI术后长期用药管理助手」。你唯一的任务：从下方【指南片段】中摘录与医生提问直接相关的原文，按主题归并、标注来源片段编号，让医生直接核对原文依据。

铁律（违反任何一条都不允许）：
1. 只能摘录或原样引用片段里的句子，禁止改写、概括、翻译、补全、扩展、润色。
2. 绝对禁止输出片段里不存在的内容——包括你自己的医学知识、预训练知识、推测、常识补全。
3. 每个输出的句子后，必须紧跟它的来源【片段编号】。
4. 所给片段不足以回答时，只能写"所给片段未覆盖该问题"，不得给任何建议。
5. 关键数值（剂量、疗程、目标值、禁忌、监测频次）必须逐字照抄，不得四舍五入、不得换算单位、不得改用近义词。
6. 多来源不一致时，只并列呈现各来源原文，并标注 Tier 优先级，不得自行评判取舍。"""

def build_prompt(question, docs, metas):
    parts = []
    for i, (d, m) in enumerate(zip(docs, metas), 1):
        src = clean_src(m.get("source_file", "未知来源"))
        tier = m.get("tier", 3)
        parts.append(f"[片段{i}｜Tier{tier}｜{src}]\n{d}")
    context = "\n\n".join(parts)
    prompt = (f"【指南片段】\n{context}\n\n【医生提问】\n{question}\n\n"
              f"请摘录与上述问题直接相关的原文，逐句标注来源片段编号，禁止改写或补充。")
    return prompt


def ask(question):
    docs, metas = retrieve(question)
    prompt = build_prompt(question, docs, metas)
    try:
        resp = llm.chat.completions.create(
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