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

SYSTEM_PROMPT = """你是「PCI 术后长期用药管理助手」，服务于基层医院复诊场景，辅助医生给出冠心病 PCI 术后患者的用药建议。

你必须严格遵守：
1. 只依据下面提供的【指南片段】作答，不要编造指南里没有的内容；知识不足就明说"指南片段中未覆盖"。
2. 遇到这些红线情况：疑似急性心梗、活动性大出血/黑便、急性心衰、严重过敏、晕厥、血压异常危象等，必须第一句就提示"建议立即转诊/急诊"，不要给常规用药建议。
3. 回答结构清晰：先给结论，再给依据，并标注每条依据来自哪个【片段编号】。
4. 提到具体药物时，同时给出关键监测项（如 INR、肌酶、血压、心率、出血征象等）。
5. 语言给医生看，专业、简洁，不要客套废话。
6. 【冲突消解】当多个片段对同一问题建议不一致时，优先采信 Tier 更小的来源（Tier 1 > Tier 2 > Tier 3）；同 Tier 内优先更新的版本。若高 Tier 片段已明确，应以其为准，可简要说明与其他来源的差异。"""


def build_prompt(question, docs, metas):
    parts = []
    for i, (d, m) in enumerate(zip(docs, metas), 1):
        src = clean_src(m.get("source_file", "未知来源"))
        tier = m.get("tier", 3)
        parts.append(f"[片段{i}｜Tier{tier}｜{src}]\n{d}")
    context = "\n\n".join(parts)
    prompt = (f"【指南片段】\n{context}\n\n【医生提问】\n{question}\n\n"
              f"请给出用药建议，标注来源片段编号；多来源不一致时说明采信哪一条及理由。")
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