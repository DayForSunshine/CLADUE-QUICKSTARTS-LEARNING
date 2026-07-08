"""Load Skill objects from YAML definition files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .base import Skill
from ..tools.file_tools import FileReadTool, FileWriteTool
from ..tools.web_search import WebSearchServerTool

# Default directory for YAML skill definitions
_DEFINITIONS_DIR = Path(__file__).parent / "definitions"

# Maps YAML tool type → factory function(config_dict) → tool instance
_TOOL_REGISTRY: dict[str, Any] = {
    "web_search": lambda cfg: WebSearchServerTool(max_uses=cfg.get("max_uses", 5)),
    "file_read":  lambda cfg: FileReadTool(),
    "file_write": lambda cfg: FileWriteTool(),
}

# Lazily registered tools (avoid import errors if deps missing)
def _get_think_tool(cfg: dict) -> Any:
    from ..tools.think import ThinkTool
    return ThinkTool()

def _get_code_tool(cfg: dict) -> Any:
    from ..tools.code_execution import CodeExecutionServerTool  #修改过
    return CodeExecutionServerTool()

_TOOL_REGISTRY["think"] = _get_think_tool
_TOOL_REGISTRY["code_execution"] = _get_code_tool


def load_skill(yaml_path: str | Path) -> Skill:
    """Load a Skill from a YAML file.

    Relative paths are resolved against agents/skills/definitions/.
    Absolute paths are used as-is.

    Args:
        yaml_path: Path to the YAML skill definition file.

    Returns:
        A configured Skill instance ready for create_agent().

    Example::

        skill = load_skill("web_search.yaml")
        agent = skill.create_agent(verbose=True)
        response = await agent.run_async("your task")
    """
    path = Path(yaml_path)
    if not path.is_absolute():
        path = _DEFINITIONS_DIR / path

    if not path.exists():
        raise FileNotFoundError(f"Skill definition not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)  

    tools = []
    for tool_cfg in data.get("tools", []):
        tool_type = tool_cfg.get("type")
        if tool_type not in _TOOL_REGISTRY:
            raise ValueError(
                f"Unknown tool type '{tool_type}' in {path.name}. "
                f"Available: {list(_TOOL_REGISTRY)}"
            )
        tools.append(_TOOL_REGISTRY[tool_type](tool_cfg))

    return Skill(
        name=data["name"],
        description=data.get("description", ""),
        system=data["system"].strip(),
        tools=tools,
        model=data.get("model", "claude-opus-4-8"),
        max_tokens=data.get("max_tokens", 4096),
        mcp_servers=data.get("mcp_servers", []),
    )
