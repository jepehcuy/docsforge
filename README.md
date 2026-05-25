# DocsForge

**Multi-agent documentation generator. Turn any codebase into a production-ready mkdocs site in minutes.**

DocsForge runs 5 specialist AI agents in parallel against a codebase — analyzing structure, public APIs, usage patterns, change history, and configuration — then synthesizes everything into a deployable mkdocs site with full navigation, code examples, and architecture diagrams.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![mkdocs](https://img.shields.io/badge/mkdocs-material-526CFE.svg)](https://squidfunk.github.io/mkdocs-material/)

## How It Works

```
Your Codebase (path or repo URL)
    │
    ▼
┌─────────────────────────────────────────────┐
│        Scanner (file tree + AST)            │
│  → languages, modules, dependencies         │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│            Agent Orchestrator               │
│                                             │
│  ┌──────────────┐  ┌──────────────┐         │
│  │ Architecture │  │     API      │         │
│  │    Agent     │  │    Agent     │         │
│  └──────┬───────┘  └──────┬───────┘         │
│  ┌──────┴───────┐  ┌──────┴───────┐         │
│  │   Examples   │  │  Changelog   │ parallel│
│  │    Agent     │  │    Agent     │         │
│  └──────┬───────┘  └──────┬───────┘         │
│  ┌──────┴───────┐         │                 │
│  │    Config    │─────────┘                 │
│  │    Agent     │                           │
│  └──────────────┘                           │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
        ┌──────────────────┐
        │    Synthesis      │
        │    Compiler       │
        └────────┬─────────┘
                 │
                 ▼
        ┌──────────────────┐
        │   Quality Judge   │
        │  (5 dimensions)   │
        └────────┬─────────┘
                 │
                 ▼
       mkdocs site (deployable)
       + scorecard + token stats
```

## What You Get

Each run produces:

- **`docs/`** — full mkdocs site (architecture, API reference, quickstart, examples, changelog, setup)
- **`mkdocs.yml`** — preconfigured navigation + theme
- **Quality scorecard** — completeness, accuracy, clarity, structure, usefulness (0-100 each)
- **Token usage breakdown** — per-agent costs + total run cost
- **SQLite cache** — incremental rebuilds skip unchanged files

## Agents

| Agent | What It Does |
|-------|-------------|
| **ArchitectureAgent** | Reads module structure, infers design patterns, generates Mermaid diagrams + system overview |
| **APIAgent** | Extracts public functions/classes/endpoints, fills in missing docstrings, produces reference pages |
| **ExamplesAgent** | Finds existing usage in tests/examples, writes runnable snippets for undocumented features |
| **ChangelogAgent** | Reads `git log`, categorizes commits (feat/fix/docs), produces release notes |
| **ConfigAgent** | Finds `.env`, `config.yaml`, `pyproject.toml` etc., produces setup + deployment guide |

Each agent runs concurrently via `asyncio.gather()` — total runtime is bounded by the slowest agent, not the sum.

## Quick Start

```bash
# Clone
git clone https://github.com/jepehcuy/docsforge.git
cd docsforge

# Install
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API key and endpoint

# Generate docs (CLI)
python cli.py generate /path/to/your/project

# Or launch the web UI
uvicorn web.main:app --port 8090
# Open http://localhost:8090
```

## CLI Reference

```bash
# Full documentation generation
python cli.py generate <path>

# Scan only (no LLM calls — fast preview)
python cli.py scan <path> --json

# Run history with quality scores
python cli.py history

# Export proof bundle for a specific run
python cli.py proof <run_id>

# Skip specific agents
python cli.py generate <path> --skip-agents ChangelogAgent,ConfigAgent

# Force full rebuild (ignore cache)
python cli.py generate <path> --full
```

## Web API

### Generate Documentation

```bash
curl -X POST http://localhost:8090/api/generate \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/project"}' \
  --no-buffer
```

Returns Server-Sent Events streaming agent progress:

```
data: {"type": "progress", "stage": "scanning"}
data: {"type": "agent_complete", "agent": "ArchitectureAgent", "duration": 12.3}
data: {"type": "agent_complete", "agent": "APIAgent", "duration": 14.8}
...
data: {"type": "complete", "result": {...}}
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/generate` | Run full pipeline (SSE stream) |
| `GET`  | `/api/history` | Past runs with scores |
| `GET`  | `/api/health` | Service + model status |
| `GET`  | `/api/docs/{run_id}` | Serve generated docs |

## Real Run Example

Tested on **httpx** (encode/httpx — popular Python HTTP client):

```
Target:        https://github.com/encode/httpx
Files scanned: 116
Lines:         26,868
Languages:     Python (60), Markdown (26), TOML, YAML, HTML, CSS

Pipeline:
  Scanner:        0.2s
  5 Agents:      82.1s (parallel)
  Synthesis:    122.5s
  Eval:           9.2s
  ─────────────────
  Total:        214.1s

Quality Score: 72/100
  Completeness: 75
  Accuracy:     80
  Clarity:      78
  Structure:    70
  Usefulness:   68

Token Usage:   158,501 (7 LLM calls)
Output:        3 doc pages + mkdocs.yml
```

See `proofs/` directory for the full run JSON, screenshots, and token breakdown.

## Token Economics

| Codebase Size | Tokens Per Run | Use Case |
|--------------|----------------|----------|
| Small (<50 files) | ~200K | Solo project, quick docs |
| Medium (50-500 files) | ~500K | Team library, OSS project |
| Large (500+ files) | ~1.5-2M | Monorepo, framework |
| CI/CD rebuild | ~10-20M/month | Auto-update docs on every merge |
| Documentation agency | ~100M/month | 100+ client repos |

## Incremental Cache

DocsForge caches file hashes and agent outputs in SQLite. On subsequent runs, only changed files trigger agent re-runs — turning a 200K-token full run into a 20K-token incremental update.

```bash
# First run: full generation
python cli.py generate .          # 200K tokens

# Edit one file, re-run
python cli.py generate .          # ~20K tokens (cached unchanged files)

# Force full rebuild
python cli.py generate . --full   # 200K tokens
```

## Configuration

Set via environment variables or `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | API key for your LLM provider |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible endpoint |
| `DOCSFORGE_MODEL` | `kr/claude-sonnet-4.5` | Model for all agents |
| `DOCSFORGE_CACHE_DB` | `.docsforge/cache.db` | Cache database path |

DocsForge works with any OpenAI-compatible API — OpenAI, Anthropic via proxy, MiMo, Claude, local models (Ollama, vLLM), or any compatible provider.

## Tech Stack

- **Backend:** FastAPI + AsyncOpenAI + asyncio
- **CLI:** Typer
- **LLM:** Any OpenAI-compatible API
- **Storage:** SQLite (WAL mode) for cache + history
- **Output:** mkdocs + mkdocs-material
- **Frontend:** Vanilla JS + marked.js (zero build step)
- **Code parsing:** Python `ast` + tree-sitter for multi-language support

## Project Structure

```
docsforge/
├── core/                  # Scanner, base agent, orchestrator, synthesizer, LLM client
├── agents/                # 5 specialist agents
│   ├── architecture_agent.py
│   ├── api_agent.py
│   ├── examples_agent.py
│   ├── changelog_agent.py
│   └── config_agent.py
├── eval/                  # LLM-as-judge quality scorer
├── db/                    # SQLite incremental cache
├── web/                   # FastAPI app + frontend
│   ├── main.py
│   └── static/
├── tests/                 # 45 tests (pytest)
├── proofs/                # Run evidence + screenshots
├── cli.py                 # Typer CLI entry
├── requirements.txt
└── README.md
```

## Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=core --cov=agents --cov=eval --cov=db
```

45 tests covering scanner, cache, MiMo client, and CLI integration.

## License

MIT — see [LICENSE](LICENSE) for details.
