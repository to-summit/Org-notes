#!/usr/bin/env python3
"""批量构建本地 PageIndex 数据库(四本 OER 教材)。

用法:
    export DEEPSEEK_API_KEY=sk-...
    python build_index.py                 # 用默认四本 + optimize="full"
    python build_index.py --optimize merge  # 更省 token(不调 LLM 扩写)
    python build_index.py --rebuild         # 先清空再重建

特性:
  - 断点续跑:已在库里的文档自动跳过(按文件名判断)
  - 单本失败不影响其余
  - 结果 doc_id 写入 index_manifest.json,供 demo_use.py 使用
"""
from __future__ import annotations

import argparse
import json
import os # env check
import sys 
import time  # just for timer 
from pathlib import Path # OOP filesystem path

from pageindex import PageIndexLocalClient
from pageindex.errors import PageIndexAPIError

CWD = Path(__file__).resolve().parent

# 按 408 科目对应的四本教材
PDFS = [
    "archbook.pdf",      # 计算机组成原理: Basic Computer Architecture
    "C++3elatest.pdf",   # 数据结构: Data Structures and Algorithm Analysis
    "OSTEP.pdf",         # 操作系统: Operating Systems: Three Easy Pieces
    "compnetworks.pdf",  # 计算机网络: Computer Networks: A Systems Approach
]

STORAGE_PATH = CWD / ".pageindex"
MANIFEST = CWD / "index_manifest.json"

# 通过 LiteLLM 调用 DeepSeek;模型名也可换成 "deepseek/deepseek-reasoner"
INDEX_MODEL = "deepseek/deepseek-flash"
SUMMARY_MODEL = "deepseek/deepseek-flash"
CHAT_MODEL = "deepseek/deepseek-flash"


def build_client(optimize: str) -> PageIndexLocalClient:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        sys.exit("请先设置环境变量 DEEPSEEK_API_KEY")
    return PageIndexLocalClient(
        storage_path=str(STORAGE_PATH),
        index_model=INDEX_MODEL,
        summary_model=SUMMARY_MODEL,
        chat_model=CHAT_MODEL,          # 供 demo 的 chat() 使用
        optimize=optimize,              # "full" | "merge" | "off"
        index_backend = { "thinking": {"type":"disabled"}}, # close the thinking mode
    )


def index_by_name(client: PageIndexLocalClient) -> dict[str, str]:
    """已入库文档: 文件名 -> doc_id"""
    return {d["name"]: d["id"]
            for d in client.list_documents(limit=10000)["documents"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--optimize", default="full",
                    choices=["full", "merge", "off"],
                    help="full=LLM扩写(默认);merge=仅确定性合并;off=关闭")
    ap.add_argument("--rebuild", action="store_true",
                    help="先删除已存在的同名文档再重建")
    args = ap.parse_args()

    client = build_client(args.optimize)
    existing = index_by_name(client)

    if args.rebuild and existing:
        print(f"[clear] 删除 {len(existing)} 个已索引文档")
        for doc_id in existing.values():
            client.delete_document(doc_id)
        existing = {}

    manifest: dict[str, str] = {}
    t_all = time.time()

    for pdf in PDFS:
        path = CWD / pdf
        if not path.is_file():
            print(f"[skip ] 找不到文件: {path}")
            continue

        if pdf in existing:
            print(f"[skip ] 已索引,跳过: {pdf} -> {existing[pdf]}")
            manifest[pdf] = existing[pdf]
            continue

        print(f"[index] {pdf} ... (几百页,可能要几分钟)")
        t0 = time.time()
        try:
            result = client.submit_document(str(path))
        except PageIndexAPIError as e:
            print(f"[error] {pdf} 失败: {e}")
            continue
        dt = time.time() - t0

        doc_id = result["doc_id"]
        meta = client.get_document(doc_id)
        print(f"        doc_id={doc_id}  status={meta['status']}  "
              f"pages={meta['pageNum']}  用时 {dt:.0f}s")
        manifest[pdf] = doc_id

    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n完成: {len(manifest)} 本,共耗时 {time.time() - t_all:.0f}s")
    print(f"数据库: {STORAGE_PATH}")
    print(f"清单:   {MANIFEST}")


if __name__ == "__main__":       # 必须:索引会派生多进程 worker
    main()
