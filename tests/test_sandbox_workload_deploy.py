"""Reproducing tests for sandbox workload deployment and namespace normalization."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from typer.testing import CliRunner

from agentforge.cli.main import app
from agentforge.sandbox.manager import SandboxManager

runner = CliRunner()


def test_reproduce_get_namespace_duplicate_prefix():
    """Verify get_namespace does NOT duplicate 'sandbox-' prefix when already provided."""
    # When developer specifies 'sandbox-a08126', it should produce 'sandbox-a08126', NOT 'sandbox-sandbox-a08126'
    assert SandboxManager.get_namespace("sandbox-a08126") == "sandbox-a08126"
    assert SandboxManager.get_namespace("sandbox-user") == "sandbox-user"
    assert SandboxManager.get_namespace("a08126") == "sandbox-a08126"


def test_reproduce_k8s_workload_deployment_in_scaffolded_project():
    """Verify sandbox up deploys k8s/dev manifests when charts directory does not exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        proj_dir = Path(tmpdir) / "my-agent"
        k8s_dev = proj_dir / "k8s" / "dev"
        k8s_dev.mkdir(parents=True)

        # Create sample k8s/dev manifests mimicking AgentForge generated structure
        backend_yaml = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-agent-backend
  labels:
    app: my-agent-backend
spec:
  replicas: 1
  template:
    spec:
      containers:
        - name: backend
          image: my-agent-backend:latest
"""
        configmap_yaml = """apiVersion: v1
kind: ConfigMap
metadata:
  name: my-agent-config
data:
  APP_ENV: dev
"""
        (k8s_dev / "backend.yaml").write_text(backend_yaml, encoding="utf-8")
        (k8s_dev / "configmap.yaml").write_text(configmap_yaml, encoding="utf-8")

        manager = SandboxManager()
        # Verify manager has deploy_k8s_workloads method
        assert hasattr(manager, "deploy_k8s_workloads"), "SandboxManager must have deploy_k8s_workloads"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="success", stderr="")
            applied_manifests = manager.deploy_k8s_workloads(
                namespace="sandbox-a08126",
                k8s_dir=k8s_dev,
                domain_suffix="127.0.0.1.nip.io",
                dry_run=True,
            )
            assert len(applied_manifests) >= 2
            # Verify target namespace is injected
            for manifest in applied_manifests:
                docs = list(yaml.safe_load_all(manifest))
                for doc in docs:
                    if doc and "metadata" in doc:
                        assert doc["metadata"].get("namespace") == "sandbox-a08126"
