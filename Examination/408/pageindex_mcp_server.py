#!/usr/bin/env python3
"""本地 PageIndex 的独立 MCP 服务器(stdio)。

把已建好的本地库(.pageindex)暴露成 MCP 工具,任何 MCP 客户端
(Claude Desktop / Cursor / Cline 等)都能用。

用法(一般由 MCP 客户端拉起,不用手动跑):
    python pageindex_mcp_server.py

环境变量:
    PAGEINDEX_STORAGE   库目录(默认 ./pageindex)
    DEEPSEEK_API_KEY    仅 ask 工具需要(问答用)
    PAGEINDEX_CHAT_MODEL  问答模型(默认 deepseek/deepseek-flash)
"""
from __future__ import annotations

import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from pageindex import PageIndexLocalClient

HERE = Path(__file__).resolve().parent
STORAGE = os.environ.get("PAGEINDEX_STORAGE", str(HERE / ".pageindex"))
CHAT_MODEL = os.environ.get("PAGEINDEX_CHAT_MODEL", "deepseek/deepseek-flash")

# 本地客户端:检索工具只读本地库,不需要任何 API key
client = PageIndexLocalClient(
    storage_path=STORAGE,
    chat_model=CHAT_MODEL if os.environ.get("DEEPSEEK_API_KEY") else None,
)

server = MCPServer(
    name="pageindex-local",
    title="PageIndex (local)",
    version="1.0.0",
    instructions=client.agent_instructions(),
)

# 1) 注册 PageIndex 自带的四个只读工具:
#    browse_documents / get_document / get_document_structure / get_page_content
for fn in client.agent_tools():
    server.add_tool(fn)


# 2) 额外加一个「带引用的问答」工具(需要 DEEPSEEK_API_KEY)
@server.tool(
    name="ask",
    description=(
        "Answer a question grounded in the local PageIndex library, with "
        "page citations. Use this when you want a synthesized answer; use "
        "get_page_content() when you want raw page text."
    ),
)
def ask(question: str) -> str:
    if not os.environ.get("DEEPSEEK_API_KEY"):
        return "ERROR: ask 需要设置 DEEPSEEK_API_KEY"
    return client.chat(question, citations=True)


if __name__ == "__main__":
    server.run("stdio")          # stdio 传输,不要在此打印任何东西
