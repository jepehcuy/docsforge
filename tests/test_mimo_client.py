"""Tests for DocsForge mimo_client module."""

import json
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.mimo_client import ClientStats, UsageStats


class TestClientStats:
    def test_empty(self):
        stats = ClientStats()
        assert stats.total_tokens == 0
        assert stats.total_prompt_tokens == 0
        assert len(stats.calls) == 0

    def test_with_calls(self):
        stats = ClientStats()
        stats.calls.append(UsageStats(
            prompt_tokens=100, completion_tokens=50,
            total_tokens=150, model="test", duration_ms=100,
        ))
        stats.calls.append(UsageStats(
            prompt_tokens=200, completion_tokens=100,
            total_tokens=300, model="test", duration_ms=200,
        ))
        assert stats.total_tokens == 450
        assert stats.total_prompt_tokens == 300
        assert stats.total_completion_tokens == 150
        assert stats.total_duration_ms == 300

    def test_to_dict(self):
        stats = ClientStats()
        stats.calls.append(UsageStats(
            prompt_tokens=100, completion_tokens=50,
            total_tokens=150, model="test", duration_ms=100,
        ))
        d = stats.to_dict()
        assert "total_tokens" in d
        assert "calls" in d
        assert len(d["calls"]) == 1
        assert d["calls"][0]["model"] == "test"


class TestUsageStats:
    def test_defaults(self):
        s = UsageStats()
        assert s.prompt_tokens == 0
        assert s.model == ""
