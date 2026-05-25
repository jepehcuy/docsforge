"""DocsForge — FastAPI web server with SSE progress streaming."""

import asyncio
import json
import os
import shutil
import tempfile
import time
import uuid
from dataclasses import asdict
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Ensure project root is importable
import sys

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from core.scanner import scan_codebase
from core.mimo_client import get_mimo_client, MIMO_MODEL, ClientStats
from core.agent import BaseAgent, AgentOutput
from core.synthesizer import Synthesizer
from eval.scorer import DocScorer
from agents.architecture_agent import ArchitectureAgent
from agents.api_agent import APIAgent
from agents.examples_agent import ExamplesAgent
from agents.changelog_agent import ChangelogAgent
from agents.config_agent import ConfigAgent
from db import cache as db_cache

app = FastAPI(title="DocsForge", docs_url=None, redoc_url=None)

STATIC_DIR = Path(__file__).parent / "static"
RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"

# In-memory store for run results (markdown pages, synthesis data)
_run_cache: dict[str, dict] = {}

AGENT_ORDER = [
    "ArchitectureAgent",
    "APIAgent",
    "ExamplesAgent",
    "ChangelogAgent",
    "ConfigAgent",
]

AGENT_MAP = {
    "ArchitectureAgent": ArchitectureAgent,
    "APIAgent": APIAgent,
    "ExamplesAgent": ExamplesAgent,
    "ChangelogAgent": ChangelogAgent,
    "ConfigAgent": ConfigAgent,
}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "model": MIMO_MODEL,
        "agent_count": len(AGENT_ORDER),
    }


@app.get("/api/history")
async def history():
    try:
        rows = await db_cache.get_run_history(limit=20)
        return {"runs": rows}
    except Exception as e:
        return {"runs": [], "error": str(e)}


@app.get("/api/docs/{run_id}")
async def get_docs(run_id: int):
    """Return generated docs pages for a run."""
    entry = _run_cache.get(str(run_id))
    if entry:
        return entry

    # Fallback: try loading from disk
    run_dir = RUNS_DIR / str(run_id)
    docs_dir = run_dir / "docs"
    if docs_dir.exists():
        pages = {}
        for f in docs_dir.iterdir():
            if f.suffix == ".md":
                pages[f.name] = f.read_text()
        result = {"run_id": run_id, "pages": pages}
        _run_cache[str(run_id)] = result
        return result

    return JSONResponse({"error": "Run not found"}, status_code=404)


@app.post("/api/generate")
async def generate(request: Request):
    """SSE endpoint — run full pipeline, stream progress events."""
    body = await request.json()
    path = body.get("path", "").strip()
    code = body.get("code", "").strip()
    language = body.get("language", "python").strip()

    if not path and not code:
        return JSONResponse({"error": "Provide 'path' or 'code'"}, status_code=400)

    return EventSourceResponse(_run_pipeline(path, code, language))


