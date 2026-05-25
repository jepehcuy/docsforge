"""Tests for DocsForge CLI (basic import checks)."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_cli_import():
    """Verify CLI module can be imported."""
    import cli
    assert hasattr(cli, "app")


def test_scan_result_to_dict():
    """Verify ScanResult serialization."""
    from core.scanner import ScanResult
    result = ScanResult(root="/test")
    d = result.to_dict()
    assert d["total_files"] == 0
    assert d["files"] == []


def test_agent_output_dataclass():
    """Verify AgentOutput creation."""
    from core.agent import AgentOutput
    output = AgentOutput(agent_name="TestAgent")
    assert output.agent_name == "TestAgent"
    assert output.sections == {}
    assert output.confidence == 0.5
