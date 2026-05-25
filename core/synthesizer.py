"""Synthesizer — merges agent outputs into mkdocs site files."""

import os
from dataclasses import dataclass
from openai import AsyncOpenAI

from core.agent import AgentOutput
from core.mimo_client import mimo_chat, ClientStats, MIMO_MODEL
from core.scanner import ScanResult


@dataclass
class SynthesisResult:
    """Final synthesized mkdocs site."""
    site_dir: str  # output directory
    pages: dict[str, str]  # relative_path → markdown content
    nav: list[dict]  # mkdocs nav structure
    mkdocs_config: str  # mkdocs.yml content


SYNTHESIS_SYSTEM_PROMPT = """You are the Documentation Synthesizer for DocsForge.

You receive analysis from 5 specialist agents who analyzed a codebase:
1. ArchitectureAgent - overall structure and design patterns
2. APIAgent - public APIs, functions, classes, interfaces
3. ExamplesAgent - usage examples and code snippets
4. ChangelogAgent - change history, versioning patterns
5. ConfigAgent - configuration files and setup instructions

Your job: merge all agent outputs into a complete mkdocs documentation site.

You must produce output in this EXACT format:

---NAV---
- Home: index.md
- Architecture: architecture.md
- API Reference: api-reference.md
- Examples: examples.md
- Configuration: configuration.md
- Changelog: changelog.md
---END NAV---

---MKDOCS CONFIG---
site_name: [Project Name]
site_description: [Brief description from architecture analysis]
theme:
  name: material
  palette:
    - scheme: default
      primary: indigo
      accent: indigo
---END MKDOCS CONFIG---

---FILE: index.md---
# [Project Name]

[Brief intro paragraph from architecture analysis]

## Quick Start
[From config agent]

## Key Features
[From architecture agent]
---END FILE---

[Repeat for each page with ---FILE: filename.md--- / ---END FILE---]

Be comprehensive. Use ALL information from agents. Format as clean markdown
suitable for mkdocs-material theme. Include cross-references between pages."""


class Synthesizer:
    """Merges agent outputs into mkdocs site files."""

    def __init__(self, client: AsyncOpenAI, model: str = MIMO_MODEL, stats: ClientStats | None = None):
        self.client = client
        self.model = model
        self.stats = stats or ClientStats()

    async def synthesize(
        self,
        scan_result: ScanResult,
        agent_outputs: dict[str, AgentOutput],
    ) -> SynthesisResult:
        """Produce mkdocs site from agent outputs."""
        # Build user message with all agent outputs
        agent_block = ""
        for name, output in agent_outputs.items():
            agent_block += f"\n\n## {name} (confidence: {output.confidence})\n"
            for title, content in output.sections.items():
                agent_block += f"\n### {title}\n{content}\n"
            if output.findings:
                agent_block += "\nKey findings:\n"
                for f in output.findings:
                    agent_block += f"- {f}\n"

        user_msg = f"""## Codebase Scan Summary
- Root: {scan_result.root}
- Files: {scan_result.total_files}
- Languages: {scan_result.languages}
- Config files: {scan_result.config_files}
- Doc files: {scan_result.doc_files}

## Agent Analyses
{agent_block}

Generate the complete mkdocs documentation site."""

        raw = await mimo_chat(
            self.client,
            self.model,
            messages=[
                {"role": "system", "content": SYNTHESIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.2,
            max_tokens=8192,
            stats=self.stats,
        )

        return self._parse_synthesis(raw, scan_result)

    def _parse_synthesis(self, raw: str, scan_result: ScanResult) -> SynthesisResult:
        """Parse synthesis output into structured mkdocs site."""
        pages: dict[str, str] = {}
        nav: list[dict] = []
        mkdocs_config = ""

        # Extract NAV
        if "---NAV---" in raw and "---END NAV---" in raw:
            nav_text = raw.split("---NAV---")[1].split("---END NAV---")[0].strip()
            for line in nav_text.split("\n"):
                line = line.strip()
                if ": " in line:
                    label, path = line.split(": ", 1)
                    nav.append({label.strip(): path.strip()})

        # Extract mkdocs config
        if "---MKDOCS CONFIG---" in raw and "---END MKDOCS CONFIG---" in raw:
            mkdocs_config = raw.split("---MKDOCS CONFIG---")[1].split("---END MKDOCS CONFIG---")[0].strip()

        # Extract files
        import re
        file_pattern = re.compile(
            r'---FILE:\s*(.+?)\s*---\n(.*?)\n---END FILE---',
            re.DOTALL,
        )
        for m in file_pattern.finditer(raw):
            filename = m.group(1).strip()
            content = m.group(2).strip()
            pages[filename] = content

        # Fallback: if no structured output, create basic pages
        if not pages:
            project_name = os.path.basename(scan_result.root)
            pages = self._create_fallback_pages(scan_result, agent_outputs={}, raw=raw)
            nav = [
                {"Home": "index.md"},
                {"Architecture": "architecture.md"},
                {"API Reference": "api-reference.md"},
                {"Examples": "examples.md"},
                {"Configuration": "configuration.md"},
            ]
            mkdocs_config = f"""site_name: {project_name}
site_description: Documentation for {project_name}
theme:
  name: material
  palette:
    - scheme: default
      primary: indigo
      accent: indigo
"""

        # Determine output dir
        site_dir = os.path.join(scan_result.root, "site-docs")

        return SynthesisResult(
            site_dir=site_dir,
            pages=pages,
            nav=nav or [{"Home": "index.md"}],
            mkdocs_config=mkdocs_config,
        )

    def _create_fallback_pages(
        self, scan_result: ScanResult, agent_outputs: dict, raw: str
    ) -> dict[str, str]:
        """Create basic fallback pages when synthesis parsing fails."""
        name = os.path.basename(scan_result.root)
        return {
            "index.md": f"# {name}\n\n{raw[:2000]}",
            "architecture.md": "# Architecture\n\nSee raw synthesis output.",
            "api-reference.md": "# API Reference\n\nSee raw synthesis output.",
            "examples.md": "# Examples\n\nSee raw synthesis output.",
            "configuration.md": "# Configuration\n\nSee raw synthesis output.",
        }

    def write_site(self, result: SynthesisResult) -> str:
        """Write the mkdocs site to disk. Returns the output directory path."""
        os.makedirs(result.site_dir, exist_ok=True)

        # Write mkdocs.yml
        config_path = os.path.join(result.site_dir, "mkdocs.yml")
        with open(config_path, "w") as f:
            f.write(result.mkdocs_config + "\n")

        # Write docs/ directory
        docs_dir = os.path.join(result.site_dir, "docs")
        os.makedirs(docs_dir, exist_ok=True)

        for filename, content in result.pages.items():
            filepath = os.path.join(docs_dir, filename)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w") as f:
                f.write(content + "\n")

        return result.site_dir
