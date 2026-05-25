"""SQLite incremental cache — avoid re-analyzing unchanged files."""

import hashlib
import os
from pathlib import Path
import sqlite3
from datetime import datetime, timezone


def get_cache_path() -> Path:
    return Path(os.environ.get("DOCSFORGE_CACHE_DB", ".docsforge/cache.db"))


def init_cache(path: Path | None = None) -> sqlite3.Connection:
    cache_path = path or get_cache_path()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(cache_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS file_hashes (
            path TEXT PRIMARY KEY,
            hash TEXT NOT NULL,
            last_seen TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS builds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repo_name TEXT NOT NULL,
            output_dir TEXT NOT NULL,
            tokens_used INTEGER DEFAULT 0,
            pages_generated INTEGER DEFAULT 0,
            errors INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    return conn


def hash_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def changed_files(conn: sqlite3.Connection, files: list[tuple[str, str]]) -> list[str]:
    """Return list of relative paths whose hashes differ from the cache.

    `files` is a list of (rel_path, abs_path).
    """
    out = []
    cur = conn.cursor()
    now = datetime.now(timezone.utc).isoformat()
    for rel, abs_p in files:
        try:
            new_hash = hash_file(abs_p)
        except OSError:
            continue
        cur.execute("SELECT hash FROM file_hashes WHERE path = ?", (rel,))
        row = cur.fetchone()
        if row is None or row[0] != new_hash:
            out.append(rel)
        cur.execute(
            "INSERT OR REPLACE INTO file_hashes(path, hash, last_seen) VALUES (?, ?, ?)",
            (rel, new_hash, now),
        )
    conn.commit()
    return out


def record_build(conn: sqlite3.Connection, repo_name: str, output_dir: str,
                 tokens: int, pages: int, errors: int) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO builds (repo_name, output_dir, tokens_used, pages_generated, errors, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (repo_name, output_dir, tokens, pages, errors, now),
    )
    conn.commit()
    return cur.lastrowid or 0
