"""Tests for AgentForge project generator and scaffolding engine."""

from __future__ import annotations

import tempfile
from pathlib import Path
import pytest

from agentforge.generator.copier import copy_core_engine
from agentforge.generator.engine import ScaffoldingEngine
from agentforge.generator.validator import (
    ValidationError,
    validate_framework,
    validate_frontend,
    validate_generated_project,
    validate_project_name,
)


def test_validator_project_name():
    assert validate_project_name("my-agent") == "my-agent"
    assert validate_project_name("my_agent_123") == "my_agent_123"
    with pytest.raises(ValidationError):
        validate_project_name("")
    with pytest.raises(ValidationError):
        validate_project_name("my agent with spaces")
    with pytest.raises(ValidationError):
        validate_project_name("agent@invalid!")


def test_validator_framework():
    assert validate_framework("langgraph") == "langgraph"
    assert validate_framework("LANGCHAIN") == "langchain"
    assert validate_framework("aws_bedrock") == "bedrock"
    with pytest.raises(ValidationError):
        validate_framework("unsupported_framework")


def test_validator_frontend():
    assert validate_frontend("react") == "react-vite"
    assert validate_frontend("react-vite") == "react-vite"
    assert validate_frontend("streamlit") == "streamlit"
    assert validate_frontend("none") == "none"
    with pytest.raises(ValidationError):
        validate_frontend("angular")


def test_copier_copies_core_engine():
    with tempfile.TemporaryDirectory() as tmpdir:
        dest_backend_src = Path(tmpdir) / "backend" / "src"
        copied = copy_core_engine(dest_backend_src)

        dest_core = dest_backend_src / "core"
        assert dest_core.exists()
        assert (dest_core / "adapter.py").exists()
        assert (dest_core / "streaming.py").exists()
        assert (dest_core / "database.py").exists()
        assert (dest_core / "logging.py").exists()
        assert (dest_core / "config.py").exists()
        assert (dest_core / "__init__.py").exists()
        assert len(copied) >= 6


def test_scaffolding_engine_full_generation():
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = ScaffoldingEngine()
        project_dir = engine.generate(
            project_name="demo-agent",
            target_dir=tmpdir,
            framework="langgraph",
            frontend="react",
        )

        assert project_dir.exists()
        assert (project_dir / "README.md").exists()
        assert (project_dir / "docker-compose.yml").exists()

        # Backend checks
        backend_dir = project_dir / "backend"
        assert backend_dir.exists()
        assert (backend_dir / "pyproject.toml").exists()
        assert (backend_dir / "Dockerfile").exists()
        assert (backend_dir / "alembic.ini").exists()

        # Clean Architecture layer checks
        src_dir = backend_dir / "src"
        assert (src_dir / "core" / "adapter.py").exists()
        assert (src_dir / "core" / "streaming.py").exists()
        assert (src_dir / "domain" / "entities" / "user.py").exists()
        assert (src_dir / "application" / "auth_service.py").exists()
        assert (src_dir / "infrastructure" / "auth" / "redis_session.py").exists()
        assert (src_dir / "infrastructure" / "rest" / "routes" / "_chat_routes.py").exists()
        assert (src_dir / "bootstrap.py").exists()
        assert (src_dir / "main.py").exists()

        # Frontend checks (Multi-entrypoint)
        frontend_dir = project_dir / "frontend"
        assert frontend_dir.exists()
        assert (frontend_dir / "package.json").exists()
        assert (frontend_dir / "vite.config.js").exists()
        assert (frontend_dir / "index.html").exists()
        assert (frontend_dir / "admin.html").exists()
        assert (frontend_dir / "src" / "App.jsx").exists()
        assert (frontend_dir / "src" / "admin" / "AdminApp.jsx").exists()
        assert (frontend_dir / "src" / "components" / "chat" / "ChatAssistant.jsx").exists()
        assert (frontend_dir / "src" / "components" / "settings" / "AccountManagementPanel.jsx").exists()

        # Kubernetes checks
        k8s_dir = project_dir / "k8s"
        assert (k8s_dir / "k8s-deploy.sh").exists()
        assert (k8s_dir / "dev" / "backend.yaml").exists()
        assert (k8s_dir / "prd" / "backend.yaml").exists()

        # Python syntax validation
        assert validate_generated_project(project_dir) is True
