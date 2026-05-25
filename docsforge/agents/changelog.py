"""ChangelogAgent — categorizes git history into release notes."""

import subprocess
from openai import AsyncOpenAI
from docsforge.core.agent import BaseAgent, AgentConfig
from docsforge.core.scanner import RepoMeta


def _git_log(repo_root: str, max_commits: int = 100) -> str:
    """Run `git log` and return condensed output."""
    try:
        result = subprocess.run(
            ["git", "log", f"-{max_commits}", "--pretty=format:%h|%ad|%s", "--date=short"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return ""


class ChangelogAgent(BaseAgent):
    """Generates a CHANGELOG.md from git history."""

    def __init__(self, client: AsyncOpenAI, model: str):
        super().__init__(
            AgentConfig(
                name="ChangelogAgent",
                system_prompt=(
                    "You are ChangelogAgent. Given a git commit log, produce a "
                    "CHANGELOG.md following Keep a Changelog conventions. "
                    "Group commits by Conventional Commit categories: Added, Changed, "
                    "Fixed, Removed, Security. Combine similar commits. If no clear "
                    "version tags exist, group by month. Output ONLY Markdown."
                ),
                temperature=0.2,
                max_tokens=3500,
            ),
            client,
            model,
        )

    def build_user_prompt(self, meta: RepoMeta) -> str:
        log = _git_log(meta.root) if meta.has_git else ""
        if not log:
            return (
                f"Repository '{meta.name}' has no git history (or git is not available). "
                "Output a placeholder CHANGELOG.md with a heading and a one-paragraph "
                "note explaining that no version history is available yet."
            )
        return f"""Repo: {meta.name}

Recent commit log (sha|date|subject):
{log}

Produce the CHANGELOG.md now."""

    def parse_response(self, raw: str, meta: RepoMeta) -> dict[str, str]:
        content = raw.strip()
        for fence in ("```markdown", "```md", "```"):
            if content.startswith(fence):
                content = content[len(fence):].strip()
                break
        if content.endswith("```"):
            content = content[:-3].strip()
        if not content.lstrip().startswith("#"):
            content = f"# Changelog\n\n{content}"
        return {"changelog.md": content}
