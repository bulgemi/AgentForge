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
    with pytest.raises(ValidationError):
        validate_project_name("---")
    with pytest.raises(ValidationError):
        validate_project_name("___")


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
        
        # Docker Compose & Infrastructure checks
        dc_path = project_dir / "docker-compose.yml"
        assert dc_path.exists()
        dc_content = dc_path.read_text(encoding="utf-8")
        assert "demo-agent-postgres" in dc_content
        assert "demo-agent-redis" in dc_content
        assert "demo-agent-clickhouse" in dc_content
        assert "demo-agent-minio" in dc_content
        assert "demo-agent-minio-setup" in dc_content
        assert "demo-agent-langfuse" in dc_content
        assert "demo-agent-langfuse-worker" in dc_content
        assert "demo-agent-opensearch" in dc_content
        assert "demo-agent-opensearch-init" in dc_content
        assert "demo-agent-opensearch-dashboards" in dc_content
        assert "demo-agent-backend" in dc_content
        assert "demo-agent-frontend" in dc_content
        assert 'profiles: ["infra", "all"]' in dc_content
        assert 'profiles: ["infra", "observability", "all"]' in dc_content
        assert 'profiles: ["infra", "search", "audit", "all"]' in dc_content
        assert 'profiles: ["app", "all"]' in dc_content

        # Postgres init SQL check
        sql_path = project_dir / "postgres-init" / "init.sql"
        assert sql_path.exists()
        sql_content = sql_path.read_text(encoding="utf-8")
        assert "CREATE DATABASE demo_agent" in sql_content
        assert "CREATE DATABASE langfuse" in sql_content
        assert 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"' in sql_content
        assert 'CREATE EXTENSION IF NOT EXISTS "pgcrypto"' in sql_content

        # OpenSearch config & init script check
        os_init_sh = project_dir / "config" / "opensearch" / "init-opensearch.sh"
        os_template = project_dir / "config" / "opensearch" / "agent-index-template.json"
        assert os_init_sh.exists()
        assert os_template.exists()
        assert os.access(os_init_sh, os.X_OK)
        assert "demo_agent-template" in os_init_sh.read_text(encoding="utf-8")
        template_content = os_template.read_text(encoding="utf-8")
        assert "demo_agent-*" in template_content
        assert "knn_vector" in template_content

        # One-click convenience scripts checks (macOS / Linux / Windows)
        run_sh = project_dir / "run.sh"
        setup_sh = project_dir / "setup.sh"
        run_bat = project_dir / "run.bat"
        setup_bat = project_dir / "setup.bat"
        assert run_sh.exists()
        assert run_bat.exists()
        assert setup_sh.exists()
        assert setup_bat.exists()
        assert os.access(run_sh, os.X_OK)
        assert os.access(setup_sh, os.X_OK)

        run_sh_content = run_sh.read_text(encoding="utf-8")
        assert "docker compose --profile infra up -d" in run_sh_content
        assert "http://localhost:3000" in run_sh_content
        assert "http://localhost:5601" in run_sh_content

        run_bat_content = run_bat.read_text(encoding="utf-8")
        assert "docker compose --profile infra up -d" in run_bat_content
        assert "http://localhost:3000" in run_bat_content
        assert "http://localhost:5601" in run_bat_content

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
        backend_pyproj_text = (backend_dir / "pyproject.toml").read_text(encoding="utf-8")
        assert "[tool.hatch.build.targets.wheel]" in backend_pyproj_text
        assert 'packages = ["src"]' in backend_pyproj_text
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
        assert "OPENSEARCH_URL=http://localhost:9200" in env_content
        assert "LANGFUSE_ENABLED=true" in env_content

        env_sample_content = env_sample_file.read_text(encoding="utf-8")
        assert 'PROJECT_NAME="demo-agent"' in env_sample_content
        assert "DATABASE_DBNAME=demo_agent" in env_sample_content
        assert "OPENSEARCH_URL=http://localhost:9200" in env_sample_content
        assert "LANGFUSE_ENABLED=true" in env_sample_content

        # Clean Architecture layer checks
        src_dir = backend_dir / "src"
        assert (src_dir / "__init__.py").exists()
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

        # Frontend DESIGN.md and README.md checks
        design_md = frontend_dir / "DESIGN.md"
        fe_readme = frontend_dir / "README.md"
        assert design_md.exists()
        assert fe_readme.exists()

        design_content = design_md.read_text(encoding="utf-8")
        assert "# demo-agent Frontend Design System & AI Agent Guidelines" in design_content
        assert "skred" in design_content
        assert "lucide-react" in design_content
        assert "Strict Rules & Constraints for AI Coding Agents" in design_content

        fe_readme_content = fe_readme.read_text(encoding="utf-8")
        assert "# demo-agent - Frontend" in fe_readme_content
        assert "DESIGN.md" in fe_readme_content

        root_readme_content = (project_dir / "README.md").read_text(encoding="utf-8")
        assert "Frontend UI/UX Design System & AI Coding Agent Guidelines" in root_readme_content
        assert "frontend/DESIGN.md" in root_readme_content

        # Kubernetes checks
        k8s_dir = project_dir / "k8s"
        assert (k8s_dir / "k8s-deploy.sh").exists()
        assert (k8s_dir / "dev" / "backend.yaml").exists()
        assert (k8s_dir / "prd" / "backend.yaml").exists()

        # Python syntax validation
        assert validate_generated_project(project_dir) is True


