"""Scaffolding and template synthesis engine for AgentForge projects."""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Mapping

from .copier import copy_core_engine
from .validator import (
    ValidationError,
    validate_framework,
    validate_frontend,
    validate_generated_project,
    validate_project_name,
    validate_target_directory,
)

PACKAGE_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
PACKAGE_ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets"


def to_snake_case(name: str) -> str:
    """Convert PascalCase, camelCase, or kebab-case string into lowercase snake_case."""
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
    s = s.replace("-", "_")
    s = re.sub(r'_+', '_', s)
    result = s.strip("_").lower()
    return result or "agentforge_app"


class ScaffoldingEngine:
    """Orchestrates creation of fullstack standalone agent projects."""

    def __init__(self, templates_dir: str | Path | None = None) -> None:
        self.templates_dir = Path(templates_dir or PACKAGE_TEMPLATES_DIR).resolve()

    def render_content(self, text: str, context: Mapping[str, Any]) -> str:
        """Simple, fast token replacement without requiring heavy template runtime."""
        rendered = text
        for key, value in context.items():
            # Support {{ key }}, {{key}}, {{  key  }} with arbitrary internal whitespace
            pattern = re.compile(r"\{\{\s*" + re.escape(key) + r"\s*\}\}")
            rendered = pattern.sub(str(value), rendered)
        return rendered

    def copy_template_tree(
        self,
        source_dir: Path,
        dest_dir: Path,
        context: Mapping[str, Any],
        exclude_exts: tuple[str, ...] = (".pyc", ".pyo"),
    ) -> None:
        """Recursively copy template directory tree, substituting variables in text files."""
        if not source_dir.exists():
            return

        dest_dir.mkdir(parents=True, exist_ok=True)
        text_extensions = (
            ".py",
            ".json",
            ".yaml",
            ".yml",
            ".md",
            ".toml",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".html",
            ".css",
            ".sh",
            ".bat",
            ".cmd",
            ".env",
            ".sample",
            ".ini",
            ".conf",
            ".txt",
            ".sql",
        )

        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if not d.startswith("__pycache__") and d != "node_modules"]
            rel_dir = Path(root).relative_to(source_dir)
            target_current_dir = dest_dir / rel_dir
            target_current_dir.mkdir(parents=True, exist_ok=True)

            for file_name in files:
                if any(file_name.endswith(ext) for ext in exclude_exts):
                    continue
                src_file = Path(root) / file_name
                dest_file = target_current_dir / file_name

                # Check if it is a text template that can be substituted
                is_text = any(file_name.endswith(ext) for ext in text_extensions) or file_name.startswith(".env")
                if is_text:
                    try:
                        content = src_file.read_text(encoding="utf-8")
                        rendered = self.render_content(content, context)
                        dest_file.write_text(rendered, encoding="utf-8")
                        # Preserve executable permissions for scripts
                        if (src_file.stat().st_mode & 0o111) or file_name.endswith(".sh"):
                            dest_file.chmod(dest_file.stat().st_mode | 0o755)
                        continue
                    except UnicodeDecodeError:
                        pass

                # Binary or non-text file copy
                shutil.copy2(src_file, dest_file)

    def generate(
        self,
        project_name: str,
        target_dir: str | Path,
        framework: str = "langgraph",
        frontend: str = "react-vite",
        force: bool = False,
    ) -> Path:
        """Generate a complete standalone project with backend, frontend, infra, and core.

        Args:
            project_name: Name of the project.
            target_dir: Directory where the project should be created.
            framework: Agent framework (e.g. langgraph, langchain, bedrock, etc.).
            frontend: Frontend framework (react-vite, streamlit, or none).
            force: Overwrite if directory exists.

        Returns:
            Path to the created project.
        """
        clean_name = validate_project_name(project_name)
        clean_framework = validate_framework(framework)
        clean_frontend = validate_frontend(frontend)
        dest_root = validate_target_directory(Path(target_dir) / clean_name, force=force)
        dest_root.mkdir(parents=True, exist_ok=True)

        context = {
            "project_name": clean_name,
            "project_name_snake": to_snake_case(clean_name),
            "framework": clean_framework,
            "frontend": clean_frontend,
            "python_version": "3.12",
        }

        # 1. Copy Backend Template
        backend_tpl = self.templates_dir / "backend"
        if backend_tpl.exists():
            self.copy_template_tree(backend_tpl, dest_root / "backend", context)

        # 2. Inject Selected Framework Adapter Template
        framework_tpl = self.templates_dir / "backend" / "src" / "frameworks" / clean_framework
        if framework_tpl.exists():
            dest_fw = dest_root / "backend" / "src" / "infrastructure" / "adapters" / "agent"
            dest_fw.mkdir(parents=True, exist_ok=True)
            self.copy_template_tree(framework_tpl, dest_fw, context)

        # 3. Copy Frontend Template
        if clean_frontend in ("react", "react-vite"):
            frontend_tpl = self.templates_dir / "frontend" / "react-vite"
            if frontend_tpl.exists():
                self.copy_template_tree(frontend_tpl, dest_root / "frontend", context)

            # Ensure branding assets (favicon, logos) from assets/ are synced to frontend/public
            if PACKAGE_ASSETS_DIR.exists():
                dest_public = dest_root / "frontend" / "public"
                dest_public.mkdir(parents=True, exist_ok=True)
                for asset_file in PACKAGE_ASSETS_DIR.iterdir():
                    if asset_file.is_file() and not asset_file.name.startswith("."):
                        shutil.copy2(asset_file, dest_public / asset_file.name)
        elif clean_frontend == "streamlit":
            streamlit_tpl = self.templates_dir / "frontend" / "streamlit"
            if streamlit_tpl.exists():
                self.copy_template_tree(streamlit_tpl, dest_root / "frontend", context)

        # 4. Copy Infrastructure & Kubernetes Templates
        infra_tpl = self.templates_dir / "infra"
        if infra_tpl.exists():
            # docker-compose.yml and postgres-init
            for item in infra_tpl.iterdir():
                if item.is_file():
                    content = item.read_text(encoding="utf-8")
                    (dest_root / item.name).write_text(self.render_content(content, context), encoding="utf-8")
                elif item.is_dir():
                    self.copy_template_tree(item, dest_root / item.name, context)

        k8s_tpl = self.templates_dir / "k8s"
        if k8s_tpl.exists():
            self.copy_template_tree(k8s_tpl, dest_root / "k8s", context)

        # 4.1 Copy Convenience Scripts (run.sh, run.bat, setup.sh, setup.bat)
        scripts_tpl = self.templates_dir / "scripts"
        if scripts_tpl.exists():
            for item in scripts_tpl.iterdir():
                if item.is_file():
                    content = item.read_text(encoding="utf-8")
                    dest_file = dest_root / item.name
                    dest_file.write_text(self.render_content(content, context), encoding="utf-8")
                    if item.name.endswith(".sh"):
                        dest_file.chmod(dest_file.stat().st_mode | 0o755)

        # 5. Standalone Core Engine Copy
        dest_backend_src = dest_root / "backend" / "src"
        copy_core_engine(dest_backend_src, overwrite=True)

        # 6. Generate project README.md and root files
        gitignore_tpl = self.templates_dir / "root" / ".gitignore"
        dest_gitignore = dest_root / ".gitignore"
        if gitignore_tpl.exists() and not dest_gitignore.exists():
            gi_content = gitignore_tpl.read_text(encoding="utf-8")
            dest_gitignore.write_text(self.render_content(gi_content, context), encoding="utf-8")

        # 6.0 Copy Agent Developer Harness Skills (.agents/skills)
        agents_tpl = self.templates_dir / "root" / ".agents"
        if agents_tpl.exists():
            self.copy_template_tree(agents_tpl, dest_root / ".agents", context)

        # 6.1 Generate VS Code Launch and Settings configurations (.vscode/launch.json, settings.json)
        self._generate_vscode_configs(dest_root, clean_frontend)

        readme_path = dest_root / "README.md"
        if not readme_path.exists():
            readme_content = f"""# {clean_name} ⚡

Standalone AI Agent Project built with [AgentForge](https://github.com/bulgemi/AgentForge).

- **Framework**: {clean_framework}
- **Frontend**: {clean_frontend}
- **Architecture**: Fullstack Clean Architecture Monorepo
- **Authentication**: ID/PW, LDAP, SAML 2.0
- **Database & Cache**: PostgreSQL 16 + Redis 7.4
- **Observability**: Langfuse v3 (ClickHouse + MinIO + Web + Worker)
- **Search & Vectors**: OpenSearch 2.19.3 + OpenSearch Dashboards

## Quick Start

### 1. One-Click Local Run (Recommended)
Automatically sets up virtual environment, launches Docker infrastructure (Postgres, Redis, Langfuse, OpenSearch), and runs dev servers.

```bash
# macOS / Linux
./run.sh

# Windows
run.bat
```

> **Tip**: To install dependencies only without starting servers, run `./setup.sh` or `setup.bat`.

### 2. VS Code One-Click Launch & Debug (F5)
Press **F5** or navigate to the **Run and Debug** view (`Ctrl+Shift+D` / `Cmd+Shift+D`):
- **Fullstack: Backend + Frontend**: Launches both backend (FastAPI uvicorn) and frontend dev server simultaneously.
- **Backend: FastAPI (uvicorn)**: Debug FastAPI backend with breakpoint support.
- **Frontend: Vite Dev Server**: Start frontend with automatic browser launching.

### 3. Manage Infrastructure with Docker Compose

> **Important**: All services use Docker Compose profiles. Running `docker compose up -d` without `--profile` will result in `no service selected`. Always specify `--profile infra` (recommended for local development) or `--profile all`.

Start specific stacks using Docker Compose profiles:

```bash
# 1. Start all infrastructure (Recommended: PostgreSQL, Redis, Langfuse v3, OpenSearch)
docker compose --profile infra up -d

# 2. Start observability stack only (Langfuse Web, Worker, ClickHouse, MinIO)
docker compose --profile observability up -d

# 3. Start search stack only (OpenSearch, Init, Dashboards)
docker compose --profile search up -d

# 4. Start all services including Backend & Frontend containers
docker compose --profile all up -d
```

### 4. Service Dashboard & URLs
- **Frontend (Chat)**: http://localhost:5173
- **Frontend (Admin)**: http://localhost:5173/admin.html
- **Backend API Docs**: http://localhost:8000/docs
- **Langfuse Observability**: http://localhost:3000
- **OpenSearch Dashboards**: http://localhost:5601
- **OpenSearch API**: http://localhost:9200

### 5. Initial Login Credentials (Default Admin)
When the backend starts up for the first time, it automatically creates database tables and seeds a default administrator account:
- **Username**: `admin`
- **Password**: `admin1234!` (Can be customized via `DEFAULT_ADMIN_PASSWORD` in `backend/.env`)
- **Role**: `admin` (Has access to both Chat Portal and Admin Console)

### 6. Manual Run Locally
```bash
# Backend
cd backend
uv run uvicorn src.main:app --reload --port 8000

# Frontend
cd ../frontend
npm install
npm run dev
```

### 7. Frontend UI/UX Design System & AI Coding Agent Guidelines
AgentForge adopts a **Spec-Driven UI Development** methodology:
- Edit [`frontend/DESIGN.md`](frontend/DESIGN.md) to define your project's unique domain requirements, branding, and UI specifications.
- When pairing with AI Coding Agents (Cursor, Claude Code, GitHub Copilot, Windsurf, Antigravity), point the agent to [`frontend/DESIGN.md`](frontend/DESIGN.md) as the Single Source of Truth for generating and maintaining consistent, spec-compliant UI components.
- Refer to [`frontend/README.md`](frontend/README.md) for frontend architecture and prompt instructions.

### 8. AI Developer Harness & Workflow Skills (`.agents/skills`)
This project comes pre-configured with standardized AI Developer Harness Skills to streamline feature delivery, enhancements, and bugfixes:
- **`feature-development`** (`.agents/skills/feature-development/SKILL.md`): End-to-end new feature development harness.
- **`feature-enhancement`** (`.agents/skills/feature-enhancement/SKILL.md`): Safe feature enhancement, refactoring, and impact analysis harness.
- **`bugfix`** (`.agents/skills/bugfix/SKILL.md`): RCA, reproducing failing test-driven bugfix harness.
- **Standard 8-Stage Pipeline**:
  `분석` → `파일 단위 상세 설계` → `설계 리뷰(오버엔지니어링 검토)` → `★사용자 승인 게이트` → `GitHub Issue 등록(단계/상태 태그)` → `Issue 기반 구현` → `코드 리뷰` → `기능 점검(신규/회귀 테스트)` → `결과 보고 및 Issue 종료`
- See [`.agents/skills/shared/workflow-spec.md`](.agents/skills/shared/workflow-spec.md) for GitHub CLI (`gh`) commands, label schema (`type:*`, `stage:*`, `status:*`), and local markdown fallback rules.
"""
            readme_path.write_text(readme_content, encoding="utf-8")

        # 7. Post-scaffold syntax verification
        validate_generated_project(dest_root)

        return dest_root

    def _generate_vscode_configs(self, dest_root: Path, frontend: str) -> None:
        """Generate .vscode/launch.json and .vscode/settings.json configurations."""
        vscode_dir = dest_root / ".vscode"
        vscode_dir.mkdir(parents=True, exist_ok=True)

        backend_config: dict[str, Any] = {
            "name": "Backend: FastAPI (uvicorn)",
            "type": "debugpy",
            "request": "launch",
            "python": "${workspaceFolder}/backend/.venv/bin/python",
            "windows": {
                "python": "${workspaceFolder}/backend/.venv/Scripts/python.exe"
            },
            "module": "uvicorn",
            "args": [
                "src.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
                "--reload"
            ],
            "cwd": "${workspaceFolder}/backend",
            "envFile": "${workspaceFolder}/backend/.env",
            "env": {
                "PYTHONPATH": "${workspaceFolder}/backend/src:${workspaceFolder}/backend"
            },
            "jinja": True,
            "justMyCode": False,
            "console": "integratedTerminal"
        }

        configurations: list[dict[str, Any]] = [backend_config]
        compounds: list[dict[str, Any]] = []

        if frontend in ("react", "react-vite"):
            frontend_config: dict[str, Any] = {
                "name": "Frontend: Vite Dev Server",
                "type": "node-terminal",
                "request": "launch",
                "command": "npm run dev",
                "cwd": "${workspaceFolder}/frontend",
                "envFile": "${workspaceFolder}/frontend/.env",
                "serverReadyAction": {
                    "pattern": "Local:\\s+(https?://\\S+)",
                    "uriFormat": "%s",
                    "action": "openExternally"
                }
            }
            configurations.append(frontend_config)
            compounds.append({
                "name": "Fullstack: Backend + Frontend",
                "configurations": [
                    "Backend: FastAPI (uvicorn)",
                    "Frontend: Vite Dev Server"
                ],
                "stopAll": True
            })
        elif frontend == "streamlit":
            frontend_config = {
                "name": "Frontend: Streamlit UI",
                "type": "debugpy",
                "request": "launch",
                "python": "${workspaceFolder}/backend/.venv/bin/python",
                "windows": {
                    "python": "${workspaceFolder}/backend/.venv/Scripts/python.exe"
                },
                "module": "streamlit",
                "args": [
                    "run",
                    "app.py"
                ],
                "cwd": "${workspaceFolder}/frontend",
                "envFile": "${workspaceFolder}/backend/.env",
                "console": "integratedTerminal"
            }
            configurations.append(frontend_config)
            compounds.append({
                "name": "Fullstack: Backend + Frontend",
                "configurations": [
                    "Backend: FastAPI (uvicorn)",
                    "Frontend: Streamlit UI"
                ],
                "stopAll": True
            })

        launch_data: dict[str, Any] = {
            "version": "0.2.0",
            "configurations": configurations
        }
        if compounds:
            launch_data["compounds"] = compounds

        launch_file = vscode_dir / "launch.json"
        if not launch_file.exists():
            launch_file.write_text(json.dumps(launch_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        settings_data: dict[str, Any] = {
            "python.defaultInterpreterPath": "${workspaceFolder}/backend/.venv/bin/python",
            "python.analysis.extraPaths": [
                "${workspaceFolder}/backend",
                "${workspaceFolder}/backend/src"
            ],
            "python.autoComplete.extraPaths": [
                "${workspaceFolder}/backend",
                "${workspaceFolder}/backend/src"
            ]
        }
        settings_file = vscode_dir / "settings.json"
        if not settings_file.exists():
            settings_file.write_text(json.dumps(settings_data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
