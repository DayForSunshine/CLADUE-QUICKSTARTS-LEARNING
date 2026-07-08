"""Calculator MCP agent runner. Usage: python run_calculator.py "calculate 123 * 456" """
import asyncio, sys
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.agent import Agent, ModelConfig

CALCULATOR_MCP = {
    "type": "stdio",
    "command": sys.executable,
    "args": [str(Path(__file__).parent / "tools" / "calculator_mcp.py")],
}

async def main(task: str):
    agent = Agent(
        name="CalculatorAgent",
        system="You are a math assistant. Use the calculator tool to compute results.",
        tools=[],
        mcp_servers=[CALCULATOR_MCP],
        config=ModelConfig(model="claude-haiku-4-5-20251001", max_tokens=1024),
        verbose=True,
    )
    response = await agent.run_async(task)
    for block in response.content:
        if block.type == "text":
            print(block.text)

if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "计算 123 乘以 456"
    asyncio.run(main(task))