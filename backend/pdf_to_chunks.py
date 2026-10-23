# -*- coding: utf-8 -*-
"""
指南 PDF 转文本 + 切块

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

# 参数
PDF_FILENAME = "心房颤动诊断和治疗中国指南.pdf" 
CHUNK_CHARS = 500      # 每块目标字符数
OVERLAP_CHARS = 100    # 相邻块重叠字符数
MIN_TEXT_CHARS = 150   

BASE = Path(__file__).parent
PDF_PATH = BASE / PDF_FILENAME


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
        # 过滤纯数字页码
        if re.fullmatch(r"·?\s*\d+\s*·?", s):
            continue
        # 过滤明显的页眉
        if "中华心血管病杂志" in s or s.startswith("Chin J Cardiol"):
            continue
        out.append(s)
    # 将连续 3 个以上的换行合并为 2 个
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
    if not PDF_PATH.exists():
        print(f"错误：找不到文件 {PDF_PATH}")
        print("请确认 PDF 文件已经放入 backend 目录，且文件名与脚本中 PDF_FILENAME 一致。")
        sys.exit(1)

    print(f"正在解析：{PDF_FILENAME}")
    name = PDF_PATH.stem  # 获取不带后缀的文件名

    # 创建输出文件夹
    text_dir = BASE / "text"
    chunks_dir = BASE / "chunks"
    text_dir.mkdir(exist_ok=True)
    chunks_dir.mkdir(exist_ok=True)

    pages = extract_text(PDF_PATH)
    full = clean_text("\n".join(pg["text"] for pg in pages))

    if len(full) < MIN_TEXT_CHARS:
        print(f"警告：该文件仅 {len(full)} 字符，疑似图片扫描件，需OCR。")
        sys.exit(1)

    # 写入全文
    txt_file = text_dir / f"{name}.txt"
    txt_file.write_text(full, encoding="utf-8")
    print(f"全文已保存至：{txt_file.name}")

    # 切块
    raw = split_chunks(full, CHUNK_CHARS, OVERLAP_CHARS)
    records = [
        {
            "entry_id": f"{name}-{idx + 1:04d}",
            "guideline_name": name,
            "source_file": PDF_FILENAME,
            "chunk_chars": len(c),
            "text": c,
        }
        for idx, c in enumerate(raw)
    ]

    # 写入 JSON
    json_file = chunks_dir / f"{name}.json"
    json_file.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"\n切块完成：共 {len(raw)} 块。")
    print(f"结果已保存至：{json_file}")


if __name__ == "__main__":
    main()