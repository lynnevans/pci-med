# -*- coding: utf-8 -*-
from pathlib import Path

BASE = Path(__file__).parent
DB_DIR = BASE / "vector_db"
MODEL_DIR = BASE / "models" / "bge-m3"

QUERIES = [
    "PCI 术后患者双联抗血小板治疗（DAPT）应该持续多久？",
    "极高危动脉粥样硬化患者 LDL-C 的目标值是多少？",
    "房颤合并 PCI 术后的患者，抗栓方案如何选择？",
]


def main():
    from FlagEmbedding import BGEM3FlagModel
    import chromadb

    if not (MODEL_DIR / "config.json").exists():
        print("找不到模型，请先运行 vectorize_chunks.py")
        return

    print("加载模型和向量库...")
    model = BGEM3FlagModel(str(MODEL_DIR), use_fp16=False, devices="cpu")  
    client = chromadb.PersistentClient(path=str(DB_DIR)) 
    col = client.get_collection("pci_med_guidelines") 
    print(f"向量库共 {col.count()} 条记录\n")

    for q in QUERIES:
        print("=" * 60)
        print(f"问题：{q}\n")
        qvec = model.encode([q], batch_size=1, max_length=1024)["dense_vecs"]  #问题encode
        res = col.query(  #比对指纹库
            query_embeddings=qvec.tolist(),
            n_results=3,
            include=["documents", "metadatas", "distances"],
        )
        for i in range(len(res["ids"][0])):
            meta = res["metadatas"][0][i]
            dist = res["distances"][0][i]   #距离小于0.4，完全匹配
            doc = res["documents"][0][i].replace("\n", " ")
            print(f"[Top{i+1}] 来源: {meta['source_file']} | 距离: {dist:.4f}")
            print(f"  {doc[:180]}...")
            print()
        print()


if __name__ == "__main__":
    main()