"""DocsForge — CLI entry point.

Multi-agent documentation generation system.
Scans a codebase, runs 5 specialist agents, synthesizes into mkdocs site.
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()  # Load env BEFORE importing modules that read os.environ at import time

import typer

app = typer.Typer(
    name="docsforge",
    help="Multi-agent documentation generation system",
    add_completion=False,
)


def version_callback(value: bool):
    if value:
        typer.echo("docsforge 0.1.0")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v", callback=version_callback, is_eager=True,
        help="Show version and exit",
    ),
):
    """DocsForge: Multi-agent documentation generation system."""
    pass


@app.command()
def generate(
    path: str = typer.Argument(
        ".", help="Path to codebase root"
    ),
    output: str = typer.Option(
        None, "--output", "-o", help="Output directory (default: <path>/site-docs)"
    ),
    model: str = typer.Option(
        None, "--model", "-m", help="LLM model override"
    ),
    no_eval: bool = typer.Option(
        False, "--no-eval", help="Skip quality evaluation"
    ),
    incremental: bool = typer.Option(
        True, "--incremental/--full", help="Use incremental cache"
    ),
    skip_agents: str = typer.Option(
        "", "--skip-agents", help="Comma-separated agent names to skip"
    ),
):
    """Generate documentation for a codebase."""
    load_dotenv()
    asyncio.run(_generate(path, output, model, no_eval, incremental, skip_agents))


async def _generate(
    path: str,
    output: str | None,
    model: str | None,
    no_eval: bool,
    incremental: bool,
    skip_agents: str,
):
    from core.mimo_client import get_mimo_client, MIMO_MODEL, ClientStats
    from core.scanner import scan_codebase
    from core.orchestrator import Orchestrator
    from core.synthesizer import Synthesizer
    from db.cache import init_db, save_run, compute_files_hash

    typer.echo("🔍 Scanning codebase...")
    t0 = time.time()
    scan_result = scan_codebase(path)
    scan_time = time.time() - t0
    typer.echo(f"   Found {scan_result.total_files} files, {scan_result.total_lines} lines, {len(scan_result.languages)} languages ({scan_time:.1f}s)")

    # Init cache
    if incremental:
        await init_db()

    # Setup client
    client = get_mimo_client()
    used_model = model or MIMO_MODEL
    stats = ClientStats()

    # Filter agents
    skip_set = set(s.strip() for s in skip_agents.split(",") if s.strip())

    typer.echo(f"🤖 Running agents with model: {used_model}")
    t1 = time.time()
    orchestrator = Orchestrator(client, used_model, stats)

    # Filter out skipped agents
    if skip_set:
        orchestrator.agents = [
            a for a in orchestrator.agents
            if a.config.name not in skip_set
        ]

    agent_outputs = await orchestrator.run_all(scan_result)
    agent_time = time.time() - t1
    typer.echo(f"   {len(agent_outputs)} agents completed ({agent_time:.1f}s)")

    # Synthesize
    typer.echo("📝 Synthesizing documentation...")
    t2 = time.time()
    synthesizer = Synthesizer(client, used_model, stats)
    synth_result = await synthesizer.synthesize(scan_result, agent_outputs)
    site_dir = synthesizer.write_site(synth_result)
    synth_time = time.time() - t2
    typer.echo(f"   Wrote {len(synth_result.pages)} pages to {site_dir} ({synth_time:.1f}s)")

    # Evaluate
    quality_score = 0
    if not no_eval:
        typer.echo("⚖️  Evaluating quality...")
        t3 = time.time()
        from eval.scorer import DocScorer
        scorer = DocScorer(client, used_model, stats)
        score = await scorer.evaluate(scan_result, agent_outputs, synth_result.pages)
        quality_score = score.overall
        eval_time = time.time() - t3
        typer.echo(f"   Quality score: {score.overall}/100 ({eval_time:.1f}s)")
        typer.echo(f"   Completeness: {score.completeness}, Accuracy: {score.accuracy}")
        typer.echo(f"   Clarity: {score.clarity}, Structure: {score.structure}")
        typer.echo(f"   Usefulness: {score.usefulness}")
        if score.recommendations:
            typer.echo("   Recommendations:")
            for r in score.recommendations:
                typer.echo(f"     - {r}")

    # Save run history
    total_time = time.time() - t0
    usage = stats.to_dict()
    typer.echo(f"\n📊 Token usage: {usage['total_tokens']} total ({usage['num_calls']} calls)")
    typer.echo(f"   Duration: {total_time:.1f}s")

    if incremental:
        run_id = await save_run(
            root_path=os.path.abspath(path),
            total_files=scan_result.total_files,
            total_tokens=usage["total_tokens"],
            agents_run=list(agent_outputs.keys()),
            quality_score=quality_score,
            site_dir=site_dir,
            proof_data={
                "usage": usage,
                "total_time_s": round(total_time, 2),
                "scan_files": scan_result.total_files,
                "scan_lines": scan_result.total_lines,
                "languages": scan_result.languages,
                "quality_score": quality_score,
            },
        )
        typer.echo(f"   Run ID: {run_id}")

    typer.echo(f"\n✅ Done! Site at: {site_dir}")
    typer.echo(f"   Run: mkdocs serve -f {site_dir}/mkdocs.yml")


@app.command()
def scan(
    path: str = typer.Argument(".", help="Path to codebase root"),
    json_output: bool = typer.Option(False, "--json", "-j", help="Output as JSON"),
):
    """Scan a codebase without generating docs."""
    load_dotenv()
    from core.scanner import scan_codebase

    result = scan_codebase(path)

    if json_output:
        typer.echo(json.dumps(result.to_dict(), indent=2))
    else:
        typer.echo(f"Root: {result.root}")
        typer.echo(f"Files: {result.total_files}")
        typer.echo(f"Lines: {result.total_lines}")
        typer.echo(f"Size: {result.total_bytes:,} bytes")
        typer.echo(f"Languages: {result.languages}")
        typer.echo(f"Config files: {len(result.config_files)}")
        typer.echo(f"Doc files: {len(result.doc_files)}")


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of runs to show"),
):
    """Show recent generation run history."""
    load_dotenv()
    asyncio.run(_history(limit))


async def _history(limit: int):
    from db.cache import init_db, get_run_history
    await init_db()
    runs = await get_run_history(limit)

    if not runs:
        typer.echo("No runs found.")
        return

    for run in runs:
        typer.echo(f"\n--- Run #{run['id']} ---")
        typer.echo(f"  Time: {run['created_at']}")
        typer.echo(f"  Root: {run['root_path']}")
        typer.echo(f"  Files: {run['total_files']}")
        typer.echo(f"  Tokens: {run['total_tokens']}")
        typer.echo(f"  Score: {run['quality_score']}/100")
        typer.echo(f"  Site: {run['site_dir']}")


@app.command()
def proof(
    run_id: int = typer.Argument(..., help="Run ID to generate proof for"),
    output_dir: str = typer.Option("proofs", "--output", "-o"),
):
    """Generate proof/evidence for a specific run."""
    load_dotenv()
    asyncio.run(_proof(run_id, output_dir))


async def _proof(run_id: int, output_dir: str):
    from db.cache import init_db, get_run_history
    await init_db()
    runs = await get_run_history(100)
    run = None
    for r in runs:
        if r["id"] == run_id:
            run = r
            break

    if not run:
        typer.echo(f"Run #{run_id} not found.")
        raise typer.Exit(1)

    os.makedirs(output_dir, exist_ok=True)

    # Write proof JSON
    proof_path = os.path.join(output_dir, f"run_{run_id}_proof.json")
    proof_data = json.loads(run["proof_data"]) if run["proof_data"] else {}

    full_proof = {
        "run_id": run_id,
        "created_at": run["created_at"],
        "root_path": run["root_path"],
        "total_files": run["total_files"],
        "quality_score": run["quality_score"],
        "site_dir": run["site_dir"],
        "proof": proof_data,
        "token_usage": proof_data.get("usage", {}),
    }

    with open(proof_path, "w") as f:
        json.dump(full_proof, f, indent=2)

    typer.echo(f"Proof written to {proof_path}")

    # Write token usage stats
    stats_path = os.path.join(output_dir, f"run_{run_id}_stats.md")
    usage = proof_data.get("usage", {})
    with open(stats_path, "w") as f:
        f.write(f"# DocsForge Run #{run_id} — Token Usage Stats\n\n")
        f.write(f"- **Date:** {run['created_at']}\n")
        f.write(f"- **Root:** {run['root_path']}\n")
        f.write(f"- **Files scanned:** {run['total_files']}\n")
        f.write(f"- **Quality score:** {run['quality_score']}/100\n")
        f.write(f"- **Total tokens:** {usage.get('total_tokens', 'N/A')}\n")
        f.write(f"- **Prompt tokens:** {usage.get('total_prompt_tokens', 'N/A')}\n")
        f.write(f"- **Completion tokens:** {usage.get('total_completion_tokens', 'N/A')}\n")
        f.write(f"- **API calls:** {usage.get('num_calls', 'N/A')}\n")
        f.write(f"- **Total duration:** {usage.get('total_duration_ms', 0) / 1000:.1f}s\n\n")

        calls = usage.get("calls", [])
        if calls:
            f.write("## Per-Call Breakdown\n\n")
            for i, call in enumerate(calls, 1):
                f.write(f"{i}. **{call.get('model', 'unknown')}**: "
                       f"{call.get('total_tokens', 0)} tokens "
                       f"({call.get('duration_ms', 0) / 1000:.1f}s)\n")

    typer.echo(f"Stats written to {stats_path}")


if __name__ == "__main__":
    app()
