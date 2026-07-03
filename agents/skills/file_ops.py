"""Pre-built file operations skill."""

from .base import Skill
from ..tools.file_tools import FileReadTool, FileWriteTool


def FileOpsSkill() -> Skill:
    """File system agent that can read, list, write, and edit local files."""
    return Skill(
        name="FileOpsAgent",
        description="Read, write, and edit local files.",
        system=(
            "You are a file system assistant. Use file_read to inspect files or list "
            "directories, and file_write to create or modify files. "
            "Confirm what you did at the end."
        ),
        tools=[FileReadTool(), FileWriteTool()],
    )
