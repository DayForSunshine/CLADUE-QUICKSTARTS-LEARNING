"""全工具 agent runner.

包含：ThinkTool(本地) + FileReadTool + FileWriteTool(本地)
    + WebSearchServerTool(Anthropic服务端) + CodeExecutionServerTool(Anthropic服务端)
    + calculator(MCP本地子进程)

Usage: python agents/run_all_tools.py "your task here"
"""
import asyncio, sys
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.agent import Agent, ModelConfig
from agents.tools.think import ThinkTool
from agents.tools.file_tools import FileReadTool, FileWriteTool
from agents.tools.web_search import WebSearchServerTool
from agents.tools.code_execution import CodeExecutionServerTool

CALCULATOR_SERVER = {
    "type": "stdio",
    "command": sys.executable,
    "args": [str(Path(__file__).parent / "tools" / "calculator_mcp.py")],
}

SYSTEM_PROMPT = """
You are a powerful assistant with access to:
1. think            — 内部推理，复杂问题先思考再回答
2. file_read        — 读取本地文件 / 列目录
3. file_write       — 写入 / 编辑本地文件
4. web_search       — 联网搜索最新信息（Anthropic 服务端）
5. code_execution   — 在沙箱中运行 Python 代码（Anthropic 服务端）
6. calculator       — 精确数学运算（本地 MCP 子进程）

根据任务选择最合适的工具组合。
"""

async def main(task: str):
    agent = Agent(
        name="AllToolsAgent",
        system=SYSTEM_PROMPT,
        tools=[
            ThinkTool(),
            FileReadTool(),
            FileWriteTool(),
            WebSearchServerTool(max_uses=5),
            CodeExecutionServerTool(),
        ],
        mcp_servers=[CALCULATOR_SERVER],
        config=ModelConfig(
            model="claude-sonnet-5",
            max_tokens=4096,
            temperature=1.0,
        ),
        verbose=True,
    )
    response = await agent.run_async(task)
    print("\n=== Final Answer ===")
    for block in response.content:
        if block.type == "text":
            print(block.text)

if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else \
        "搜索中国人口，然后用 code_execution 计算每平方公里人口密度（面积约 9600000 km²）"
    asyncio.run(main(task))
