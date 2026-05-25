"""DocsForge CLI — Typer-based command-line interface."""

import asyncio
import os
from pathlib import Path

# IMPORTANT: load .env BEFORE importing modules that read env at import time
from dotenv import load_dotenv
load_dotenv()

import typer
from rich.console import Console
from rich.table import Table

from docsforge.core.scanner import scan_repo, summarize_repo
from docsforge.core.orchestrator import Orchestrator
from docsforge.core.llm import get_client, DEFAULT_MODEL
from docsforge.db.cache import init_cache, record_build

app = typer.Typer(
    add_completion=False,
    help="DocsForge — multi-agent documentation generator.",
)
console = Console()


@app.command()
def scan(
    path: str = typer.Argument(".", help="Path to the repository to scan"),
):
    """Scan a repo and print metadata without calling any LLM."""
    meta = scan_repo(path)
    console.print(f"[bold cyan]Scan results for {meta.name}[/bold cyan]")
    console.print(summarize_repo(meta))


@app.command()
def build(
    path: str = typer.Argument(".", help="Path to the repository"),
    output: str = typer.Option("./docs-build", help="Output directory for the docs site"),
    model: str = typer.Option(DEFAULT_MODEL, help="LLM model to use"),
):
    """Run the full docs pipeline on a repo."""
    console.print(f"[bold]Scanning repo at {path}...[/bold]")
    meta = scan_repo(path)
    console.print(f"  → {len(meta.files)} files, {meta.total_loc:,} LOC, "
                  f"{len(meta.python_symbols)} Python symbols")

    console.print(f"\n[bold]Running 5 agents in parallel against {model}...[/bold]")
    client = get_client()
    orch = Orchestrator(client, model)

    result = asyncio.run(orch.build(meta, output))

    # Record build in cache
    cache = init_cache()
    build_id = record_build(
        cache, result.repo_name, result.output_dir,
        result.total_tokens, result.pages_generated, len(result.errors),
    )
    cache.close()

    # Rich summary
    table = Table(title=f"Build #{build_id} — {result.repo_name}", show_header=True)
    table.add_column("Agent", style="cyan")
    table.add_column("Pages", justify="right")
    table.add_column("Tokens", justify="right")
    table.add_column("Notes", style="dim")
    for ao in result.agent_outputs:
        table.add_row(
            ao.agent_name,
            str(len(ao.pages)),
            f"{ao.tokens_used:,}",
            "; ".join(ao.notes) or "ok",
        )
    console.print(table)

    console.print(
        f"\n[bold green]✓ {result.pages_generated} pages generated[/bold green] "
        f"using [bold]{result.total_tokens:,} tokens[/bold]"
    )
    console.print(f"  Output: [cyan]{result.output_dir}[/cyan]")
    console.print(f"  Serve:  [dim]mkdocs serve -f {result.output_dir}/mkdocs.yml[/dim]")

    if result.errors:
        console.print(f"\n[red]Errors:[/red]")
        for e in result.errors:
            console.print(f"  - {e}")


@app.command()
def history(
    limit: int = typer.Option(10, help="Number of recent builds to show"),
):
    """Show recent build history from the cache."""
    cache = init_cache()
    cur = cache.execute(
        "SELECT id, repo_name, tokens_used, pages_generated, errors, created_at "
        "FROM builds ORDER BY id DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    cache.close()

    if not rows:
        console.print("[dim]No builds yet.[/dim]")
        return

    table = Table(title="Recent builds")
    table.add_column("ID", justify="right")
    table.add_column("Repo")
    table.add_column("Tokens", justify="right")
    table.add_column("Pages", justify="right")
    table.add_column("Errors", justify="right")
    table.add_column("When", style="dim")
    for row in rows:
        table.add_row(*[str(c) for c in row])
    console.print(table)


@app.command()
def version():
    """Show DocsForge version."""
    from docsforge import __version__
    console.print(f"DocsForge v{__version__}")


if __name__ == "__main__":
    app()
