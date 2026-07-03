---
description: Run a Claude agent with Anthropic's server-side WebSearchServerTool to research a topic and return a cited summary
disable-model-invocation: true
argument-hint: <search task>
---

## Task

$ARGUMENTS

## Tool implementation

!`cat /media/prince/data6/Claude_projects/claude-quickstarts/agents/tools/web_search.py`

## Instructions

Write a self-contained Python runner script to the scratchpad, then execute it with `python`.

The script must:
1. Add the repo root to `sys.path`
2. Import and instantiate `WebSearchServerTool`
3. Create an `Agent` with `verbose=True` and the search tool
4. Call `agent.run_async()` with the task above
5. Print all text blocks from the final response

```python
import asyncio, os, sys
sys.path.insert(0, "/media/prince/data6/Claude_projects/claude-quickstarts")

from agents.agent import Agent, ModelConfig
from agents.tools.web_search import WebSearchServerTool

async def main():
    agent = Agent(
        name="WebSearchAgent",
        system="You are a research assistant. Use the web_search tool to find accurate, up-to-date information. Always cite your sources and end with a concise summary.",
        tools=[WebSearchServerTool(max_uses=5)],
        config=ModelConfig(model="claude-opus-4-8", max_tokens=4096),
        verbose=True,
    )
    response = await agent.run_async("REPLACE_WITH_TASK")
    for block in response.content:
        if block.type == "text":
            print(block.text)

asyncio.run(main())
```

> **Note:** `WebSearchServerTool` is an Anthropic server-side tool. The web search
> runs inside the API — no `tool_use` block is returned to the client and no local
> `execute()` method is called. The agent loop exits as soon as Claude returns a
> pure-text response with search results already incorporated.

After the script exits, report:
- The key facts found
- Sources cited by the agent
- The agent's final summary
