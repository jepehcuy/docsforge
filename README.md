# DocsForge

Multi-agent documentation generation system. Scans a codebase, runs 5 specialist AI agents in parallel, synthesizes outputs into a complete mkdocs site.

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API endpoint

# Generate docs
python cli.py generate /path/to/your/project

# Serve locally
cd /path/to/your/project/site-docs
mkdocs serve
```

## Architecture

```
docsforge/
├── core/
│   ├── scanner.py        # File tree + language detection + AST
│   ├── agent.py          # Base agent class
│   ├── mimo_client.py    # Async OpenAI client with SSE adapter
│   ├── orchestrator.py   # Parallel agent runner
│   └── synthesizer.py    # Merge outputs into mkdocs
├── agents/
│   ├── architecture_agent.py   # Structure + design patterns
│   ├── api_agent.py            # Public APIs + interfaces
│   ├── examples_agent.py       # Usage examples + snippets
│   ├── changelog_agent.py      # Versioning + change history
│   └── config_agent.py         # Configuration + setup docs
├── eval/
│   └── scorer.py         # LLM-as-judge quality evaluation
├── db/
│   └── cache.py          # SQLite incremental cache
├── cli.py                # Typer CLI entry point
└── proofs/               # Run evidence + token stats
```

## CLI Commands

```bash
# Generate full documentation
python cli.py generate .

# Scan only (no LLM calls)
python cli.py scan . --json

# View run history
python cli.py history

# Generate proof for a specific run
python cli.py proof 1

# Skip specific agents
python cli.py generate . --skip-agents ChangelogAgent,ConfigAgent

# Full rebuild (ignore cache)
python cli.py generate . --full
```

## 5 Specialist Agents

| Agent | Focus | Output |
|-------|-------|--------|
| ArchitectureAgent | Project structure, design patterns, module deps | Architecture docs |
| APIAgent | Public functions, classes, interfaces | API reference |
| ExamplesAgent | Usage patterns, code snippets | Example cookbook |
| ChangelogAgent | Versioning, change history, migrations | Changelog docs |
| ConfigAgent | Config files, env vars, setup | Setup guide |

## Token Economics

- Small repo (<50 files): ~200K tokens total
- Medium repo (50-500 files): ~500K tokens
- Large monorepo (500+ files): ~1.5M tokens

## Incremental Cache

DocsForge caches file hashes and agent outputs in SQLite. On subsequent runs, only changed files trigger agent re-runs. Use `--full` to force a complete rebuild.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | API endpoint |
| `OPENAI_API_KEY` | - | API key |
| `MIMO_MODEL` | `kr/claude-sonnet-4.5` | Model for all agents |
| `DOCSFORGE_DB` | `~/.docsforge/cache.db` | Cache database path |

## License

MIT
