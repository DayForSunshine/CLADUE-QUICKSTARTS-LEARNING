---
description: Run a Claude agent with FileReadTool and FileWriteTool to perform local file read, write, and edit operations
disable-model-invocation: true
argument-hint: <task description>
---

## Task

$ARGUMENTS

## Available tool implementations

!`cat /media/prince/data6/Claude_projects/claude-quickstarts/agents/tools/file_tools.py`

## Instructions

Write a self-contained Python runner script to the scratchpad, then execute it with `python`.

The script must:
1. Add the repo root to `sys.path` so `agents` can be imported
2. Import and instantiate `FileReadTool` and `FileWriteTool`
3. Create an `Agent` with `verbose=True` and both tools
4. Call `agent.run_async()` with the task above
5. Print all text blocks from the final response

```python
import asyncio, os, sys
sys.path.insert(0, "/media/prince/data6/Claude_projects/claude-quickstarts")

from agents.agent import Agent, ModelConfig
from agents.tools.file_tools import FileReadTool, FileWriteTool

async def main():
    agent = Agent(
        name="FileAgent",
        system="You are a file system assistant. Use file_read to inspect files or list directories, and file_write to create or modify files. Confirm what you did at the end.",
        tools=[FileReadTool(), FileWriteTool()],
        config=ModelConfig(model="claude-opus-4-8", max_tokens=4096),
        verbose=True,
    )
    response = await agent.run_async("REPLACE_WITH_TASK")
    for block in response.content:
        if block.type == "text":
            print(block.text)

asyncio.run(main())
```

After the script exits, report:
- Which files were read or listed
- Which files were written or edited
- The agent's final answer
- Any tool errors (lines containing `Error:`)
