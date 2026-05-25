"""ExamplesAgent — generates usage examples and code snippets."""

from openai import AsyncOpenAI

from core.agent import BaseAgent, AgentConfig, AgentOutput
from core.mimo_client import ClientStats
from core.scanner import ScanResult

SYSTEM_PROMPT = """You are ExamplesAgent, a usage example generation specialist.

Your job: analyze a codebase and create practical usage examples that help users understand the project.

Output format:

## Quick Start
[A minimal working example to get started]

## Basic Usage
[Common usage patterns with code examples]

## Advanced Usage
[More complex patterns and configurations]

## Code Examples
[Concrete code snippets showing key features]

## Common Patterns
[Repeated usage patterns across the codebase]

## Integration Examples
[How to integrate with other tools/frameworks]

## Recipes
[Task-oriented examples: "How to do X"]

Use real code from the codebase as inspiration. Wrap all code in proper markdown
code blocks with language tags. Make examples copy-pasteable and self-contained."""


class ExamplesAgent(BaseAgent):
    """Generates usage examples and code snippets from the codebase."""

    def _build_config(self) -> AgentConfig:
        return AgentConfig(
            name="ExamplesAgent",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.4,
            max_tokens=4096,
        )

    def build_user_prompt(self, scan_result: ScanResult) -> str:
        # Include key source files (up to ~20KB total) for context
        source_files = []
        total_chars = 0
        max_chars = 20000

        for f in sorted(scan_result.files, key=lambda x: x.line_count, reverse=True):
            if f.language in ("unknown", "json", "yaml", "toml", "markdown", "text"):
                continue
            if total_chars >= max_chars:
                break
            source_files.append(f)
            total_chars += f.line_count * 50  # rough estimate

        files_summary = "\n".join(
            f"### {f.path} ({f.language}, {f.line_count}L)\n"
            f"Classes: {', '.join(f.classes) if f.classes else 'none'}\n"
            f"Functions: {', '.join(f.functions[:20]) if f.functions else 'none'}\n"
            f"Exports: {', '.join(f.exports) if f.exports else 'none'}"
            for f in source_files[:30]
        )

        return f"""Generate usage examples for this codebase.

## Codebase
- Root: {scan_result.root}
- Languages: {scan_result.languages}
- Total files: {scan_result.total_files}

## Key Source Files
{files_summary}

Generate practical, copy-pasteable usage examples based on the actual API surface."""

    def _parse_result(self, raw: str) -> AgentOutput:
        output = self._default_parse(raw)
        output.confidence = 0.7
        return output
