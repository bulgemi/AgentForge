"""Tests for sandbox live file watcher and sync engine."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from agentforge.sandbox.watcher import FastFileSyncer


def test_fast_file_syncer_init(tmp_path: Path):
    syncer = FastFileSyncer(
        namespace="sandbox-test",
        local_dir=tmp_path,
        remote_dest="/app/src",
        pod_component="backend",
    )
    assert syncer.namespace == "sandbox-test"
    assert syncer.local_dir == tmp_path.resolve()
    assert syncer.remote_dest == "/app/src"
    assert syncer.pod_component == "backend"


def test_scan_changes_lifecycle(tmp_path: Path):
    syncer = FastFileSyncer(namespace="sandbox-test", local_dir=tmp_path)

    # Initial empty scan
    assert syncer.scan_changes() == []

    # Create a source file
    py_file = tmp_path / "main.py"
    py_file.write_text("print('hello')", encoding="utf-8")

    # Second scan: file is newly discovered and cached as baseline
    assert syncer.scan_changes() == []

    # Update file mtime / content
    py_file.write_text("print('updated')", encoding="utf-8")
    changed = syncer.scan_changes()
    assert py_file in changed

    # Non-changed subsequent scan
    assert syncer.scan_changes() == []


def test_scan_changes_ignores_unwanted_files(tmp_path: Path):
    syncer = FastFileSyncer(namespace="sandbox-test", local_dir=tmp_path)

    # Hidden file
    hidden = tmp_path / ".hidden.py"
    hidden.write_text("pass", encoding="utf-8")

    # pyc file
    pyc = tmp_path / "test.pyc"
    pyc.write_text("pass", encoding="utf-8")

    # __pycache__ directory
    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    cached = pycache / "cached.py"
    cached.write_text("pass", encoding="utf-8")

    syncer.scan_changes()
    # Now modify them
    hidden.write_text("modified", encoding="utf-8")
    pyc.write_text("modified", encoding="utf-8")
    cached.write_text("modified", encoding="utf-8")

    assert syncer.scan_changes() == []


def test_get_target_pod_success(tmp_path: Path):
    syncer = FastFileSyncer(namespace="sandbox-test", local_dir=tmp_path)

    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = "backend-7b89f6d4c-abc12\n"

    with patch("shutil.which", return_value="/usr/local/bin/kubectl"):
        with patch("subprocess.run", return_value=mock_res) as mock_run:
            pod = syncer.get_target_pod()
            assert pod == "backend-7b89f6d4c-abc12"
            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert "sandbox-test" in cmd
            assert "app.kubernetes.io/component=backend" in cmd[6]


def test_get_target_pod_not_found(tmp_path: Path):
    syncer = FastFileSyncer(namespace="sandbox-test", local_dir=tmp_path)

    with patch("shutil.which", return_value=None):
        assert syncer.get_target_pod() is None


def test_sync_file_to_pod(tmp_path: Path):
    syncer = FastFileSyncer(namespace="sandbox-test", local_dir=tmp_path, remote_dest="/app/src/")
    file_to_sync = tmp_path / "models" / "user.py"
    file_to_sync.parent.mkdir(parents=True)
    file_to_sync.write_text("class User: pass", encoding="utf-8")

    mock_res = MagicMock()
    mock_res.returncode = 0

    with patch("subprocess.run", return_value=mock_res) as mock_run:
        success = syncer.sync_file_to_pod("pod-123", file_to_sync)
        assert success is True
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "kubectl"
        assert cmd[1] == "cp"
        assert cmd[2] == str(file_to_sync)
        assert cmd[3] == "sandbox-test/pod-123:/app/src/models/user.py"


def test_sync_file_to_pod_failure(tmp_path: Path):
    syncer = FastFileSyncer(namespace="sandbox-test", local_dir=tmp_path)
    test_file = tmp_path / "main.py"
    test_file.write_text("test", encoding="utf-8")

    with patch("subprocess.run", side_effect=subprocess.SubprocessError("timeout")):
        success = syncer.sync_file_to_pod("pod-123", test_file)
        assert success is False
