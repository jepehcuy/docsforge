"""ConfigAgent — documents configuration files and setup instructions."""

from openai import AsyncOpenAI

from core.agent import BaseAgent, AgentConfig, AgentOutput
from core.mimo_client import ClientStats
from core.scanner import ScanResult

SYSTEM_PROMPT = """You are ConfigAgent, a configuration and setup documentation specialist.

Your job: analyze configuration files and produce setup/installation documentation.

Output format:

## Installation
[How to install the project — pip install, npm install, cargo install, etc.]

## Prerequisites
[System requirements, language versions, dependencies]

## Configuration
[Document each configuration file and its options]

## Environment Variables
[Document all environment variables the project uses]

## Development Setup
[How to set up a development environment]

## Build & Deploy
[How to build and deploy the project]

## Troubleshooting
[Common issues and their solutions]

Be specific about file paths and configuration values. Include code blocks
for config file formats. Document both required and optional settings."""


class ConfigAgent(BaseAgent):
    """Documents configuration files, environment, and setup procedures."""

    def _build_config(self) -> AgentConfig:
        return AgentConfig(
            name="ConfigAgent",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.2,
            max_tokens=4096,
        )

    def build_user_prompt(self, scan_result: ScanResult) -> str:
        # Group config files by type
        config_files = []
        for f in scan_result.files:
            if f.path in scan_result.config_files or any(
                kw in f.path.lower()
                for kw in ["config", "setup", "env", "docker", "makefile", "ci", "cd", "workflow", "action"]
            ):
                config_files.append(f)

        config_summary = "\n".join(
            f"### {f.path} ({f.language}, {f.size_bytes}B)\n"
            f"Lines: {f.line_count}"
            for f in config_files[:30]
        ) or "No configuration files detected"

        # Build environment variable hints
        env_hints = []
        for f in scan_result.files:
            if f.language in ("python", "javascript", "typescript", "go"):
                for imp in f.imports:
                    if "env" in imp.lower() or "config" in imp.lower():
                        env_hints.append(f"{f.path}: {imp}")

        env_text = "\n".join(env_hints[:20]) or "None detected"

        return f"""Document the configuration and setup for this codebase.

## Codebase
- Root: {scan_result.root}
- Languages: {scan_result.languages}

## Config Files ({len(config_files)} found)
{config_summary}

## Environment Variable References
{env_text}

## Documentation Files
{chr(10).join(scan_result.doc_files) or 'None'}

Produce comprehensive configuration and setup documentation."""

    def _parse_result(self, raw: str) -> AgentOutput:
        output = self._default_parse(raw)
        output.confidence = 0.75
        return output
