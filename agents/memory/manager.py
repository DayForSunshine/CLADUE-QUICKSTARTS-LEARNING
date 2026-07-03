"""Persistent memory manager for agents — read/write across runs."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


class MemoryManager:
    """Read and write agent memories stored as markdown files.

    Directory layout:
        store/
            MEMORY.md          ← index of all entries
            <slug>.md          ← individual memory file
    """

    def __init__(self, store_dir: Path | str | None = None):
        if store_dir is None:
            store_dir = Path(__file__).parent / "store"
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.store_dir / "MEMORY.md"

    # ------------------------------------------------------------------ #
    # Write                                                                #
    # ------------------------------------------------------------------ #

    def save(self, name: str, content: str, description: str) -> Path:
        """Write a memory entry and update the index.

        Args:
            name:        kebab-case slug, e.g. "user-preference-lang"
            content:     body of the memory
            description: one-line summary shown in MEMORY.md index

        Returns:
            Path to the written memory file.
        """
        slug = re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-")
        file_path = self.store_dir / f"{slug}.md"

        file_path.write_text(
            f"---\n"
            f"name: {slug}\n"
            f"description: {description}\n"
            f"updated: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"---\n\n"
            f"{content.strip()}\n",
            encoding="utf-8",
        )
        self._update_index(slug, description, file_path.name)
        return file_path

    def delete(self, name: str) -> bool:
        """Remove a memory entry and its index line."""
        slug = re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-")
        file_path = self.store_dir / f"{slug}.md"
        if not file_path.exists():
            return False
        file_path.unlink()
        self._remove_from_index(slug)
        return True

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    def load_all(self) -> str:
        """Return all memory content concatenated as a single string.
        Suitable for injecting into an agent system prompt or first message.
        """
        files = sorted(self.store_dir.glob("*.md"))
        files = [f for f in files if f.name != "MEMORY.md"]
        if not files:
            return ""

        parts = ["<memory>"]
        for f in files:
            body = self._strip_frontmatter(f.read_text(encoding="utf-8"))
            if body.strip():
                parts.append(f"## {f.stem}\n{body.strip()}")
        parts.append("</memory>")
        return "\n\n".join(parts)

    def load_index(self) -> str:
        """Return the raw MEMORY.md index."""
        if not self.index_path.exists():
            return ""
        return self.index_path.read_text(encoding="utf-8")

    def list_entries(self) -> list[dict[str, str]]:
        """Return a list of {name, description} dicts from the index."""
        entries = []
        for f in sorted(self.store_dir.glob("*.md")):
            if f.name == "MEMORY.md":
                continue
            text = f.read_text(encoding="utf-8")
            name = self._frontmatter_value(text, "name") or f.stem
            desc = self._frontmatter_value(text, "description") or ""
            entries.append({"name": name, "description": desc})
        return entries

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _update_index(self, slug: str, description: str, filename: str):
        lines = []
        if self.index_path.exists():
            lines = self.index_path.read_text(encoding="utf-8").splitlines()

        # Replace existing entry or append
        marker = f"[{slug}]"
        new_line = f"- [{slug}]({filename}) — {description}"
        replaced = False
        for i, line in enumerate(lines):
            if marker in line:
                lines[i] = new_line
                replaced = True
                break

        if not replaced:
            if not lines:
                lines.append("# Memory Index\n")
            lines.append(new_line)

        self.index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def _remove_from_index(self, slug: str):
        if not self.index_path.exists():
            return
        lines = self.index_path.read_text(encoding="utf-8").splitlines()
        lines = [l for l in lines if f"[{slug}]" not in l]
        self.index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def _strip_frontmatter(text: str) -> str:
        if text.startswith("---"):
            end = text.find("---", 3)
            if end != -1:
                return text[end + 3:].lstrip("\n")
        return text

    @staticmethod
    def _frontmatter_value(text: str, key: str) -> str | None:
        for line in text.splitlines():
            if line.startswith(f"{key}:"):
                return line.split(":", 1)[1].strip()
        return None
