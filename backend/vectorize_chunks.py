# -*- coding: utf-8 -*-
"""
PCI 术后用药管理 RAG —— 文本块向量化 + 入库 Chroma
依赖：pip install FlagEmbedding chromadb modelscope
"""

import json
from pathlib import Path

BASE = Path(__file__).parent
CHUNKS_DIR = BASE / "chunks"  #文本
DB_DIR = BASE / "vector_db"  #存储数据库
MODEL_DIR = BASE / "models" / "bge-m3"  #模型位置
MODEL_ID = "BAAI/bge-m3"


def ensure_model():
    if (MODEL_DIR / "config.json").exists():
        print("检测到本地已有模型，跳过下载。")
    else:
        print(f"本地无模型，从 ModelScope（阿里魔搭，国内较快）下载 {MODEL_ID}，请耐心等待...")
        from modelscope import snapshot_download
        snapshot_download(MODEL_ID, local_dir=str(MODEL_DIR))
        print("模型下载完成。")
    return str(MODEL_DIR)


def load_chunks():
    if not CHUNKS_DIR.exists():
        print("找不到 chunks 目录，请先运行 pdf_to_chunks.py")
        return []
    records = []
    for jf in sorted(CHUNKS_DIR.glob("*.json")):
        records.extend(json.loads(jf.read_text(encoding="utf-8")))
    return records


def main():
    from FlagEmbedding import BGEM3FlagModel
    import chromadb

    records = load_chunks()
    if not records:
        print("没有可向量化的文本块。")
        return

    model_path = ensure_model()
    print(f"共 {len(records)} 块。加载模型 {model_path} ...")
    model = BGEM3FlagModel(model_path, use_fp16=False, devices="cpu")

    texts = [r["text"] for r in records]  #文本
    ids = [r["entry_id"] for r in records]  #编号
    metas = [  #来源
        {"guideline_name": r["guideline_name"],
         "source_file": r["source_file"],
         "chunk_chars": r["chunk_chars"]}
        for r in records
    ]

    print("开始向量化（CPU）...")
    out = model.encode(texts, batch_size=32, max_length=1024)  #语义指纹
    embeddings = out["dense_vecs"]

    client = chromadb.PersistentClient(path=str(DB_DIR))  #向量数据库
    col = client.get_or_create_collection(
        name="pci_med_guidelines",
        metadata={"hnsw:space": "cosine"}, 
    )

    BATCH = 500
    for i in range(0, len(texts), BATCH):
        col.add(
            ids=ids[i:i + BATCH],
            embeddings=embeddings[i:i + BATCH].tolist(),
            metadatas=metas[i:i + BATCH],
            documents=texts[i:i + BATCH],
        )
    print(f"入库完成：向量库现有 {col.count()} 条记录，存储在 {DB_DIR}")


if __name__ == "__main__":
    main()