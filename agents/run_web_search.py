"""Web search agent runner. Usage: python run_web_search.py "your task here" """
import asyncio
import json
import re
import sys
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.agent import Agent, ModelConfig
from agents.skills import load_skill
from agents.memory import MemoryManager

MEMORY_DECISION_PROMPT = """\
你是一个记忆管理助手。请判断以下搜索任务和结果中是否包含值得长期保存的内容。

判断标准（满足任意一条即保存）：
- 结论性事实：跨时间仍然成立的知识点（如产品特性对比、技术概念）
- 用户偏好：体现用户关注方向的任务主题
- 高质量摘要：信息密度高、未来可直接复用的内容

判断标准（以下情况不保存）：
- 纯时效性新闻（一周后失效）
- 结果为空或搜索失败

---
任务：{task}

结果：
{result}
---

如果值得保存，严格按以下 JSON 格式回复，不要添加任何其他文字：
{{"name": "kebab-case-slug", "description": "一行摘要（50字以内）", "content": "提炼后的记忆正文"}}

如果不值得保存，只回复：null
"""


def _extract_memory_json(text: str) -> dict | None:
    """从模型回复中提取 JSON 或识别 null。

    处理三种常见格式：
    1. 裸 JSON：{"name": ...}
    2. 代码块包裹：```json\n{"name": ...}\n```
    3. null 或 "null"
    """
    text = text.strip()

    # null 判断
    if text.lower() in ("null", "none", "no", "不保存", ""):
        return None

    # 剥离 markdown 代码块
    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if code_block:
        text = code_block.group(1)

    # 提取第一个完整 JSON 对象（防止模型在 JSON 前后加说明文字）
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if not json_match:
        return None

    try:
        data = json.loads(json_match.group())
        # 验证必要字段
        if all(k in data for k in ("name", "description", "content")):
            return data
    except json.JSONDecodeError:
        pass

    return None


async def _decide_and_save_memory(
    task: str,
    result: str,
    memory: MemoryManager,
) -> None:
    """让模型决定是否保存记忆，解析决策并写入 MemoryManager。"""
    print("\n=== Memory Decision ===")

    # 纯推理 agent，不需要任何工具
    decision_agent = Agent(
        name="MemoryDecider",
        system="你是一个严格的记忆管理助手，只输出 JSON 或 null，不输出其他内容。",
        tools=[],
        config=ModelConfig(model="claude-opus-4-8", max_tokens=512),
        verbose=False,
    )

    prompt = MEMORY_DECISION_PROMPT.format(task=task, result=result)
    response = await decision_agent.run_async(prompt)

    raw = "\n".join(
        block.text for block in response.content if block.type == "text"
    )
    print(f"Model decision: {raw[:200]}")

    entry = _extract_memory_json(raw)

    if entry is None:
        print("→ 判断为不值得保存，跳过。")
        return

    saved_path = memory.save(
        name=entry["name"],
        content=entry["content"],
        description=entry["description"],
    )
    print(f"→ 记忆已保存：{saved_path}")


async def main(task: str):
    # 1. 加载历史记忆注入上下文
    memory = MemoryManager()
    memory_context = memory.load_all()

    # 2. 运行搜索 agent
    skill = load_skill("web_search.yaml")
    agent = skill.create_agent(verbose=True)

    full_task = f"{memory_context}\n\n{task}" if memory_context else task
    response = await agent.run_async(full_task)

    final_text = "\n".join(
        block.text for block in response.content if block.type == "text"
    )
    print("\n=== Final Answer ===")
    print(final_text)

    # 3. 持久化结果到文件
    output_path = Path(__file__).parent / "search_result.md"
    output_path.write_text(f"# {task}\n\n{final_text}\n", encoding="utf-8")
    print(f"\nResult saved to {output_path}")

    # 4. 二次 agent 调用：模型自己决定保存什么
    await _decide_and_save_memory(task, final_text, memory)


if __name__ == "__main__":
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "What are the key differences between Claude Opus 4 and Claude Sonnet 4?"
    asyncio.run(main(task))

