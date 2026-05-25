# Changelog

All notable changes to httpx will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Versioning

- **Source**: `httpx/__version__.py`
- **Scheme**: Semver (0.x series)
- **Sync**: `scripts/sync-version` keeps version in sync across `pyproject.toml` and docs

## Current Version

**0.23.0** (from `pyproject.toml`)

## Release Notes

<!-- Extract from CHANGELOG.md -->
- Check `CHANGELOG.md` for detailed per-version changes
- Run `git log --oneline -20` for recent commits
- Migration notes available per minor version (breaking changes in 0.x)

## Version History Template

```markdown
### [Unreleased]

### [X.Y.Z] - YYYY-MM-DD
#### Added
#### Changed
#### Fixed
#### Removed
#### Deprecated
#### Security
```

## Key Files

| File | Purpose |
|---|---|
| `httpx/__version__.py` | Single source of version |
| `scripts/sync-version` | Version propagation script |
| `CHANGELOG.md` | Project changelog |
| `pyproject.toml` | Build metadata (version synced) |

## Breaking Changes

httpx is pre-1.0 (0.x). Breaking changes expected between minor versions per semver.
