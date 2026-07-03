"""Pre-built web search skill."""

from .base import Skill
from ..tools.web_search import WebSearchServerTool


def WebSearchSkill(max_uses: int = 5) -> Skill:
    """Research agent equipped with Anthropic's server-side web search tool."""
    return Skill(
        name="WebSearchAgent",
        description="Search the web and return a cited summary.",
        system=(
            "You are a research assistant. Use the web_search tool to find accurate, "
            "up-to-date information. Always cite your sources and end with a concise summary."
        ),
        tools=[WebSearchServerTool(max_uses=max_uses)],
    )
