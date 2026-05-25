"""ArchitectureAgent — produces system overview + Mermaid diagrams."""

from openai import AsyncOpenAI
from docsforge.core.agent import BaseAgent, AgentConfig
from docsforge.core.scanner import RepoMeta, summarize_repo


class ArchitectureAgent(BaseAgent):
    """Generates the architecture overview page."""

    def __init__(self, client: AsyncOpenAI, model: str):
        super().__init__(
            AgentConfig(
                name="ArchitectureAgent",
                system_prompt=(
                    "You are ArchitectureAgent, a senior staff engineer who "
                    "writes architecture documentation. Given a repo summary, "
                    "produce a single Markdown page covering: "
                    "1. One-paragraph project description, "
                    "2. Tech stack table (language, framework, purpose), "
                    "3. Directory structure as a tree, "
                    "4. A Mermaid flowchart showing major components and how data flows, "
                    "5. Key design decisions in 3-5 bullets. "
                    "Output ONLY the Markdown — no preamble, no code fences around the whole doc. "
                    "Use ```mermaid blocks for diagrams. Be concise but precise."
                ),
                temperature=0.3,
                max_tokens=3500,
            ),
            client,
            model,
        )

    def build_user_prompt(self, meta: RepoMeta) -> str:
        # Build a directory tree string
        tree_lines: list[str] = []
        seen_dirs: set[str] = set()
        for f in meta.files[:200]:
            parts = f.path.split("/")
            for i in range(1, len(parts)):
                d = "/".join(parts[:i])
                if d not in seen_dirs:
                    seen_dirs.add(d)
                    tree_lines.append(f"  {'  ' * (i - 1)}{parts[i-1]}/")
        tree = "\n".join(sorted(set(tree_lines))[:60]) or "(empty)"

        sample_symbols = "\n".join(
            f"- {s.kind} `{s.name}` in `{s.file}`"
            for s in meta.python_symbols[:30]
        ) or "(no Python symbols extracted)"

        return f"""## Repo Summary

{summarize_repo(meta)}

## Directory Tree (sample)
```
{tree}
```

## Sample Public Symbols
{sample_symbols}

## Config Files
{', '.join(meta.config_files) or 'none'}

Now write the architecture overview page as Markdown."""

    def parse_response(self, raw: str, meta: RepoMeta) -> dict[str, str]:
        # Strip wrapping ```markdown fences if present
        content = raw.strip()
        if content.startswith("```markdown"):
            content = content[len("```markdown"):].strip()
        if content.startswith("```"):
            content = content[3:].strip()
        if content.endswith("```"):
            content = content[:-3].strip()

        if not content.lstrip().startswith("#"):
            content = f"# Architecture\n\n{content}"
        return {"architecture.md": content}