async def _run_pipeline(path: str, code: str, language: str):
    """Generator that yields SSE events throughout the pipeline."""
    temp_dir = None

    try:
        # Resolve target path
        if code:
            temp_dir = tempfile.mkdtemp(prefix="docsforge_")
            ext = _lang_to_ext(language)
            code_file = os.path.join(temp_dir, f"input{ext}")
            with open(code_file, "w") as f:
                f.write(code)
            target = temp_dir
        else:
            target = os.path.abspath(path)
            if not os.path.isdir(target):
                yield {"event": "error", "data": json.dumps({"error": f"Not a directory: {target}"})}
                return

        # --- Stage: scanning ---
        yield {"event": "progress", "data": json.dumps({"type": "progress", "stage": "scanning"})}
        t0 = time.time()
        scan_result = scan_codebase(target)
        scan_duration = time.time() - t0
        yield {
            "event": "progress",
            "data": json.dumps({
                "type": "scan_complete",
                "total_files": scan_result.total_files,
                "total_lines": scan_result.total_lines,
                "languages": scan_result.languages,
                "duration": round(scan_duration, 2),
            }),
        }

        # --- Stage: agents ---
        yield {"event": "progress", "data": json.dumps({"type": "progress", "stage": "agents"})}
        client = get_mimo_client()
        stats = ClientStats()
        agent_outputs: dict[str, AgentOutput] = {}

        # Run agents concurrently, emit event as each completes
        async def run_one(name: str):
            agent_cls = AGENT_MAP[name]
            agent = agent_cls(client, MIMO_MODEL, stats)
            t = time.time()
            output = await agent.run(scan_result)
            dur = time.time() - t
            return name, output, dur

        tasks = {asyncio.create_task(run_one(n)): n for n in AGENT_ORDER}
        for coro in asyncio.as_completed(tasks):
            name, output, dur = await coro
            agent_outputs[name] = output
            yield {
                "event": "agent_complete",
                "data": json.dumps({
                    "type": "agent_complete",
                    "agent": name,
                    "duration": round(dur, 2),
                    "status": "done",
                    "confidence": output.confidence,
                    "sections": list(output.sections.keys()),
                }),
            }

        # --- Stage: synthesizing ---
        yield {"event": "progress", "data": json.dumps({"type": "progress", "stage": "synthesizing"})}
        synthesizer = Synthesizer(client, MIMO_MODEL, stats)
        synthesis = await synthesizer.synthesize(scan_result, agent_outputs)
        site_dir = synthesizer.write_site(synthesis)

        # --- Stage: evaluating ---
        yield {"event": "progress", "data": json.dumps({"type": "progress", "stage": "evaluating"})}
        scorer = DocScorer(client, MIMO_MODEL, stats)
        quality = await scorer.evaluate(scan_result, agent_outputs, synthesis.pages)

        # --- Save to cache ---
        total_tokens = stats.total_tokens
        run_id = await db_cache.save_run(
            root_path=target,
            total_files=scan_result.total_files,
            total_tokens=total_tokens,
            agents_run=AGENT_ORDER,
            quality_score=quality.overall,
            site_dir=site_dir,
        )

        # Store pages in memory
        _run_cache[str(run_id)] = {
            "run_id": run_id,
            "pages": synthesis.pages,
            "nav": synthesis.nav,
            "mkdocs_config": synthesis.mkdocs_config,
        }

        # Also persist to runs directory
        run_dir = RUNS_DIR / str(run_id)
        docs_dir = run_dir / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        for fname, content in synthesis.pages.items():
            (docs_dir / fname).write_text(content)

        # --- Complete ---
        result = {
            "type": "complete",
            "run_id": run_id,
            "scan": {
                "root": scan_result.root,
                "total_files": scan_result.total_files,
                "total_lines": scan_result.total_lines,
                "languages": scan_result.languages,
            },
            "quality": {
                "overall": quality.overall,
                "completeness": quality.completeness,
                "accuracy": quality.accuracy,
                "clarity": quality.clarity,
                "structure": quality.structure,
                "usefulness": quality.usefulness,
                "reasoning": quality.judge_reasoning,
                "recommendations": quality.recommendations,
            },
            "tokens": stats.to_dict(),
            "pages": list(synthesis.pages.keys()),
            "agents": {
                name: {
                    "confidence": out.confidence,
                    "sections": list(out.sections.keys()),
                    "findings_count": len(out.findings),
                }
                for name, out in agent_outputs.items()
            },
        }
        yield {"event": "complete", "data": json.dumps(result)}

    except Exception as e:
        yield {"event": "error", "data": json.dumps({"type": "error", "error": str(e)})}
    finally:
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Static files (after routes so / takes priority)
# ---------------------------------------------------------------------------
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lang_to_ext(language: str) -> str:
    return {
        "python": ".py", "javascript": ".js", "typescript": ".ts",
        "go": ".go", "rust": ".rs", "java": ".java", "ruby": ".rb",
        "php": ".php", "c": ".c", "cpp": ".cpp", "csharp": ".cs",
        "swift": ".swift", "kotlin": ".kt", "shell": ".sh",
    }.get(language, ".txt")


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def startup():
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    await db_cache.init_db()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web.main:app", host="0.0.0.0", port=8090, reload=True)