def test_scaffolding_engine_infrastructure_idempotence_and_edge_cases():
    """Verify infrastructure generation works with underscores, streamlit, and force overwrite."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = ScaffoldingEngine()
        # 1. First generation
        project_dir = engine.generate(
            project_name="my_custom_bot",
            target_dir=tmpdir,
            framework="bedrock",
            frontend="streamlit",
        )

        assert project_dir.exists()
        dc_path = project_dir / "docker-compose.yml"
        assert dc_path.exists()
        dc_text = dc_path.read_text(encoding="utf-8")
        assert "my_custom_bot-postgres" in dc_text
        assert "my_custom_bot-opensearch" in dc_text

        sql_path = project_dir / "postgres-init" / "init.sql"
        assert sql_path.exists()
        sql_text = sql_path.read_text(encoding="utf-8")
        assert "CREATE DATABASE my_custom_bot" in sql_text
        assert "CREATE DATABASE langfuse" in sql_text

        init_sh = project_dir / "config" / "opensearch" / "init-opensearch.sh"
        assert init_sh.exists()
        assert os.access(init_sh, os.X_OK)
        assert "my_custom_bot-template" in init_sh.read_text(encoding="utf-8")

        template_json = project_dir / "config" / "opensearch" / "agent-index-template.json"
        assert template_json.exists()
        assert "my_custom_bot-*" in template_json.read_text(encoding="utf-8")

        # 2. Re-generation with force=True (idempotent overwrite)
        project_dir_force = engine.generate(
            project_name="my_custom_bot",
            target_dir=tmpdir,
            framework="bedrock",
            frontend="streamlit",
            force=True,
        )
        assert project_dir_force.exists()
        assert (project_dir_force / "docker-compose.yml").exists()
        assert (project_dir_force / "postgres-init" / "init.sql").exists()
        assert validate_generated_project(project_dir_force) is True


def test_scaffolding_docker_compose_all_profiles_validation():
    """Verify Docker Compose configurations are valid across all 6 logical profiles."""
    import subprocess
    import shutil

    docker_bin = shutil.which("docker")
    if not docker_bin:
        pytest.skip("Docker binary not available on host")

    with tempfile.TemporaryDirectory() as tmpdir:
        engine = ScaffoldingEngine()
        project_dir = engine.generate(
            project_name="profile-test-bot",
            target_dir=tmpdir,
            framework="langgraph",
            frontend="react-vite",
        )

        dc_path = project_dir / "docker-compose.yml"
        assert dc_path.exists()

        # Check all 6 required Compose profiles
        profiles = ["infra", "app", "observability", "search", "audit", "all"]
        for profile in profiles:
            result = subprocess.run(
                [docker_bin, "compose", "-f", str(dc_path), "--profile", profile, "config"],
                capture_output=True,
                text=True,
                cwd=str(project_dir),
            )
            assert result.returncode == 0, (
                f"Docker Compose failed for profile '{profile}':\n"
                f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
            )


def test_scaffolding_camel_case_project_name_snake_and_opensearch_schema():
    """Verify CamelCase project names produce lowercase snake_case for DB and valid OpenSearch templates."""
    import json

    with tempfile.TemporaryDirectory() as tmpdir:
        engine = ScaffoldingEngine()
        project_dir = engine.generate(
            project_name="MySuperAgent",
            target_dir=tmpdir,
            framework="langchain",
            frontend="react-vite",
        )

        # 1. OpenSearch index template JSON structure
        template_file = project_dir / "config" / "opensearch" / "agent-index-template.json"
        assert template_file.exists()
        template_data = json.loads(template_file.read_text(encoding="utf-8"))

        # Must be lowercase pattern: my_super_agent-*
        assert template_data["index_patterns"] == ["my_super_agent-*"]
        props = template_data["template"]["mappings"]["properties"]
        assert props["@timestamp"]["type"] == "date"
        assert props["trace_id"]["type"] == "keyword"
        assert props["session_id"]["type"] == "keyword"
        assert props["user_id"]["type"] == "keyword"
        assert props["action"]["type"] == "keyword"
        assert props["status"]["type"] == "keyword"
        assert props["query"]["type"] == "text"
        assert props["response"]["type"] == "text"
        assert props["embedding"]["type"] == "knn_vector"
        assert props["embedding"]["dimension"] == 1536
        assert props["embedding"]["method"]["name"] == "hnsw"
        assert props["embedding"]["method"]["space_type"] == "cosinesimil"

        # 2. Postgres init SQL check for lowercased DB name
        init_sql = project_dir / "postgres-init" / "init.sql"
        assert init_sql.exists()
        sql_text = init_sql.read_text(encoding="utf-8")
        assert "CREATE DATABASE my_super_agent" in sql_text
        assert "WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'my_super_agent')\\gexec" in sql_text
        assert "\\c my_super_agent" in sql_text

        # 3. OpenSearch init script has execution bit and lowercase template name
        init_sh = project_dir / "config" / "opensearch" / "init-opensearch.sh"
        assert init_sh.exists()
        assert os.access(init_sh, os.X_OK)
        sh_text = init_sh.read_text(encoding="utf-8")
        assert "my_super_agent-template" in sh_text
        assert "MAX_RETRIES=" in sh_text
        assert "exit 1" in sh_text
        assert "--fail-with-body" in sh_text


def test_scaffolding_engine_token_and_naming_edge_cases():
    """Verify to_snake_case and render_content robustness on complex names and bracket formatting."""
    from agentforge.generator.engine import to_snake_case

    # Naming normalization checks
    assert to_snake_case("my--agent") == "my_agent"
    assert to_snake_case("-leading-trailing-") == "leading_trailing"
    assert to_snake_case("SuperDuperBot") == "super_duper_bot"
    assert to_snake_case("already_snake_case") == "already_snake_case"
    assert to_snake_case("AgentV2") == "agent_v2"
    assert to_snake_case("Agent-47") == "agent_47"
    assert to_snake_case("---") == "agentforge_app"
    assert to_snake_case("___") == "agentforge_app"

    # Token replacement with varying whitespace
    engine = ScaffoldingEngine()
    ctx = {"project_name": "alpha-agent", "project_name_snake": "alpha_agent"}
    text = "A: {{ project_name }}, B: {{project_name}}, C: {{   project_name_snake   }}"
    rendered = engine.render_content(text, ctx)
    assert rendered == "A: alpha-agent, B: alpha-agent, C: alpha_agent"


def test_scaffolding_infra_resilience_contracts():
    """Verify minio-setup retry loops, OpenSearch template engine (faiss), health retries, and run warnings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = ScaffoldingEngine()
        project_dir = engine.generate(
            project_name="resilience-bot",
            target_dir=tmpdir,
            framework="langgraph",
            frontend="react-vite",
        )

        # 1. docker-compose.yml minio-setup loop & minio healthcheck
        dc_text = (project_dir / "docker-compose.yml").read_text(encoding="utf-8")
        assert "until mc alias set" in dc_text
        assert "mc mb --ignore-existing" in dc_text
        assert "Bucket langfuse ready." in dc_text
        assert "RETRY_COUNT=" in dc_text
        assert "MAX_RETRIES=" in dc_text
        assert "wget -qO-" in dc_text

        # 2. init-opensearch.sh error on missing template and health retry bound
        sh_text = (project_dir / "config" / "opensearch" / "init-opensearch.sh").read_text(encoding="utf-8")
        assert 'if [ ! -f "${INDEX_TEMPLATE_FILE}" ]; then' in sh_text
        assert "exit 1" in sh_text
        assert "--fail-with-body" in sh_text
        assert "HEALTH_MAX_RETRIES=30" in sh_text
        assert "Timed out waiting for OpenSearch cluster health" in sh_text

        # 3. agent-index-template.json uses faiss engine
        tpl_text = (project_dir / "config" / "opensearch" / "agent-index-template.json").read_text(encoding="utf-8")
        assert '"engine": "faiss"' in tpl_text

        # 4. run.sh and run.bat daemon diagnostic feedback
        run_sh_text = (project_dir / "run.sh").read_text(encoding="utf-8")
        assert "Docker is installed but the Docker daemon is not running" in run_sh_text
        run_bat_text = (project_dir / "run.bat").read_text(encoding="utf-8")
        assert "Docker is installed but the Docker daemon is not running" in run_bat_text


