"""ExamplesAgent — writes runnable usage examples."""

from openai import AsyncOpenAI
from docsforge.core.agent import BaseAgent, AgentConfig
from docsforge.core.scanner import RepoMeta


class ExamplesAgent(BaseAgent):
    """Generates a Getting Started / examples page."""

    def __init__(self, client: AsyncOpenAI, model: str):
        super().__init__(
            AgentConfig(
                name="ExamplesAgent",
                system_prompt=(
                    "You are ExamplesAgent, a developer-experience specialist. "
                    "Given a repo summary and key public symbols, write a "
                    "Getting Started page with 3-5 runnable code examples that "
                    "show real usage. Each example must have: a heading, "
                    "1-2 sentence context, and a fenced code block in the right "
                    "language. Examples should compose from simple to advanced. "
                    "Output ONLY Markdown. No preamble."
                ),
                temperature=0.4,
                max_tokens=3500,
            ),
            client,
            model,
        )

    def build_user_prompt(self, meta: RepoMeta) -> str:
        symbols = "\n".join(
            f"- {s.kind} `{s.signature}` (file: {s.file})"
            for s in meta.python_symbols[:30]
        ) or "(none extracted)"

        primary_lang = max(meta.languages.items(), key=lambda kv: kv[1])[0] if meta.languages else "python"

        return f"""## Repo

Name: {meta.name}
Primary language: {primary_lang}
Has examples folder: {meta.has_examples}
Has tests: {meta.has_tests}
README path: {meta.readme_path or 'missing'}

## Key public symbols
{symbols}

Write the Getting Started + examples page now. Lead with installation, then a hello-world, then 2-3 progressively richer examples."""

    def parse_response(self, raw: str, meta: RepoMeta) -> dict[str, str]:
        content = raw.strip()
        for fence in ("```markdown", "```md", "```"):
            if content.startswith(fence):
                content = content[len(fence):].strip()
                break
        if content.endswith("```"):
            content = content[:-3].strip()
        if not content.lstrip().startswith("#"):
            content = f"# Getting Started\n\n{content}"
        return {"getting-started.md": content}
