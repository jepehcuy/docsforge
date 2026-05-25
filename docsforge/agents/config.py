"""ConfigAgent — produces setup/deployment guide from config files."""

from pathlib import Path
from openai import AsyncOpenAI
from docsforge.core.agent import BaseAgent, AgentConfig
from docsforge.core.scanner import RepoMeta


def _read_snippet(abs_path: str, max_chars: int = 4000) -> str:
    try:
        text = Path(abs_path).read_text(encoding="utf-8", errors="ignore")
        return text[:max_chars]
    except OSError:
        return ""


class ConfigAgent(BaseAgent):
    """Generates the setup & deployment guide."""

    def __init__(self, client: AsyncOpenAI, model: str):
        super().__init__(
            AgentConfig(
                name="ConfigAgent",
                system_prompt=(
                    "You are ConfigAgent, a DevOps documentation specialist. "
                    "Given excerpts from a project's configuration files, produce "
                    "a single 'Setup & Deployment' Markdown page that explains: "
                    "1. Prerequisites (runtime, package manager), "
                    "2. Installation steps (commands), "
                    "3. Required environment variables (table), "
                    "4. Local development workflow, "
                    "5. Production deployment (if Dockerfile / Procfile present). "
                    "Be specific. If a value is missing, mark it as TODO. Output ONLY Markdown."
                ),
                temperature=0.2,
                max_tokens=3500,
            ),
            client,
            model,
        )

    def build_user_prompt(self, meta: RepoMeta) -> str:
        if not meta.config_files:
            return (
                f"Repository '{meta.name}' has no recognized config files. "
                "Output a placeholder 'Setup & Deployment' page recommending which "
                "config files the project should add (pyproject.toml or package.json, "
                ".env.example, Dockerfile, etc.)."
            )

        snippets = []
        for cf in meta.config_files[:8]:
            abs_path = str(Path(meta.root) / cf)
            snippet = _read_snippet(abs_path)
            snippets.append(f"### `{cf}`\n```\n{snippet}\n```")

        return f"""Repo: {meta.name}
Languages: {', '.join(meta.languages.keys())}

## Config files

{chr(10).join(snippets)}

Produce the Setup & Deployment page now."""

    def parse_response(self, raw: str, meta: RepoMeta) -> dict[str, str]:
        content = raw.strip()
        for fence in ("```markdown", "```md", "```"):
            if content.startswith(fence):
                content = content[len(fence):].strip()
                break
        if content.endswith("```"):
            content = content[:-3].strip()
        if not content.lstrip().startswith("#"):
            content = f"# Setup & Deployment\n\n{content}"
        return {"setup.md": content}
