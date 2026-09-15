"""CLI tests for developer sandbox commands."""

from __future__ import annotations

from typer.testing import CliRunner

from agentforge.cli.main import app

runner = CliRunner()


def test_cli_sandbox_help():
    result = runner.invoke(app, ["sandbox", "--help"])
    assert result.exit_code == 0
    assert "up" in result.stdout
    assert "down" in result.stdout
    assert "status" in result.stdout
    assert "watch" in result.stdout
    assert "open" in result.stdout
    assert "pause" in result.stdout
    assert "resume" in result.stdout


def test_cli_sandbox_up_dry_run_aws():
    result = runner.invoke(
        app,
        ["sandbox", "up", "--csp", "aws", "--name", "alice", "--ttl", "6h", "--dry-run"],
    )
    assert result.exit_code == 0
    assert "sandbox-alice" in result.stdout
    assert "AWS" in result.stdout
    assert "Dry-run completed" in result.stdout
    assert "alb" in result.stdout


def test_cli_sandbox_up_dry_run_gcp():
    result = runner.invoke(
        app,
        ["sandbox", "up", "--csp", "gcp", "--name", "bob", "--dry-run"],
    )
    assert result.exit_code == 0
    assert "sandbox-bob" in result.stdout
    assert "GCP" in result.stdout
    assert "gce" in result.stdout


def test_cli_sandbox_up_dry_run_azure():
    result = runner.invoke(
        app,
        ["sandbox", "up", "--csp", "azure", "--name", "carol", "--dry-run"],
    )
    assert result.exit_code == 0
    assert "sandbox-carol" in result.stdout
    assert "AZURE" in result.stdout


def test_cli_sandbox_pause_resume():
    res_pause = runner.invoke(app, ["sandbox", "pause", "--name", "test-user"])
    assert res_pause.exit_code == 0
    assert "Paused" in res_pause.stdout or "paused" in res_pause.stdout

    res_resume = runner.invoke(app, ["sandbox", "resume", "--name", "test-user"])
    assert res_resume.exit_code == 0
    assert "Resumed" in res_resume.stdout or "resumed" in res_resume.stdout


def test_cli_sandbox_down_abort():
    # When prompt confirmation is not given
    res = runner.invoke(app, ["sandbox", "down", "--name", "test-user"], input="n\n")
    assert res.exit_code == 0
    assert "Aborted" in res.stdout


def test_cli_sandbox_down_force():
    res = runner.invoke(app, ["sandbox", "down", "--name", "test-user", "--force"])
    assert res.exit_code == 0
    assert "sandbox-test-user" in res.stdout


def test_cli_sandbox_up_invalid_csp():
    res = runner.invoke(app, ["sandbox", "up", "--csp", "invalid-csp", "--dry-run"])
    assert res.exit_code == 1
    assert "Unsupported CSP 'invalid-csp'" in res.stdout


def test_cli_sandbox_open():
    from unittest.mock import patch
    with patch("webbrowser.open") as mock_open:
        res = runner.invoke(app, ["sandbox", "open", "--name", "bob", "--domain", "mytest.com"])
        assert res.exit_code == 0
        assert "https://bob.mytest.com" in res.stdout
        mock_open.assert_called_once_with("https://bob.mytest.com")


def test_cli_sandbox_status():
    res = runner.invoke(app, ["sandbox", "status", "--name", "alice"])
    assert res.exit_code == 0
    assert "sandbox-alice" in res.stdout
