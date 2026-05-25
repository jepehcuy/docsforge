"""SQLite incremental cache for DocsForge.

Caches scan results and agent outputs by content hash.
Enables incremental regeneration — only re-run agents for
files that changed since last run.
"""

import aiosqlite
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = os.environ.get("DOCSFORGE_DB", str(Path.home() / ".docsforge" / "cache.db"))


async def get_db() -> aiosqlite.Connection:
    """Get database connection."""
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    await db.execute("PRAGMA journal_mode=WAL")
    return db


async def init_db():
    """Initialize cache database tables."""
    db = await get_db()
    try:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS file_hashes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                scan_result_hash TEXT,
                agent_output TEXT,
                updated_at TEXT NOT NULL,
                UNIQUE(file_path)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS run_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                root_path TEXT NOT NULL,
                total_files INTEGER,
                total_tokens INTEGER,
                agents_run TEXT,
                quality_score INTEGER,
                site_dir TEXT,
                proof_data TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS file_content_cache (
                file_path TEXT PRIMARY KEY,
                content_hash TEXT NOT NULL,
                structural_info TEXT,
                cached_at TEXT NOT NULL
            )
        """)
        await db.commit()
    finally:
        await db.close()


def hash_content(content: str) -> str:
    """Compute SHA-256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


async def get_file_hash(file_path: str) -> str | None:
    """Get cached content hash for a file."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT content_hash FROM file_content_cache WHERE file_path = ?",
            (file_path,),
        )
        row = await cursor.fetchone()
        return row[0] if row else None
    finally:
        await db.close()


async def set_file_hash(file_path: str, content_hash: str, structural_info: dict | None = None):
    """Update cached content hash for a file."""
    db = await get_db()
    try:
        await db.execute(
            """INSERT OR REPLACE INTO file_content_cache
               (file_path, content_hash, structural_info, cached_at)
               VALUES (?, ?, ?, ?)""",
            (
                file_path,
                content_hash,
                json.dumps(structural_info) if structural_info else None,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await db.commit()
    finally:
        await db.close()


async def get_agent_output(file_paths_hash: str, agent_name: str) -> dict | None:
    """Get cached agent output for a set of files."""
    db = await get_db()
    try:
        key = f"{file_paths_hash}:{agent_name}"
        cursor = await db.execute(
            "SELECT agent_output FROM file_hashes WHERE file_path = ?",
            (key,),
        )
        row = await cursor.fetchone()
        if row and row[0]:
            return json.loads(row[0])
        return None
    finally:
        await db.close()


async def set_agent_output(file_paths_hash: str, agent_name: str, output: dict):
    """Cache agent output for a set of files."""
    db = await get_db()
    try:
        key = f"{file_paths_hash}:{agent_name}"
        await db.execute(
            """INSERT OR REPLACE INTO file_hashes
               (file_path, content_hash, agent_output, updated_at)
               VALUES (?, ?, ?, ?)""",
            (
                key,
                file_paths_hash,
                json.dumps(output),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await db.commit()
    finally:
        await db.close()


async def save_run(
    root_path: str,
    total_files: int,
    total_tokens: int,
    agents_run: list[str],
    quality_score: int,
    site_dir: str,
    proof_data: dict | None = None,
) -> int:
    """Save a generation run to history."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO run_history
               (created_at, root_path, total_files, total_tokens,
                agents_run, quality_score, site_dir, proof_data)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                root_path,
                total_files,
                total_tokens,
                json.dumps(agents_run),
                quality_score,
                site_dir,
                json.dumps(proof_data) if proof_data else None,
            ),
        )
        await db.commit()
        return cursor.lastrowid or 0
    finally:
        await db.close()


async def get_run_history(limit: int = 10) -> list[dict]:
    """Get recent generation runs."""
    db = await get_db()
    try:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM run_history ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()


async def compute_files_hash(file_paths: list[str]) -> str:
    """Compute a combined hash for a set of file paths + their current hashes."""
    db = await get_db()
    try:
        parts = []
        for fp in sorted(file_paths):
            cursor = await db.execute(
                "SELECT content_hash FROM file_content_cache WHERE file_path = ?",
                (fp,),
            )
            row = await cursor.fetchone()
            h = row[0] if row else "missing"
            parts.append(f"{fp}:{h}")
        return hash_content("\n".join(parts))
    finally:
        await db.close()


async def get_changed_files(file_paths: list[str]) -> list[str]:
    """Return list of files that changed since last scan."""
    db = await get_db()
    changed = []
    try:
        for fp in file_paths:
            if os.path.exists(fp):
                with open(fp, "r", encoding="utf-8", errors="replace") as f:
                    current_hash = hash_content(f.read())
                cursor = await db.execute(
                    "SELECT content_hash FROM file_content_cache WHERE file_path = ?",
                    (fp,),
                )
                row = await cursor.fetchone()
                if not row or row[0] != current_hash:
                    changed.append(fp)
    finally:
        await db.close()
    return changed
