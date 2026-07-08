"""File ops agent runner. Usage: python run_file_ops.py "your task here" """
import asyncio, sys
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.skills import load_skill

async def main(task: str):
    skill = load_skill("file_ops.yaml")
    agent = skill.create_agent(verbose=True)
    response = await agent.run_async(task)
    for block in response.content:
        if block.type == "text":
            print(block.text)

if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "列出 agents/ 目录下的所有文件"
    asyncio.run(main(task))
