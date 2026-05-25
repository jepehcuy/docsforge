"""ArchitectureAgent — analyzes codebase structure and design patterns."""

from openai import AsyncOpenAI

from core.agent import BaseAgent, AgentConfig, AgentOutput
from core.mimo_client import ClientStats
from core.scanner import ScanResult

SYSTEM_PROMPT = """You are ArchitectureAgent, a codebase architecture analysis specialist.

Your job: analyze a scanned codebase and produce comprehensive architecture documentation.

Output format (use ## for section headers):

## Overview
[High-level description of the project and its purpose]

## Project Structure
[Directory layout and what each major directory contains]

## Design Patterns
[Identified design patterns: MVC, pub-sub, plugin architecture, etc.]

## Module Dependencies
[How modules/packages depend on each other]

## Data Flow
[How data moves through the system]

## Key Components
[Major components/classes and their responsibilities]

## Technology Stack
[Languages, frameworks, libraries detected]

## Strengths
[What the architecture does well]

## Concerns
[Potential architectural issues or tech debt]

Be thorough. Base all analysis on the actual file tree and structural data provided."""


class ArchitectureAgent(BaseAgent):
    """Analyzes overall project structure and design patterns."""

    def _build_config(self) -> AgentConfig:
        return AgentConfig(
            name="ArchitectureAgent",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=4096,
        )

    def build_user_prompt(self, scan_result: ScanResult) -> str:
        # Summarize file tree (truncate for large repos)
        file_lines = []
        for f in scan_result.files[:200]:
            prefix = "  " * (f.path.count("/") or 0)
            file_lines.append(f"{prefix}{f.path} ({f.language}, {f.line_count}L)")

        file_tree = "\n".join(file_lines)
        if len(scan_result.files) > 200:
            file_tree += f"\n  ... and {len(scan_result.files) - 200} more files"

        # Summarize structural info
        all_classes = []
        all_imports = []
        for f in scan_result.files:
            all_classes.extend(f.classes)
            all_imports.extend(f.imports[:5])  # limit per file

        return f"""Analyze the architecture of this codebase.

## Codebase Summary
- Root: {scan_result.root}
- Total files: {scan_result.total_files}
- Total lines: {scan_result.total_lines}
- Languages: {scan_result.languages}
- Config files: {scan_result.config_files}

## File Tree
{file_tree}

## Key Classes/Types ({len(all_classes)} total)
{chr(10).join(all_classes[:100])}

## Top Imports/Dependencies
{chr(10).join(sorted(set(all_imports))[:50])}

Produce comprehensive architecture documentation."""

    def _parse_result(self, raw: str) -> AgentOutput:
        output = self._default_parse(raw)
        output.confidence = 0.8
        return output
