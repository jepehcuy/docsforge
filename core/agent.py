"""Base agent class for DocsForge specialist agents.

Each agent analyzes a codebase from a specific angle and produces
structured documentation output (markdown sections + metadata).
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from openai import AsyncOpenAI

from core.mimo_client import mimo_chat, ClientStats
from core.scanner import ScanResult


@dataclass
class AgentOutput:
    """Output from a single specialist agent."""
    agent_name: str
    # Documentation sections produced
    sections: dict[str, str] = field(default_factory=dict)  # title → markdown content
    # Metadata about the analysis
    findings: list[str] = field(default_factory=list)
    confidence: float = 0.5  # 0.0 to 1.0
    # Token usage for this agent
    token_usage: int = 0
    # Raw LLM response for debugging
    raw_response: str = ""
    # Files this agent focused on
    files_analyzed: list[str] = field(default_factory=list)


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    name: str
    system_prompt: str
    temperature: float = 0.3
    max_tokens: int = 4096


class BaseAgent(ABC):
    """Base class for all documentation specialist agents."""

    def __init__(self, client: AsyncOpenAI, model: str, stats: ClientStats | None = None):
        self.client = client
        self.model = model
        self.stats = stats or ClientStats()
        self.config = self._build_config()

    @abstractmethod
    def _build_config(self) -> AgentConfig:
        """Return the agent's configuration including system prompt."""
        ...

    @abstractmethod
    def build_user_prompt(self, scan_result: ScanResult) -> str:
        """Build the user-facing prompt from scan results."""
        ...

    @abstractmethod
    def _parse_result(self, raw: str) -> AgentOutput:
        """Parse LLM response into structured AgentOutput."""
        ...

    async def run(self, scan_result: ScanResult) -> AgentOutput:
        """Execute the agent and return structured documentation output."""
        user_prompt = self.build_user_prompt(scan_result)

        raw = await mimo_chat(
            self.client,
            self.model,
            messages=[
                {"role": "system", "content": self.config.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            stats=self.stats,
        )

        output = self._parse_result(raw)
        output.token_usage = sum(
            c.total_tokens for c in self.stats.calls
        )
        return output

    def _default_parse(self, raw: str, section_prefix: str = "") -> AgentOutput:
        """Default parsing: split on ## headings, treat as sections."""
        sections: dict[str, str] = {}
        findings: list[str] = []
        current_title = "Introduction"
        current_lines: list[str] = []

        for line in raw.split("\n"):
            if line.startswith("## "):
                if current_lines:
                    sections[current_title] = "\n".join(current_lines).strip()
                current_title = line[3:].strip()
                current_lines = []
            elif line.startswith("- "):
                findings.append(line[2:])
                current_lines.append(line)
            else:
                current_lines.append(line)

        if current_lines:
            sections[current_title] = "\n".join(current_lines).strip()

        return AgentOutput(
            agent_name=self.config.name,
            sections=sections,
            findings=findings,
            confidence=0.7,
            raw_response=raw,
        )
