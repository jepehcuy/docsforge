"""APIAgent — produces API reference pages from extracted symbols."""

from openai import AsyncOpenAI
from docsforge.core.agent import BaseAgent, AgentConfig
from docsforge.core.scanner import RepoMeta


class APIAgent(BaseAgent):
    """Generates API reference documentation."""

    def __init__(self, client: AsyncOpenAI, model: str):
        super().__init__(
            AgentConfig(
                name="APIAgent",
                system_prompt=(
                    "You are APIAgent, a documentation specialist. Given a list of "
                    "public functions and classes from a codebase (with signatures and "
                    "existing docstrings), produce a clean API reference in Markdown. "
                    "For each symbol: write a short one-line summary, list parameters "
                    "with types, describe the return value, and show a minimal usage "
                    "example. If the docstring is missing, infer behavior from the "
                    "signature and write a plausible description. "
                    "Group symbols by file. Output ONLY Markdown."
                ),
                temperature=0.3,
                max_tokens=4000,
            ),
            client,
            model,
        )

    def build_user_prompt(self, meta: RepoMeta) -> str:
        if not meta.python_symbols:
            return (
                "The repository has no extractable Python symbols. "
                "Output a single Markdown page with the heading '# API Reference' "
                "and a one-paragraph note that the project does not expose a public "
                "Python API in this scan, with suggestions on what to document if "
                "symbols are added later."
            )

        # Group by file
        by_file: dict[str, list[str]] = {}
        for s in meta.python_symbols[:80]:
            entry = (
                f"### `{s.signature}`\n"
                f"- File: `{s.file}` (line {s.line})\n"
                f"- Kind: {s.kind}\n"
                f"- Docstring: {s.docstring or '(none — please infer)'}\n"
            )
            by_file.setdefault(s.file, []).append(entry)

        blocks = []
        for file, entries in by_file.items():
            blocks.append(f"## {file}\n\n" + "\n".join(entries))

        return (
            f"Repo: {meta.name}\n\n"
            f"## Symbols to document ({sum(len(v) for v in by_file.values())} total)\n\n"
            + "\n\n".join(blocks)
            + "\n\nProduce the API reference Markdown now."
        )

    def parse_response(self, raw: str, meta: RepoMeta) -> dict[str, str]:
        content = raw.strip()
        for fence in ("```markdown", "```md", "```"):
            if content.startswith(fence):
                content = content[len(fence):].strip()
                break
        if content.endswith("```"):
            content = content[:-3].strip()

        if not content.lstrip().startswith("#"):
            content = f"# API Reference\n\n{content}"
        return {"api.md": content}
