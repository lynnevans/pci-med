# -*- coding: utf-8 -*-
"""
给向量库每条知识块补 tier 标签（依据 source_file 映射）。
运行前：在 backend 目录、venv 激活下执行 python add_tier.py
"""
from collections import Counter
from pathlib import Path
import chromadb

BASE = Path(__file__).parent
DB_DIR = BASE / "vector_db"

# source_file 的格式是「一级指南/xxx.pdf」或「二级指南/xxx.pdf」
TIER_MAP = {
    "一级指南/经皮冠状动脉介入治疗指南（2025）.pdf": 1,
    "一级指南/非ST段抬高型急性冠脉综合征诊断和治疗指南（2024）.pdf": 1,
    "一级指南/中国慢性冠脉综合征患者诊断及管理指南.pdf": 1,
    "一级指南/中国血脂管理指南（2023年）.pdf": 1,
    "一级指南/2023 ESC Guidelines for the management of acute coronary syndromes.pdf": 2,
    "一级指南/2024 ESC Guidelines for the management of chronic coronary syndromes.pdf": 2,
    "一级指南/virani-et-al-2023-2023-aha-acc-accp-aspc-nla-pcna-guideline-for-the-management-of-patients-with-chronic-coronary.pdf": 2,
    "一级指南/2021 ACC AHA SCAI 冠脉血运重建指南.pdf": 2,
    "二级指南/2019 ESC EAS Guidelines for the management of dyslipidaemias.pdf": 2,
    "一级指南/心房颤动诊断和治疗中国指南.pdf": 3,
    "二级指南/中国心力衰竭诊断和治疗指南2024.pdf": 3,
    "二级指南/中国心脏康复与二级预防指南2018精要.pdf": 3,
    "二级指南/中国糖尿病防治指南（2024版）.pdf": 3,
    "二级指南/冠状动脉生物可吸收支架临床应用中国专家共识.pdf": 3,
    "二级指南/冠心病合并心房颤动患者抗栓管理中国专家共识.pdf": 3,
    "二级指南/口服抗栓药物相关消化道损伤防治专家共识.pdf": 3,
    "二级指南/全面管理血脂相关心血管风险专家共识（2025）.pdf": 3,
    "二级指南/冠心病双联抗血小板治疗中国专家共识.pdf": 3,
    "二级指南/应用β肾上腺素能受体阻滞剂规范治疗冠心病的中国专家共识.pdf": 3,
    "二级指南/泛血管疾病抗栓治疗中国专家共识（2024版）.pdf": 3,
    "二级指南/稳定性冠心病基层合理用药指南.pdf": 3,
    "二级指南/血管紧张素受体-脑啡肽酶抑制剂在心力衰竭患者中应用中国专家共识.pdf": 3,
    "二级指南/超高危动脉粥样硬化性心血管疾病患者血脂管理中国专家共识.pdf": 3,
    "二级指南/2022 AHA ACC HFSA 心力衰竭管理指南.pdf": 3,
    "二级指南/中国高血压防治指南（2024年修订版）.pdf": 3,
    "二级指南/2024 ESC 心房颤动管理指南.pdf": 3,
}


def main():
    client = chromadb.PersistentClient(path=str(DB_DIR))
    col = client.get_collection("pci_med_guidelines")

    data = col.get(include=["metadatas"])
    ids = data["ids"]
    metas = data["metadatas"]
    print(f"共读取 {len(ids)} 条记录（向量库总数 {col.count()}）")

    new_metas = []
    unmatched = []
    for m in metas:
        sf = m.get("source_file", "")
        tier = TIER_MAP.get(sf)
        if tier is None:
            tier = 3
            unmatched.append(sf)
        nm = dict(m)          # 保留原有 guideline_name / source_file / chunk_chars
        nm["tier"] = int(tier)
        new_metas.append(nm)

    BATCH = 500
    for i in range(0, len(ids), BATCH):
        col.update(ids=ids[i:i + BATCH], metadatas=new_metas[i:i + BATCH])
    print("OK tier 标签写入完成")

    c = Counter(nm["tier"] for nm in new_metas)
    print(f"Tier 分布（按知识块数量）：Tier1={c[1]}、Tier2={c[2]}、Tier3={c[3]}")

    if unmatched:
        print("\n警告：以下 source_file 未匹配到映射表，已默认归 Tier 3：")
        for u in sorted(set(unmatched)):
            print("  ", u)
    else:
        print("\nOK 所有指南全部精确匹配，无遗漏。")


if __name__ == "__main__":
    main()