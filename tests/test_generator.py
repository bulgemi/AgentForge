"""Tests for AgentForge project generator and scaffolding engine."""

from __future__ import annotations

import os
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

        # One-click convenience scripts checks (macOS / Linux / Windows)
        run_sh = project_dir / "run.sh"
        setup_sh = project_dir / "setup.sh"
        assert run_sh.exists()
        assert (project_dir / "run.bat").exists()
        assert setup_sh.exists()
        assert (project_dir / "setup.bat").exists()
        assert os.access(run_sh, os.X_OK)
        assert os.access(setup_sh, os.X_OK)

        # Root .gitignore check
        gitignore_path = project_dir / ".gitignore"
        assert gitignore_path.exists()
        gi_content = gitignore_path.read_text(encoding="utf-8")
        assert "backend/.env" in gi_content
        assert "frontend/.env" in gi_content
        assert "!.env.sample" in gi_content

        # Backend checks
        backend_dir = project_dir / "backend"
        assert backend_dir.exists()
        assert (backend_dir / "pyproject.toml").exists()
        assert (backend_dir / "Dockerfile").exists()
        assert (backend_dir / "alembic.ini").exists()

        # Backend .env & .env.sample checks
        env_file = backend_dir / ".env"
        env_sample_file = backend_dir / ".env.sample"
        assert env_file.exists()
        assert env_sample_file.exists()

        env_content = env_file.read_text(encoding="utf-8")
        assert 'PROJECT_NAME="demo-agent"' in env_content
        assert "DATABASE_DBNAME=demo_agent" in env_content
        assert "JWT_SECRET_KEY=demo-agent-secret-key" in env_content

        env_sample_content = env_sample_file.read_text(encoding="utf-8")
        assert 'PROJECT_NAME="demo-agent"' in env_sample_content
        assert "DATABASE_DBNAME=demo_agent" in env_sample_content

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

        # Frontend checks (Multi-entrypoint & Branding Assets)
        frontend_dir = project_dir / "frontend"
        assert frontend_dir.exists()
        assert (frontend_dir / "package.json").exists()
        assert (frontend_dir / "vite.config.js").exists()
        assert (frontend_dir / "index.html").exists()
        assert (frontend_dir / "admin.html").exists()
        assert (frontend_dir / "public" / "favicon.ico").exists()
        assert (frontend_dir / "public" / "agentforge_icon.png").exists()

        # Frontend .env & .env.sample checks
        fe_env = frontend_dir / ".env"
        fe_env_sample = frontend_dir / ".env.sample"
        assert fe_env.exists()
        assert fe_env_sample.exists()

        fe_env_content = fe_env.read_text(encoding="utf-8")
        assert 'VITE_APP_TITLE="demo-agent"' in fe_env_content
        assert "VITE_API_BASE_URL=/api/v1" in fe_env_content
        assert "VITE_DEV_PROXY_TARGET=http://localhost:8000" in fe_env_content

        fe_env_sample_content = fe_env_sample.read_text(encoding="utf-8")
        assert 'VITE_APP_TITLE="demo-agent"' in fe_env_sample_content
        assert "VITE_API_BASE_URL=/api/v1" in fe_env_sample_content

        index_html = (frontend_dir / "index.html").read_text(encoding="utf-8")
        admin_html = (frontend_dir / "admin.html").read_text(encoding="utf-8")
        assert 'href="/favicon.ico"' in index_html
        assert 'href="/favicon.ico"' in admin_html

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
