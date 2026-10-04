#!/usr/bin/env python3
"""演示如何使用建好的本地 PageIndex 数据库。

前置:先运行  python build_index.py
运行:  export DEEPSEEK_API_KEY=sk-... && python demo_use.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from pageindex import PageIndexLocalClient

CWD = Path(__file__).resolve().parent
STORAGE_PATH = CWD / ".pageindex"
CHAT_MODEL = "deepseek/deepseek-flash"


def print_outline(nodes: list, indent: int = 0, max_depth: int = 2) -> None:
    """打印结构树(标题 + 页码范围)。"""
    for n in nodes:
        print("  " * indent +
              f"- {n['title']}  (p{n['start_index']}–{n['end_index']})")
        if indent + 1 < max_depth and n.get("nodes"):
            print_outline(n["nodes"], indent + 1, max_depth)


def main() -> None:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        sys.exit("请先设置环境变量 DEEPSEEK_API_KEY")

    # 打开已有数据库(只传 storage_path 即可,无需重新索引)
    client = PageIndexLocalClient(
        storage_path=str(STORAGE_PATH),
        chat_model=CHAT_MODEL,
    )

    # ---- 1. 列出库内所有文档 ----
    docs = client.list_documents(limit=10000)["documents"]
    print("=== 已索引文档 ===")
    for d in docs:
        print(f"{d['id']}  {d['name']}  pages={d['pageNum']}  "
              f"ready={client.is_retrieval_ready(d['id'])}")
    if not docs:
        sys.exit("库是空的,请先运行 build_index.py")

    # 选一本做后续演示
    doc = docs[1]
    doc_id = doc["id"]

    # ---- 2. 查看结构树(不含正文,省 token)----
    print(f"\n=== 《{doc['name']}》章节结构 ===")
    structure = client.get_document_structure(doc_id)
    print_outline(structure, max_depth=2)

    # ---- 3. 读取某一页的正文 ----
    print(f"\n=== {doc['name']} 第 5 页正文(前 300 字)===")
    pages = client.get_ocr(doc_id, format="page")["result"]
    print(pages[4]["markdown"][:300].replace("\n", " "))

    # ---- 4. 针对单本文档提问 ----
    q1 = "What is the difference between a process and a thread?"
    print(f"\n=== 限定《{doc['name']}》提问 ===\nQ: {q1}\nA: ", end="")
    print(client.chat(q1, doc_id=doc_id, citations=True))

    # ---- 5. 跨全库提问(不传 doc_id,自动检索所有文档)----
    q2 = "Explain virtual memory and paging, and how a TLB helps."
    print(f"\n=== 全库提问 ===\nQ: {q2}\nA: ", end="")
    print(client.chat(q2))

    # ---- 6. 流式输出 + 展示检索过程(可选)----
    # print("\n=== 流式输出 ===")
    # stream = client.chat("Summarize chapter 2.",
    #                      doc_id=doc_id, stream=True,
    #                      show_process={"thinking": False})
    # for chunk in stream:
    #     print(chunk, end="", flush=True)
    # print()

    # ---- 7. 只取结构化树数据(供程序处理)----
    # tree = client.get_tree(doc_id, node_summary=True, include_text=False)["result"]
    # for n in tree:
    #     print(n.get("node_id"), n["title"], n.get("summary", "")[:80])


if __name__ == "__main__":
    main()