def test_backend_hatchling_wheel_target_and_editable_resolution():
    """Verify Hatchling correctly resolves the package in backend/src when wheel target packages = ['src'] is configured."""
    import os
    import shutil
    import subprocess

    with tempfile.TemporaryDirectory() as tmpdir:
        engine = ScaffoldingEngine()
        project_dir = engine.generate(
            project_name="wheel-test-bot",
            target_dir=tmpdir,
            framework="langgraph",
            frontend="none",
        )

        backend_dir = project_dir / "backend"
        pyproject_file = backend_dir / "pyproject.toml"
        init_file = backend_dir / "src" / "__init__.py"

        assert pyproject_file.exists()
        assert init_file.exists()

        content = pyproject_file.read_text(encoding="utf-8")
        assert "[tool.hatch.build.targets.wheel]" in content
        assert 'packages = ["src"]' in content

        setup_sh = project_dir / "setup.sh"
        setup_sh_content = setup_sh.read_text(encoding="utf-8")
        assert "--python .venv" in setup_sh_content

        result = subprocess.run(
            ["bash", str(setup_sh)],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0, f"setup.sh failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        assert "ValueError" not in result.stderr

        venv_python = backend_dir / ".venv" / "bin" / "python"
        verify_import = subprocess.run(
            [str(venv_python), "-c", "import src; print(src.__file__)"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert verify_import.returncode == 0, f"Failed to import src in generated venv: {verify_import.stderr}"
        assert str(init_file) in verify_import.stdout

        # Verify environment isolation: parent virtual environment was not contaminated
        verify_leak = subprocess.run(["uv", "pip", "list"], capture_output=True, text=True)
        assert "wheel-test-bot-backend" not in verify_leak.stdout


def test_backend_hatchling_editable_resolution_pip_fallback():
    """Verify Hatchling editable build succeeds when uv is absent via standard pip fallback in setup.sh."""
    import os
    import shutil
    import subprocess

    with tempfile.TemporaryDirectory() as tmpdir:
        engine = ScaffoldingEngine()
        project_dir = engine.generate(
            project_name="pip-fallback-bot",
            target_dir=tmpdir,
            framework="langgraph",
            frontend="none",
        )

        backend_dir = project_dir / "backend"
        init_file = backend_dir / "src" / "__init__.py"

        uv_path = shutil.which("uv")
        uv_dir = str(Path(uv_path).parent) if uv_path else ""
        paths = os.environ.get("PATH", "").split(":")
        clean_path = ":".join([p for p in paths if p != uv_dir])

        env = dict(os.environ)
        env["PATH"] = clean_path

        setup_sh = project_dir / "setup.sh"
        result = subprocess.run(
            ["bash", str(setup_sh)],
            cwd=str(project_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert result.returncode == 0, f"setup.sh pip fallback failed:\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        assert "ValueError" not in result.stderr

        venv_python = backend_dir / ".venv" / "bin" / "python"
        verify_import = subprocess.run(
            [str(venv_python), "-c", "import src; print(src.__file__)"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert verify_import.returncode == 0, f"Failed to import src in fallback venv: {verify_import.stderr}"
        assert str(init_file) in verify_import.stdout

        # Verify environment isolation: parent virtual environment was not contaminated
        verify_leak = subprocess.run(["uv", "pip", "list"], capture_output=True, text=True)
        assert "pip-fallback-bot-backend" not in verify_leak.stdout


def test_existing_generated_project_af_test001():
    """Verify existing generated project af_test001 satisfies Acceptance Criteria 2 and 3."""
    import subprocess
    from pathlib import Path

    af_dir = Path("/Users/a08126/geminiProjects/af_test001")
    if not af_dir.exists():
        pytest.skip("Existing generated project af_test001 not found at /Users/a08126/geminiProjects/af_test001")

    # Criterion 2: /Users/a08126/geminiProjects/af_test001/backend/pyproject.toml contains wheel target configuration
    backend_dir = af_dir / "backend"
    pyproject_path = backend_dir / "pyproject.toml"
    assert pyproject_path.exists(), f"pyproject.toml missing at {pyproject_path}"

    pyproject_content = pyproject_path.read_text(encoding="utf-8")
    assert "[tool.hatch.build.targets.wheel]" in pyproject_content, (
        "backend/pyproject.toml missing [tool.hatch.build.targets.wheel]"
    )
    assert 'packages = ["src"]' in pyproject_content, (
        'backend/pyproject.toml missing packages = ["src"]'
    )

    init_py = backend_dir / "src" / "__init__.py"
    assert init_py.exists(), f"src/__init__.py missing at {init_py}"

    # Criterion 3: setup.sh in af_test001 completes backend dependency installation without Hatchling build errors
    setup_sh = af_dir / "setup.sh"
    assert setup_sh.exists(), f"setup.sh missing at {setup_sh}"

    result = subprocess.run(
        ["bash", str(setup_sh)],
        cwd=str(af_dir),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, (
        f"af_test001 setup.sh failed with return code {result.returncode}:\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "ValueError" not in result.stderr, (
        f"Hatchling ValueError detected in stderr:\n{result.stderr}"
    )

    # Verify editable installation allows importing src
    venv_python = backend_dir / ".venv" / "bin" / "python"
    assert venv_python.exists(), f"Virtualenv python missing at {venv_python}"
    verify_import = subprocess.run(
        [str(venv_python), "-c", "import src; print(src.__file__)"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert verify_import.returncode == 0, (
        f"Failed to import src in af_test001 venv:\n{verify_import.stderr}"
    )
    assert str(init_py) in verify_import.stdout


def test_vscode_config_react_vite():
    import json
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = ScaffoldingEngine()
        project_dir = engine.generate(
            project_name="vscode-react-test",
            target_dir=tmpdir,
            framework="langgraph",
            frontend="react-vite",
        )

        vscode_dir = project_dir / ".vscode"
        assert vscode_dir.is_dir()

        launch_file = vscode_dir / "launch.json"
        assert launch_file.is_file()
        launch_data = json.loads(launch_file.read_text(encoding="utf-8"))

        assert launch_data.get("version") == "0.2.0"
        configs = launch_data.get("configurations", [])
        config_names = [c["name"] for c in configs]
        assert "Backend: FastAPI (uvicorn)" in config_names
        assert "Frontend: Vite Dev Server" in config_names

        backend_cfg = next(c for c in configs if c["name"] == "Backend: FastAPI (uvicorn)")
        assert backend_cfg["type"] == "debugpy"
        assert backend_cfg["python"] == "${workspaceFolder}/backend/.venv/bin/python"
        assert backend_cfg["windows"]["python"] == "${workspaceFolder}/backend/.venv/Scripts/python.exe"
        assert "--port" in backend_cfg["args"]
        assert "8000" in backend_cfg["args"]
        assert backend_cfg["envFile"] == "${workspaceFolder}/backend/.env"

        frontend_cfg = next(c for c in configs if c["name"] == "Frontend: Vite Dev Server")
        assert frontend_cfg["type"] == "node-terminal"
        assert frontend_cfg["command"] == "npm run dev"
        assert "serverReadyAction" in frontend_cfg

        compounds = launch_data.get("compounds", [])
        assert len(compounds) == 1
        assert compounds[0]["name"] == "Fullstack: Backend + Frontend"
        assert "Backend: FastAPI (uvicorn)" in compounds[0]["configurations"]
        assert "Frontend: Vite Dev Server" in compounds[0]["configurations"]

        settings_file = vscode_dir / "settings.json"
        assert settings_file.is_file()
        settings_data = json.loads(settings_file.read_text(encoding="utf-8"))
        assert settings_data["python.defaultInterpreterPath"] == "${workspaceFolder}/backend/.venv/bin/python"
        assert "${workspaceFolder}/backend/src" in settings_data["python.analysis.extraPaths"]


def test_vscode_config_streamlit():
    import json
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = ScaffoldingEngine()
        project_dir = engine.generate(
            project_name="vscode-streamlit-test",
            target_dir=tmpdir,
            framework="langgraph",
            frontend="streamlit",
        )

        launch_file = project_dir / ".vscode" / "launch.json"
        assert launch_file.is_file()
        launch_data = json.loads(launch_file.read_text(encoding="utf-8"))

        config_names = [c["name"] for c in launch_data.get("configurations", [])]
        assert "Backend: FastAPI (uvicorn)" in config_names
        assert "Frontend: Streamlit UI" in config_names

        compounds = launch_data.get("compounds", [])
        assert len(compounds) == 1
        assert compounds[0]["name"] == "Fullstack: Backend + Frontend"
        assert "Frontend: Streamlit UI" in compounds[0]["configurations"]


def test_vscode_config_none():
    import json
    with tempfile.TemporaryDirectory() as tmpdir:
        engine = ScaffoldingEngine()
        project_dir = engine.generate(
            project_name="vscode-none-test",
            target_dir=tmpdir,
            framework="langgraph",
            frontend="none",
        )

        launch_file = project_dir / ".vscode" / "launch.json"
        assert launch_file.is_file()
        launch_data = json.loads(launch_file.read_text(encoding="utf-8"))

        config_names = [c["name"] for c in launch_data.get("configurations", [])]
        assert "Backend: FastAPI (uvicorn)" in config_names
        assert len(config_names) == 1
        assert "compounds" not in launch_data


def test_backend_dependencies_and_app_initialization():
    """Verify backend dependencies include email-validator and python-multipart and app initializes."""
    import subprocess
    import sys

    with tempfile.TemporaryDirectory() as tmpdir:
        engine = ScaffoldingEngine()
        project_dir = engine.generate(
            project_name="app-init-test",
            target_dir=tmpdir,
            framework="langgraph",
            frontend="react-vite",
        )

        backend_pyproject = project_dir / "backend" / "pyproject.toml"
        assert backend_pyproject.is_file()
        content = backend_pyproject.read_text(encoding="utf-8")
        assert "email-validator>=" in content
        assert "python-multipart>=" in content

        # Run python script verifying app loads with valid DTOs and routes
        backend_dir = project_dir / "backend"
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{backend_dir}/src:{backend_dir}"
        result = subprocess.run(
            [sys.executable, "-c", "from src.main import app; assert app.title == 'app-init-test API'; print('OK')"],
            cwd=str(backend_dir),
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0, f"App import failed: STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
        assert "OK" in result.stdout

