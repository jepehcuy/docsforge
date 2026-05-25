"""ChangelogAgent — documents change history and versioning patterns."""

from openai import AsyncOpenAI

from core.agent import BaseAgent, AgentConfig, AgentOutput
from core.mimo_client import ClientStats
from core.scanner import ScanResult

SYSTEM_PROMPT = """You are ChangelogAgent, a versioning and change history specialist.

Your job: analyze a codebase to document versioning patterns, changelog conventions,
and change history. Even if no formal changelog exists, infer versioning from the code.

Output format:

## Version Info
[Current version, version scheme detected]

## Changelog Convention
[What format the project uses: Keep a Changelog, semver, etc.]

## Recent Changes
[Inferred from file modifications, git patterns, or existing changelogs]

## Breaking Changes
[Any potential breaking changes detected]

## Migration Notes
[Upgrade/migration guidance based on detected changes]

## Version History
[Structured changelog entries]

If no changelog exists, create a template based on what you can infer from the code.
If git history is not available, note that and provide a recommended changelog structure."""


class ChangelogAgent(BaseAgent):
    """Documents change history, versioning, and migration patterns."""

    def _build_config(self) -> AgentConfig:
        return AgentConfig(
            name="ChangelogAgent",
            system_prompt=SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=4096,
        )

    def build_user_prompt(self, scan_result: ScanResult) -> str:
        # Look for changelog-related files
        changelog_files = [
            f for f in scan_result.files
            if any(x in f.path.lower() for x in ["changelog", "history", "changes", "release", "version"])
        ]

        # Look for version indicators in config files
        config_info = "\n".join(scan_result.config_files)

        # Check for common version patterns
        version_files = [
            f for f in scan_result.files
            if f.path.endswith(("__version__.py", "version.py", "VERSION"))
            or f.path.endswith(("version.txt", "version", ".version"))
        ]

        changelog_files_text = "\n".join(f.path for f in changelog_files) or "None found"
        version_files_text = "\n".join(f.path for f in version_files) or "None found"

        return f"""Analyze the versioning and changelog patterns in this codebase.

## Codebase
- Root: {scan_result.root}
- Languages: {scan_result.languages}

## Config Files
{config_info}

## Changelog-related Files
{changelog_files_text}

## Version Files
{version_files_text}

## Doc Files
{chr(10).join(scan_result.doc_files)}

Analyze versioning patterns and produce changelog documentation."""

    def _parse_result(self, raw: str) -> AgentOutput:
        output = self._default_parse(raw)
        output.confidence = 0.6  # Lower confidence since changelogs are often incomplete
        return output
