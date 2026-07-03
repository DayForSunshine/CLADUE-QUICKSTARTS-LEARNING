"""Session summarizer — distills a conversation into persistent Claude Code memories."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agents.agent import Agent

# Default Claude Code project memory dir for this workspace
_DEFAULT_MEMORY_DIR = (
    Path.home()
    / ".claude/projects/-media-prince-data6-Claude-projects-claude-quickstarts/memory"
)

_SUMMARIZE_PROMPT = """\
你是记忆提炼助手。请仔细阅读以下 agent 对话历史，提炼出值得在未来会话中复用的信息。

提炼类型及标准：
- **user**：用户身份、技能水平、工作职责、明确表达的偏好
- **feedback**：用户对 AI 行为的纠正或认可（要做什么/不要做什么）
- **project**：项目目标、架构决策、重要背景、关键约束
- **reference**：外部资源位置（文件路径、URL、系统名称）

不需要保存的内容：
- 可从代码或 git 历史推导的信息
- 当前任务的临时状态
- 本次会话结束后立即过期的信息

---
对话历史：
{history}
---

如果有值得保存的内容，请严格按以下 JSON 数组格式回复（可包含多条，每条对应一个独立主题）：
[
  {{
    "name": "kebab-case-slug（英文，全小写，唯一标识）",
    "description": "一行摘要（英文或中文均可，50字以内）",
    "type": "user|feedback|project|reference",
    "content": "记忆正文。feedback 类型请包含：规则本身、\\n\\n**Why:** 原因、\\n\\n**How to apply:** 适用场景。project 类型请包含：事实/决策、\\n\\n**Why:** 动机、\\n\\n**How to apply:** 如何影响建议。"
  }}
]

如果没有值得保存的内容，只回复：null
"""


class SessionSummarizer:
    """Distills agent conversation history into persistent Claude Code memory files.

    Saves to the Claude Code per-project memory directory so memories surface
    automatically in future Claude Code sessions.

    Usage::

        summarizer = SessionSummarizer()
        paths = summarizer.save_from_agent(agent)
        # or async:
        paths = await summarizer.async_save_from_agent(agent)
    """

    def __init__(self, memory_dir: Path | str | None = None):
        self.memory_dir = Path(memory_dir) if memory_dir else _DEFAULT_MEMORY_DIR
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.memory_dir / "MEMORY.md"

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def save_from_agent(
        self,
        agent: Agent,
        model: str = "claude-haiku-4-5-20251001",
        verbose: bool = False,
    ) -> list[Path]:
        """Summarize `agent`'s history and persist memories synchronously."""
        history_text = _format_history(agent.history.messages)
        if not history_text.strip():
            return []
        return self._run_and_save(history_text, agent.client, model, verbose)

    async def async_save_from_agent(
        self,
        agent: Agent,
        model: str = "claude-haiku-4-5-20251001",
        verbose: bool = False,
    ) -> list[Path]:
        """Summarize `agent`'s history and persist memories asynchronously."""
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.save_from_agent(agent, model, verbose)
        )

    def save_from_history(
        self,
        history_text: str,
        client: Any,
        model: str = "claude-haiku-4-5-20251001",
        verbose: bool = False,
    ) -> list[Path]:
        """Summarize arbitrary history text and persist memories."""
        return self._run_and_save(history_text, client, model, verbose)

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    def _run_and_save(
        self,
        history_text: str,
        client: Any,
        model: str,
        verbose: bool,
    ) -> list[Path]:
        prompt = _SUMMARIZE_PROMPT.format(history=history_text)
        response = client.messages.create(
            model=model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = "\n".join(
            b.text for b in response.content if b.type == "text"
        ).strip()

        if verbose:
            print(f"\n[SessionSummarizer] raw decision:\n{raw[:400]}")

        entries = _parse_entries(raw)
        if not entries:
            if verbose:
                print("[SessionSummarizer] Nothing worth saving.")
            return []

        saved: list[Path] = []
        for entry in entries:
            path = self._write_entry(entry)
            saved.append(path)
            if verbose:
                print(f"[SessionSummarizer] Saved → {path}")
        return saved

    def _write_entry(self, entry: dict) -> Path:
        slug = re.sub(r"[^a-z0-9-]", "-", entry["name"].lower()).strip("-")
        file_path = self.memory_dir / f"{slug}.md"
        mem_type = entry.get("type", "project")
        description = entry.get("description", "")
        content = entry.get("content", "")

        # If file exists, merge by appending update note rather than overwriting
        if file_path.exists():
            existing = file_path.read_text(encoding="utf-8")
            body = _strip_frontmatter(existing)
            # Replace body with new content (latest wins)
            content = content.strip()

        file_path.write_text(
            f"---\n"
            f"name: {slug}\n"
            f"description: {description}\n"
            f"metadata:\n"
            f"  type: {mem_type}\n"
            f"---\n\n"
            f"{content.strip()}\n",
            encoding="utf-8",
        )
        self._update_index(slug, description, file_path.name)
        return file_path

    def _update_index(self, slug: str, description: str, filename: str) -> None:
        lines: list[str] = []
        if self.index_path.exists():
            lines = self.index_path.read_text(encoding="utf-8").splitlines()

        marker = f"[{slug}]"
        new_line = f"- [{slug}]({filename}) — {description}"
        replaced = False
        for i, line in enumerate(lines):
            if marker in line:
                lines[i] = new_line
                replaced = True
                break

        if not replaced:
            if not any("Memory Index" in l for l in lines):
                lines.insert(0, "# Memory Index\n")
            lines.append(new_line)

        self.index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

def _format_history(messages: list[dict]) -> str:
    """Convert message list to a readable text for the summarizer."""
    parts: list[str] = []
    for msg in messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")

        if isinstance(content, str):
            parts.append(f"[{role}]: {content}")
            continue

        if isinstance(content, list):
            texts: list[str] = []
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "text":
                        texts.append(block["text"])
                    # Skip tool_use / tool_result blocks — they are noisy
                elif hasattr(block, "type"):
                    if block.type == "text":
                        texts.append(block.text)
            if texts:
                parts.append(f"[{role}]: " + "\n".join(texts))

    return "\n\n".join(parts)


def _parse_entries(text: str) -> list[dict]:
    """Extract JSON array from model response; return [] if none found."""
    stripped = text.strip().lower()
    if stripped in ("null", "none", ""):
        return []

    # Strip markdown code block wrapper
    code_block = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if code_block:
        text = code_block.group(1)

    arr_match = re.search(r"\[.*\]", text, re.DOTALL)
    if not arr_match:
        return []

    try:
        data = json.loads(arr_match.group())
        if isinstance(data, list):
            return [
                e for e in data
                if isinstance(e, dict) and "name" in e and "content" in e
            ]
    except json.JSONDecodeError:
        pass
    return []


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            return text[end + 3:].lstrip("\n")
    return text
