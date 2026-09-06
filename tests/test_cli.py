"""Tests for AgentForge Typer CLI commands."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typer.testing import CliRunner

from agentforge.cli.main import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "agentforge" in result.stdout.lower()
    assert "new" in result.stdout
    assert "dev" in result.stdout
    assert "build" in result.stdout
    assert "deploy" in result.stdout


def test_cli_new_help():
    result = runner.invoke(app, ["new", "--help"])
    assert result.exit_code == 0
    assert "--framework" in result.stdout
    assert "--frontend" in result.stdout
    assert "--path" in result.stdout


def test_cli_new_scaffold_success():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = runner.invoke(
            app,
            ["new", "sample-agent", "--path", tmpdir, "--framework", "langgraph", "--frontend", "react"],
        )
        assert result.exit_code == 0
        assert "Project successfully generated" in result.stdout

        target_dir = Path(tmpdir) / "sample-agent"
        assert target_dir.exists()
        assert (target_dir / "backend" / "src" / "core" / "adapter.py").exists()
        assert (target_dir / "frontend" / "admin.html").exists()
        assert (target_dir / "docker-compose.yml").exists()


def test_cli_new_invalid_name():
    result = runner.invoke(app, ["new", "invalid name with spaces"])
    assert result.exit_code != 0
    assert "Validation Error" in result.output or "Invalid project name" in result.output
