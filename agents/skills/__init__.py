"""Skills module — reusable pre-configured agent bundles."""

from .base import Skill
from .file_ops import FileOpsSkill
from .web_search import WebSearchSkill

__all__ = ["Skill", "FileOpsSkill", "WebSearchSkill"]
