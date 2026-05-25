"""APIAgent — documents public APIs, functions, classes, interfaces."""

from openai import AsyncOpenAI

from core.agent import BaseAgent, AgentConfig, AgentOutput
from core.mimo_client import ClientStats
from core.scanner import ScanResult

SYSTEM_PROMPT = """You are APIAgent, a public API documentation specialist.

Your job: analyze a codebase and produce comprehensive API reference documentation.

For each public API element, document:
- Name and type (function, class, method, etc.)
- Parameters and return types (if inferrable)
- Purpose and behavior
- Usage patterns

Output format:

## Public APIs
[Overview of the API surface]

## Functions
[Document each public function]

## Classes
[Document each public class with methods]

## Interfaces / Protocols
[Document interfaces, abstract classes, protocols]

## Type Definitions
[Document type aliases, enums, dataclasses]

## Constants and Configuration
[Document public constants]

Use markdown code blocks for signatures. Be precise about what is public vs internal.
Focus on the most important APIs first."""


class APIAgent(BaseAgent):
    """Documents public APIs, functions, classes, and interfaces."""

    def _build_config(self) -> AgentConfig:
        return AgentConfig(
            name="APIAgent",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=4096,
        )

    def build_user_prompt(self, scan_result: ScanResult) -> str:
        # Extract all public symbols from source files
        public_symbols = []
        for f in scan_result.files:
            if f.language in ("unknown", "json", "yaml", "toml", "markdown", "text"):
                continue
            entry = {"file": f.path, "language": f.language}
            if f.classes:
                entry["classes"] = f.classes
            if f.functions:
                entry["functions"] = f.functions
            if f.exports:
                entry["exports"] = f.exports
            if f.imports:
                entry["imports"] = f.imports[:10]
            if len(entry) > 2:  # has more than just file + language
                public_symbols.append(entry)

        symbols_text = "\n".join(str(s) for s in public_symbols[:100])

        return f"""Analyze and document the public APIs of this codebase.

## Codebase
- Root: {scan_result.root}
- Languages: {scan_result.languages}

## Detected Public Symbols
{symbols_text}

## File Line Counts (top files by size)
{chr(10).join(f'{f.path}: {f.line_count} lines' for f in sorted(scan_result.files, key=lambda x: x.line_count, reverse=True)[:50])}

Produce comprehensive API reference documentation."""

    def _parse_result(self, raw: str) -> AgentOutput:
        output = self._default_parse(raw)
        output.confidence = 0.75
        return output
