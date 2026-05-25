"""Tests for DocsForge cache module."""

import asyncio
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def temp_db(monkeypatch):
    """Set up a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_cache.db")
        monkeypatch.setattr("db.cache.DB_PATH", db_path)
        yield db_path


@pytest.fixture
def init(temp_db):
    """Initialize the test database."""
    from db.cache import init_db
    asyncio.get_event_loop().run_until_complete(init_db())


class TestCacheInit:
    def test_init_creates_db(self, temp_db):
        from db.cache import init_db
        asyncio.get_event_loop().run_until_complete(init_db())
        assert os.path.exists(temp_db)


class TestFileHash:
    def test_set_and_get(self, temp_db, init):
        from db.cache import set_file_hash, get_file_hash

        async def run():
            await set_file_hash("test.py", "abc123")
            result = await get_file_hash("test.py")
            assert result == "abc123"

        asyncio.get_event_loop().run_until_complete(run())

    def test_get_missing(self, temp_db, init):
        from db.cache import get_file_hash

        async def run():
            result = await get_file_hash("nonexistent.py")
            assert result is None

        asyncio.get_event_loop().run_until_complete(run())

    def test_overwrite(self, temp_db, init):
        from db.cache import set_file_hash, get_file_hash

        async def run():
            await set_file_hash("test.py", "old_hash")
            await set_file_hash("test.py", "new_hash")
            result = await get_file_hash("test.py")
            assert result == "new_hash"

        asyncio.get_event_loop().run_until_complete(run())


class TestAgentOutput:
    def test_set_and_get(self, temp_db, init):
        from db.cache import set_agent_output, get_agent_output

        async def run():
            output = {"sections": {"Overview": "Test content"}}
            await set_agent_output("hash123", "ArchitectureAgent", output)
            result = await get_agent_output("hash123", "ArchitectureAgent")
            assert result == output

        asyncio.get_event_loop().run_until_complete(run())


class TestRunHistory:
    def test_save_and_get(self, temp_db, init):
        from db.cache import save_run, get_run_history

        async def run():
            run_id = await save_run(
                root_path="/test",
                total_files=10,
                total_tokens=50000,
                agents_run=["Agent1", "Agent2"],
                quality_score=85,
                site_dir="/test/site-docs",
            )
            assert run_id > 0
            history = await get_run_history()
            assert len(history) >= 1
            assert history[0]["total_files"] == 10

        asyncio.get_event_loop().run_until_complete(run())


class TestHashContent:
    def test_hash_deterministic(self):
        from db.cache import hash_content
        h1 = hash_content("hello world")
        h2 = hash_content("hello world")
        assert h1 == h2

    def test_hash_different(self):
        from db.cache import hash_content
        h1 = hash_content("hello")
        h2 = hash_content("world")
        assert h1 != h2
