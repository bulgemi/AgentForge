"""Reproducing test for build command project name tagging and sandbox Minikube image loading."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from agentforge.cli.commands.build import build_command
from agentforge.sandbox.manager import SandboxManager


def test_build_command_uses_project_name_tags():
    """Verify that build_command tags images with the current project name, not just agent-backend."""
    with tempfile.TemporaryDirectory() as tmpdir:
        proj_dir = Path(tmpdir) / "af_test002"
        backend_dir = proj_dir / "backend"
        frontend_dir = proj_dir / "frontend"
        backend_dir.mkdir(parents=True)
        frontend_dir.mkdir(parents=True)
        (backend_dir / "Dockerfile").write_text("FROM python:3.12-slim\n", encoding="utf-8")
        (frontend_dir / "Dockerfile").write_text("FROM node:20-alpine\n", encoding="utf-8")

        with patch("pathlib.Path.cwd", return_value=proj_dir), \
             patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)

            # Run build command
            build_command(tag="latest", target="all")

            # Check calls to subprocess.run
            backend_build_call = mock_run.call_args_list[0][0][0]
            frontend_build_call = mock_run.call_args_list[1][0][0]

            # The build calls MUST include the project name tag 'af_test002-backend:latest'
            assert "af_test002-backend:latest" in backend_build_call, (
                f"Backend docker build command must tag with project name 'af_test002-backend:latest'. Actual: {backend_build_call}"
            )
            assert "af_test002-frontend:latest" in frontend_build_call, (
                f"Frontend docker build command must tag with project name 'af_test002-frontend:latest'. Actual: {frontend_build_call}"
            )


def test_sandbox_manager_minikube_image_load():
    """Verify that SandboxManager can detect Minikube and load images."""
    manager = SandboxManager()
    assert hasattr(manager, "is_minikube_cluster"), "SandboxManager must have is_minikube_cluster method"
    assert hasattr(manager, "load_images_to_minikube"), "SandboxManager must have load_images_to_minikube method"

    with patch("shutil.which", return_value="/usr/local/bin/minikube"), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        success = manager.load_images_to_minikube(["af_test002-backend:latest", "af_test002-frontend:latest"])
        assert success is True
        assert mock_run.call_count == 2
        assert mock_run.call_args_list[0][0][0] == ["minikube", "image", "load", "af_test002-backend:latest"]
        assert mock_run.call_args_list[1][0][0] == ["minikube", "image", "load", "af_test002-frontend:latest"]

