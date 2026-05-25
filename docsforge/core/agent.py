"""Base agent class for DocsForge specialist agents."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from openai import AsyncOpenAI

from docsforge.core.llm import chat
from docsforge.core.scanner import RepoMeta


@dataclass
class AgentOutput:
    """Output from a specialist agent."""
    agent_name: str
    pages: dict[str, str]      # filename -> markdown content
    tokens_used: int = 0
    raw_response: str = ""
    notes: list[str] = None     # type: ignore

    def __post_init__(self):
        if self.notes is None:
            self.notes = []


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    name: str
    system_prompt: str
    temperature: float = 0.3
    max_tokens: int = 4096


class BaseAgent(ABC):
    """Base class for all specialist documentation agents."""

    def __init__(self, config: AgentConfig, client: AsyncOpenAI, model: str):
        self.config = config
        self.client = client
        self.model = model

    @abstractmethod
    def build_user_prompt(self, meta: RepoMeta) -> str:
        """Build the user-facing prompt for this agent."""
        ...

    @abstractmethod
    def parse_response(self, raw: str, meta: RepoMeta) -> dict[str, str]:
        """Parse the LLM response into a {filename: markdown} dict."""
        ...

    async def run(self, meta: RepoMeta) -> AgentOutput:
        """Execute the agent and return structured output."""
        user_prompt = self.build_user_prompt(meta)

        raw, tokens = await chat(
            self.client,
            self.model,
            messages=[
                {"role": "system", "content": self.config.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        try:
            pages = self.parse_response(raw, meta)
        except Exception as exc:
            pages = {}
            return AgentOutput(
                agent_name=self.config.name,
                pages=pages,
                tokens_used=tokens,
                raw_response=raw,
                notes=[f"Parse error: {exc}"],
            )

        return AgentOutput(
            agent_name=self.config.name,
            pages=pages,
            tokens_used=tokens,
            raw_response=raw,
        )
