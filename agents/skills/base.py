"""Base Skill class — a reusable, pre-configured agent bundle."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..agent import Agent, ModelConfig
    from ..tools.base import Tool


@dataclass
class Skill:
    """A named, reusable agent configuration.

    Bundles a system prompt, tool set, and model config so that the same
    agent behaviour can be instantiated repeatedly without repeating setup.

    Usage::

        skill = WebSearchSkill()
        agent = skill.create_agent(verbose=True)
        response = agent.run("your task")
    """

    name: str
    description: str
    system: str
    tools: list[Any] = field(default_factory=list)
    model: str = "claude-opus-4-8"
    max_tokens: int = 4096
    mcp_servers: list[dict[str, Any]] = field(default_factory=list)

    def create_agent(self, **kwargs) -> "Agent":
        """Instantiate an Agent from this skill.

        Any keyword argument accepted by Agent.__init__ can be passed to
        override the skill's defaults (e.g. verbose=True, client=...).
        """
        from ..agent import Agent, ModelConfig

        return Agent(
            name=kwargs.pop("name", self.name),
            system=kwargs.pop("system", self.system),
            tools=kwargs.pop("tools", list(self.tools)),
            mcp_servers=kwargs.pop("mcp_servers", list(self.mcp_servers)),
            config=kwargs.pop(
                "config",
                ModelConfig(model=self.model, max_tokens=self.max_tokens),
            ),
            **kwargs,
        )
