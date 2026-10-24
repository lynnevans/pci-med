# -*- coding: utf-8 -*-
"""
PCI 术后用药管理 RAG —— 指南 PDF 批量转文本 + 切块（第二版：批量）

适用：电子文字版 PDF。扫描版会自动识别并单独报告，交给后续 OCR。

功能：
  1. 自动扫描「一级指南」「二级指南」两个子目录下所有 .pdf
  2. 逐个用 PyMuPDF 提取文字并清洗（去页眉/页码）
  3. 固定字符滑窗切块（500 字一块、重叠 100 字）
  4. 输出：
       text/     —— 每份指南的全文 .txt（方便对照）
       chunks/   —— 每份指南的切块 .json（下一步喂给向量化）
       report.txt —— 疑似扫描件清单（文字太少，需 OCR）

依赖：pip install pymupdf
用法：把本脚本放到 backend 根目录（和 main.py 同级），venv 激活后运行
      python pdf_to_chunks.py
"""

import json
import re
import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print("缺少依赖，请先运行： pip install pymupdf")
    sys.exit(1)

# 可调参数
GUIDE_DIRS = ["一级指南", "二级指南"]  
CHUNK_CHARS = 500      # 每块目标字符数
OVERLAP_CHARS = 100    # 相邻块重叠字符数
MIN_TEXT_CHARS = 150   # 全文少于这个字符数 → 判定为疑似扫描件，需 OCR
# =====================

BASE = Path(__file__).parent  # 脚本所在目录，运行时不依赖当前命令行在哪


def find_pdfs():
    pdfs = []
    for d in GUIDE_DIRS:
        dpath = BASE / d
        if not dpath.exists():
            print(f"警告：目录不存在，跳过 —— {d}")
            continue
        for p in sorted(dpath.glob("*.pdf")):
            pdfs.append(p)
    return pdfs


def extract_text(pdf_path):
    doc = fitz.open(pdf_path)
    pages = []
    for i, page in enumerate(doc):
        pages.append({"page": i + 1, "text": page.get_text("text")})
    doc.close()
    return pages


def clean_text(text):
    lines = text.split("\n")
    out = []
    for line in lines:
        s = line.strip()
        if re.fullmatch(r"·?\s*\d+\s*·?", s):      # 纯页码
            continue
        if "中华心血管病杂志" in s or s.startswith("Chin J Cardiol"):
            continue
        out.append(s)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def split_chunks(text, size, overlap):
    chunks = []
    start, n = 0, len(text)
    while start < n:
        end = min(start + size, n)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        start = end - overlap
    return chunks


def main():
    pdfs = find_pdfs()
    if not pdfs:
        print("没找到任何 PDF。请确认本脚本在 backend 目录下，且存在「一级指南」「二级指南」子文件夹。")
        sys.exit(1)
    print(f"共发现 {len(pdfs)} 份 PDF\n")

    (BASE / "text").mkdir(exist_ok=True)
    (BASE / "chunks").mkdir(exist_ok=True)

    report = []
    ok_cnt = 0
    for p in pdfs:
        name = p.stem  # 去掉 .pdf 的文件名
        pages = extract_text(p)
        full = clean_text("\n".join(pg["text"] for pg in pages))

        if len(full) < MIN_TEXT_CHARS:
            report.append(f"{p.parent.name}/{name}  —— 仅 {len(full)} 字符，疑似扫描件，需 OCR")
            continue

        (BASE / "text" / f"{name}.txt").write_text(full, encoding="utf-8")

        raw = split_chunks(full, CHUNK_CHARS, OVERLAP_CHARS)
        records = [
            {
                "entry_id": f"{name}-{idx + 1:04d}",
                "guideline_name": name,
                "source_file": f"{p.parent.name}/{p.name}",
                "chunk_chars": len(c),
                "text": c,
            }
            for idx, c in enumerate(raw)
        ]
        (BASE / "chunks" / f"{name}.json").write_text(
            json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        print(f"✓ {name}：{len(pages)} 页 → {len(raw)} 块")
        ok_cnt += 1

    if report:
        (BASE / "report.txt").write_text("\n".join(report), encoding="utf-8")
        print("\n" + "=" * 40)
        print("以下 PDF 疑似扫描件，需要另外走 OCR：")
        for r in report:
            print("  " + r)
        print("已写入 report.txt")

    print(f"\n完成：{ok_cnt}/{len(pdfs)} 份转为文字块，结果在 text/ 和 chunks/ 目录。")


if __name__ == "__main__":
    main()